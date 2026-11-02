"""001 read facade over002 storage: coherent captures and explicit absence, without incorporation."""

from uuid import uuid4

from sqlalchemy import text

from ecs_ec.consumption.catalog import CATEGORIES, CATEGORY_IDS
from ecs_ec.consumption.catalog_storage import BuildingRow, configuration_segments, read_revisions
from ecs_ec.consumption.models import instant
from ecs_ec.consumption.periods import local_day, resolve_period, timestamp
from ecs_ec.consumption.schemas import (Catalog, CategoryStatus, CategoryView, DetailResult,
    DetailRow, Diagnostic, PeriodView, SegmentView, WarningView)
from ecs_ec.core.unit_of_work import UnitOfWork


class InvalidSelection(ValueError):
    """A user period failed validation before any storage query; internal evidence errors use503."""


class Consumption:
    """Read configured singleton data using a concrete storage port and caller-owned optional UoW."""

    def __init__(self, database, clock, building_id, store):
        """Inject actual002 storage,001 context identity and an internal clock; no business writes."""
        self.database, self.clock, self.building_id, self.store = database, clock, building_id, store

    async def _context(self, uow):
        """Read context/revisions within the established capture; missing context is a setup error."""
        building = await uow.session.get(BuildingRow, self.building_id)
        if building is None:
            raise ValueError('building_context_missing')
        return building, await read_revisions(uow, self.building_id)

    async def read_functional_summary(self, content_types, start, end, *, cutoff_at, permissions, unit_of_work):
        """Copy category-event counts and registration coverage in the caller's read capture.

        Permissions are current grants resolved by006. Only002's two event types are
        supported. The permanent category ledger and atomic event writes establish
        history from building registration; before registration/after cutoff are
        known gaps. No query writes coverage evidence or renews a retention deadline.
        Unsupported content is explicitly unknown; DB failures propagate.
        """
        from sqlalchemy import select
        from ecs_ec.audit.models import FunctionalEvent
        from ecs_ec.consumption.models import CategoryUpdate, Period
        if 'consumption.read' not in permissions:
            raise PermissionError('consumption_read_required')
        period = Period(start=start, end=end)
        cutoff = instant(cutoff_at)
        building, _ = await self._context(unit_of_work)
        lower, upper = max(period.start, building.created_at), min(period.end, cutoff)
        covered = [dict(start=lower, end=upper)] if lower < upper else []
        gaps = []
        if period.start < min(period.end, building.created_at):
            gaps.append(dict(start=period.start, end=min(period.end, building.created_at)))
        future_start = max(period.start, cutoff, building.created_at)
        if future_start < period.end:
            gaps.append(dict(start=future_start, end=period.end))
        result = []
        for content in content_types:
            if content not in {'consumption.accepted', 'reception.completed'}:
                result.append(dict(content_type=content, count=None, integrity='desconocida',
                    covered_periods=[], known_gaps=[], limitation_code='unsupported_content', source_refs=[]))
                continue
            events = (await unit_of_work.session.scalars(select(FunctionalEvent).join(CategoryUpdate,
                CategoryUpdate.id == FunctionalEvent.source_entity_id).where(
                CategoryUpdate.building_id == self.building_id, FunctionalEvent.source_module == 'consumption',
                FunctionalEvent.event_type == content, FunctionalEvent.occurred_at >= period.start,
                FunctionalEvent.occurred_at < period.end, FunctionalEvent.recorded_at <= cutoff)
                .order_by(FunctionalEvent.occurred_at, FunctionalEvent.id))).all()
            result.append(dict(content_type=content, count=len(events),
                integrity='incompleta' if gaps else 'completa', covered_periods=covered, known_gaps=gaps,
                limitation_code='outside_registered_history' if gaps else None, source_refs=[e.id for e in events]))
        return tuple(result)

    async def source_status(self, category_id, *, cutoff_at=None, unit_of_work=None):
        """Return actual source/incorporation metadata;900s is admission policy, never an arrival SLA."""
        if category_id not in CATEGORY_IDS:
            raise ValueError('unknown_category')
        if unit_of_work is None:
            async with UnitOfWork(self.database.sessions) as uow:
                await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                return await self.source_status(category_id, cutoff_at=cutoff_at or self.clock.now(), unit_of_work=uow)
        cutoff = cutoff_at or self.clock.now()
        _, revisions = await self._context(unit_of_work)
        visible = [r for r in revisions if r.recorded_at <= cutoff and r.effective_from <= cutoff]
        current = visible[-1] if visible else None
        entry = current.entry(category_id) if current else None
        # A microsecond projection describes the current source, not a measurement interval.
        from datetime import timedelta
        segment = current.segment(category_id, cutoff, cutoff + timedelta(microseconds=1)) if current else None
        update = await self.store.read_update_state(self.building_id, category_id, cutoff, unit_of_work)
        return dict(category_id=category_id, cutoff_at=cutoff, configuration_revision=current.revision if current else None,
            category_revision=entry.category_revision if entry else None, has_meter=entry.has_meter if entry else False,
            source_mode=segment.source_mode if segment else 'unavailable', source_id=entry.source_id if entry else None,
            base_categories=segment.base_categories if segment else (), last_new_data_at=update.last_new_data_at,
            next_admissible_at=update.next_admissible_at)

    async def catalog(self):
        """Return seven current categories and global retained extent in one read-only snapshot."""
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            building, _ = await self._context(uow)
            cutoff = self.clock.now()
            extent = await self.store.read_extent(self.building_id, cutoff, uow)
            period = extent if extent.start is not None else local_day(cutoff, building.timezone)
            categories = []
            for category in CATEGORIES:
                state = await self.source_status(category.id, cutoff_at=cutoff, unit_of_work=uow)
                categories.append(CategoryStatus(**category.model_dump(exclude={'display_order'}),
                    **{key: state[key] for key in ('has_meter', 'source_mode', 'base_categories', 'category_revision')}))
            return Catalog(building_id=self.building_id, timezone=building.timezone, cutoff_at=timestamp(cutoff, building.timezone),
                default_period=PeriodView(start=timestamp(period.start, building.timezone), end=timestamp(period.end, building.timezone), timezone=building.timezone),
                categories=tuple(categories))

    async def query_aggregates(self, selection, principal, unit_of_work=None, *, cutoff_at=None):
        """Copy fully contained calendar blocks and diagnostics in one REPEATABLE READ capture.

        HTTP authorizes through006 middleware. Internal callers must pass a trusted
        principal or an already authorized UoW. No acceptance, candidate evaluation,
        synthetic persistence or retention changes occur in this method.
        """
        from sqlalchemy import select
        from ecs_ec.consumption.aggregates import project_block
        from ecs_ec.consumption.calendar import blocks, containing_block
        from ecs_ec.consumption.models import ConsumptionAggregate, IncorporatedRecord
        from ecs_ec.consumption.ports import AggregateQueryResult, ExcludedBlock, HistoryWarning, ZonedPeriod
        if selection.building_id != self.building_id:
            raise ValueError('building_mismatch')
        if unit_of_work is None:
            async with UnitOfWork(self.database.sessions) as uow:
                await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                return await self.query_aggregates(selection, principal, uow, cutoff_at=cutoff_at or self.clock.now())
        building, revisions = await self._context(unit_of_work)
        if selection.timezone != building.timezone:
            raise InvalidSelection('invalid_timezone')
        cutoff = cutoff_at or self.clock.now()
        revisions = tuple(r for r in revisions if r.recorded_at <= cutoff)
        segments = configuration_segments(revisions, selection.category_id, selection.start, selection.end)
        stored = (await unit_of_work.session.scalars(select(ConsumptionAggregate).where(
            ConsumptionAggregate.building_id == self.building_id, ConsumptionAggregate.category_id == selection.category_id,
            ConsumptionAggregate.granularity == selection.granularity, ConsumptionAggregate.timezone == selection.timezone,
            ConsumptionAggregate.start >= selection.start, ConsumptionAggregate.end <= selection.end,
            ConsumptionAggregate.created_at <= cutoff))).all()
        by_bounds = {(r.start, r.end): r for r in stored}
        records = (await unit_of_work.session.scalars(select(IncorporatedRecord).where(
            IncorporatedRecord.building_id == self.building_id, IncorporatedRecord.category_id == selection.category_id,
            IncorporatedRecord.start < selection.end, IncorporatedRecord.end > selection.start,
            IncorporatedRecord.first_incorporated_at <= cutoff))).all()
        projected, warnings = [], []
        for block in blocks(selection.start, selection.end, selection.granularity, selection.timezone):
            aggregate = by_bounds.get((block.start, block.end))
            if any(r.start < block.end and r.end > block.start for r in stored) and aggregate is None:
                raise ValueError('tzdata_reconciliation_required')
            provenance = configuration_segments(revisions, selection.category_id, block.start, block.end)
            local_warnings = []
            crossing = tuple(r.id for r in records if r.start < block.end and r.end > block.start
                and not (r.start >= block.start and r.end <= block.end))
            if crossing:
                local_warnings.append(HistoryWarning(code='measurement_crosses_block', start=block.start, end=block.end,
                    record_refs=crossing, detail='Mediciones que cruzan límites excluidas; no se reparte su energía.'))
            withdrawn = tuple(r.id for r in records if r.start >= block.start and r.end <= block.end and r.detail_state == 'withdrawn')
            if withdrawn:
                local_warnings.append(HistoryWarning(code='detail_withdrawn', record_refs=withdrawn,
                    detail='Detalle retirado; el agregado conserva sus aportes históricos.'))
            if any(p.source_mode == 'calculated' and len(p.base_categories) < 6 for p in provenance):
                local_warnings.append(HistoryWarning(code='partial_calculation_basis', detail='La base calculada no garantiza cubrir todas las cargas del edificio.'))
            value = project_block(block, aggregate, provenance, cutoff, tuple(local_warnings))
            if value.coverage_state != 'complete':
                value = value.model_copy(update={'warnings': value.warnings + (HistoryWarning(code='missing_coverage',
                    start=block.start, end=block.end, detail='Cobertura incompleta; los huecos no representan consumo cero.'),)})
            projected.append(value)
            warnings.extend(local_warnings)
        excluded = []
        current = containing_block(selection.start, selection.granularity, selection.timezone)
        while current.start < selection.end:
            left, right = current.start < selection.start, current.end > selection.end
            if left or right:
                excluded.append(ExcludedBlock(start=current.start, end=current.end,
                    reason_code='filter_both' if left and right else 'filter_start' if left else 'filter_end'))
            if current.end >= selection.end:
                break
            current = containing_block(current.end, selection.granularity, selection.timezone)
        if excluded:
            warnings.append(HistoryWarning(code='filter_excludes_block', detail='Se excluyeron bloques no contenidos completamente en el filtro.'))
        if not revisions or selection.start < revisions[0].effective_from:
            warnings.append(HistoryWarning(code='unconfigured_period', detail='Parte del período es anterior a la configuración disponible.'))
        if selection.start < building.created_at:
            warnings.append(HistoryWarning(code='before_operation', detail='El período incluye historia anterior al inicio del registro; no se inventan mediciones.'))
        detail = await self.store.read_detail(self.building_id, selection.category_id, selection.start, selection.end, cutoff, unit_of_work)
        modes = {s.source_mode for s in segments}
        mode = next(iter(modes)) if len(modes) == 1 else 'mixed' if modes else 'unavailable'
        if selection.category_id == 'CAT-01' and mode == 'unavailable':
            warnings.append(HistoryWarning(code='no_calculation_basis', detail='No hay categorías presentes para calcular el total.'))
        has_data = any(b.contribution_count for b in projected)
        no_meter = selection.category_id != 'CAT-01' and (not modes or modes == {'unavailable'})
        incomplete = bool(detail.diagnostics) or any(b.coverage_state != 'complete' for b in projected)
        state = 'no_meter' if no_meter else 'incomplete' if detail.diagnostics or has_data and incomplete else 'available' if has_data else 'no_data'
        reason = 'no_complete_blocks' if not projected else 'no_calculation_basis' if selection.category_id == 'CAT-01' and mode == 'unavailable' else 'no_history' if not has_data else None
        return AggregateQueryResult(request_ref=uuid4(), building_id=self.building_id, category_id=selection.category_id,
            period=ZonedPeriod(start=selection.start, end=selection.end, timezone=selection.timezone),
            granularity=selection.granularity, cutoff_at=cutoff, state=state, source_mode=mode,
            configuration_segments=segments, blocks=tuple(projected), excluded_blocks=tuple(excluded),
            diagnostics=detail.diagnostics, warnings=tuple(warnings), reason_code=reason)

    async def latest_admissible_window(self, *, building_id, category_id, resolution, timezone,
            activation_at, cursor, cutoff_at, unit_of_work):
        """Project the latest finished, completely covered window from permanent incorporated evidence.

        Other zones group original ledger intervals directly; no persisted bucket is
        created or summed. Cursor v1 binds selection/window/evidence. It is an
        internal continuation reference, never an authorization credential.
        """
        import base64
        import json
        from sqlalchemy import select
        from ecs_ec.consumption.aggregates import quanta_energy
        from ecs_ec.consumption.calendar import containing_block, duration_us
        from ecs_ec.consumption.models import IncorporatedRecord, Period
        from ecs_ec.consumption.ports import AdmissibleWindow
        from ecs_ec.core.timezones import iana_zone
        if building_id != self.building_id or category_id not in CATEGORY_IDS:
            raise ValueError('invalid_selection')
        iana_zone(timezone)
        if resolution not in {'intervalo', 'hour', 'day', 'month', 'year'}:
            raise ValueError('invalid_resolution')
        activation, cutoff = instant(activation_at), instant(cutoff_at)
        binding = [str(building_id), category_id, resolution, timezone]
        previous = None
        if cursor is not None:
            try:
                previous = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
                if set(previous) != {'v', 'selection', 'start', 'end', 'revision'} or previous['v'] != 1 or previous['selection'] != binding:
                    raise ValueError()
                Period(start=previous['start'], end=previous['end'])
                if not isinstance(previous['revision'], str) or len(previous['revision']) != 64:
                    raise ValueError()
            except (ValueError, TypeError, KeyError, UnicodeError):
                raise ValueError('invalid_cursor') from None
        _, revisions = await self._context(unit_of_work)
        revisions = tuple(r for r in revisions if r.recorded_at <= cutoff)
        records = (await unit_of_work.session.scalars(select(IncorporatedRecord).where(
            IncorporatedRecord.building_id == building_id, IncorporatedRecord.category_id == category_id,
            IncorporatedRecord.first_incorporated_at <= cutoff, IncorporatedRecord.end <= cutoff,
            IncorporatedRecord.start >= activation).order_by(IncorporatedRecord.start, IncorporatedRecord.id))).all()
        candidates = {}
        for record in records:
            if resolution == 'intervalo':
                bounds = (record.start, record.end)
            else:
                block = containing_block(record.start, resolution, timezone)
                if record.end > block.end:
                    continue
                bounds = (block.start, block.end)
            if bounds[0] >= activation and bounds[1] <= cutoff:
                candidates.setdefault(bounds, []).append(record)
        for (start, end), rows in sorted(candidates.items(), key=lambda item: (item[0][1], item[0][0]), reverse=True):
            if previous and end < instant(previous['end']):
                continue
            covered = sum(duration_us(r.start, r.end) for r in rows)
            if covered != duration_us(start, end):
                continue
            segments = configuration_segments(revisions, category_id, start, end)
            if not segments or segments[0].start != start or segments[-1].end != end or any(s.source_mode == 'unavailable' for s in segments):
                continue
            modes = {s.source_mode for s in segments}
            mode = next(iter(modes)) if len(modes) == 1 else 'mixed'
            revision = evidence_revision(rows, segments, timezone)
            encoded = base64.urlsafe_b64encode(json.dumps(dict(v=1, selection=binding,
                start=start.isoformat(), end=end.isoformat(), revision=revision), sort_keys=True).encode()).decode()
            return AdmissibleWindow(status='available', building_id=building_id, category_id=category_id,
                resolution=resolution, timezone=timezone, cutoff_at=cutoff, period=Period(start=start, end=end),
                energy_kwh=decimal_text(quanta_energy(sum(int(r.energy_quanta) for r in rows))),
                duration_us=str(covered), covered_duration_us=str(covered), source_mode=mode,
                configuration_segments=segments, record_refs=tuple(r.id for r in rows), evidence_revision=revision,
                cursor=encoded, reason_code=None)
        status = await self.source_status(category_id, cutoff_at=cutoff, unit_of_work=unit_of_work)
        return AdmissibleWindow(status='not_evaluable', building_id=building_id, category_id=category_id,
            resolution=resolution, timezone=timezone, cutoff_at=cutoff, period=None, energy_kwh=None,
            duration_us='0', covered_duration_us='0', source_mode=status['source_mode'], configuration_segments=(),
            record_refs=(), evidence_revision=None, cursor=cursor,
            reason_code='no_source' if status['source_mode'] == 'unavailable' else 'no_complete_window')

    async def read_general_snapshot(self, building_id, start, end, cutoff_at, unit_of_work):
        """Copy retained physicalCAT-01 evidence and explicit coverage limitations for004; apply no tariffs."""
        from ecs_ec.consumption.calendar import duration_us
        from ecs_ec.consumption.ports import PhysicalHistorySnapshot, ZonedPeriod
        if building_id != self.building_id:
            raise ValueError('building_mismatch')
        building, revisions = await self._context(unit_of_work)
        period = ZonedPeriod(start=start, end=end, timezone=building.timezone)
        revisions = tuple(r for r in revisions if r.recorded_at <= cutoff_at)
        segments = configuration_segments(revisions, 'CAT-01', period.start, period.end)
        detail = await self.store.read_detail(building_id, 'CAT-01', period.start, period.end, cutoff_at, unit_of_work)
        physical = tuple(r for r in detail.rows if r.kind == 'measured')
        covered = sum(duration_us(r.start, r.end) for r in physical)
        reason = 'calculated_general' if any(s.source_mode == 'calculated' for s in segments) else (
            'no_source' if not segments or all(s.source_mode == 'unavailable' for s in segments) else
            'insufficient_evidence' if covered != duration_us(period.start, period.end) else None)
        return PhysicalHistorySnapshot(building_id=building_id, period=period, cutoff_at=cutoff_at,
            rows=physical, configuration_segments=segments, evidence_revision=evidence_revision(physical, segments, building.timezone), reason_code=reason)

    async def read_demand_history(self, building_id, start, end, cutoff_at, unit_of_work):
        """Expose only original exact900-second physical intervals; never split hourly energy into quarters."""
        from ecs_ec.consumption.calendar import duration_us
        snapshot = await self.read_general_snapshot(building_id, start, end, cutoff_at, unit_of_work)
        if snapshot.reason_code is None and any(duration_us(r.start, r.end) != 900000000 for r in snapshot.rows):
            return snapshot.model_copy(update={'reason_code': 'insufficient_resolution'})
        return snapshot

    async def read_report_snapshot(self, building_id, start, end, scale, cutoff_at, principal, *, unit_of_work):
        """Copy seven categories at the caller's capture for005, without rendering PDF or reproducing past DB state.

        The caller owns a REPEATABLE READ transaction and current authorization.
        A date alone cannot reproduce an earlier revision: consumers persist this snapshot.
        """
        from ecs_ec.consumption.ports import AggregateSelection, ZonedPeriod
        if building_id != self.building_id:
            raise ValueError('building_mismatch')
        building, revisions = await self._context(unit_of_work)
        period = ZonedPeriod(start=start, end=end, timezone=building.timezone)
        revisions = tuple(r for r in revisions if r.recorded_at <= cutoff_at)
        categories = []
        for category in CATEGORIES:
            detail = await self.store.read_detail(building_id, category.id, period.start, period.end, cutoff_at, unit_of_work)
            aggregates = None if scale in {'detail', 'intervalo'} else await self.query_aggregates(AggregateSelection(
                building_id=building_id, category_id=category.id, granularity=scale,
                start=period.start, end=period.end, timezone=building.timezone), principal, unit_of_work, cutoff_at=cutoff_at)
            segments = configuration_segments(revisions, category.id, period.start, period.end)
            categories.append(dict(category=category.model_dump(), detail=detail, aggregates=aggregates,
                provenance_segments=segments, evidence_revision=evidence_revision(detail.rows, segments, building.timezone)))
        return dict(building_id=building_id, period=period, cutoff_at=cutoff_at, categories=tuple(categories))

    async def detail(self, category_id, start, end, timezone):
        """Copy fully contained rows with captured provenance; do not recalculate or renew retention."""
        if category_id not in CATEGORY_IDS:
            raise ValueError('unknown_category')
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            building, revisions = await self._context(uow)
            try:
                period = resolve_period(start, end, timezone, building.timezone)
            except (ValueError, TypeError, OverflowError):
                raise InvalidSelection('invalid_period') from None
            cutoff = self.clock.now()
            revisions = tuple(r for r in revisions if r.recorded_at <= cutoff)
            segments = configuration_segments(revisions, category_id, period.start, period.end)
            stored = await self.store.read_detail(self.building_id, category_id, period.start, period.end, cutoff, uow)
            rows = tuple(row_view(row, timezone) for row in sorted(stored.rows, key=lambda r: (r.start, r.end, r.record_id)))
            diagnostics = tuple(diagnostic_view(d, timezone) for d in stored.diagnostics)
            warnings = []
            if stored.crossing_record_ids or stored.crossing_diagnostic_ids:
                warnings.append(warning('crossing_intervals_excluded', len(set(stored.crossing_record_ids) | set(stored.crossing_diagnostic_ids)), 'Se excluyeron intervalos que cruzan los límites.'))
            if stored.withdrawn_record_ids:
                warnings.append(warning('detail_withdrawn', len(stored.withdrawn_record_ids), 'Detalle retirado; los agregados conservan sus aportes históricos.'))
            gaps = sum(left.end < right.start for left, right in zip(stored.rows, stored.rows[1:]))
            if gaps:
                warnings.append(warning('observed_gaps', gaps, 'Hay huecos entre intervalos observados; no se interpretan como cero.'))
            unavailable = sum(s.source_mode == 'unavailable' for s in segments)
            if unavailable:
                warnings.append(warning('source_unavailable_in_segment', unavailable, 'Hay segmentos sin fuente disponible.'))
            if category_id == 'CAT-01':
                if not segments or all(s.source_mode == 'unavailable' for s in segments):
                    warnings.append(warning('no_calculation_basis', 1, 'No hay categorías presentes para calcular el total.'))
                partial = sum(s.source_mode == 'calculated' and len(s.base_categories) < 6 for s in segments)
                if partial:
                    warnings.append(warning('partial_calculation_scope', partial, 'La base calculada no garantiza cubrir todas las cargas del edificio.'))
            modes = {s.source_mode for s in segments}
            mode = next(iter(modes)) if len(modes) == 1 else 'mixed' if modes else 'unavailable'
            state = ('incomplete' if diagnostics else 'available' if rows else
                'no_meter' if category_id != 'CAT-01' and (not modes or modes == {'unavailable'}) else 'no_data')
            category = next(c for c in CATEGORIES if c.id == category_id)
            return DetailResult(request_ref=uuid4(), building_id=self.building_id,
                category=CategoryView(**category.model_dump(exclude={'display_order'})),
                period=PeriodView(start=timestamp(period.start, timezone), end=timestamp(period.end, timezone), timezone=timezone),
                cutoff_at=timestamp(cutoff, timezone), state=state, source_mode=mode,
                configuration_segments=tuple(segment_view(s, timezone) for s in segments),
                rows=rows, diagnostics=diagnostics, warnings=tuple(warnings))


def decimal_text(value):
    """Produce fixed exact decimal text, removing only insignificant fractional zeros."""
    from decimal import Decimal
    result = format(Decimal(value), 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def segment_view(segment, timezone):
    """Project UTC boundaries to the building zone while excluding internal basis revision helpers."""
    return SegmentView(**segment.model_dump(exclude={'start', 'end'}),
        start=timestamp(segment.start, timezone), end=timestamp(segment.end, timezone))


def row_view(row, timezone):
    """Copy original or captured calculated evidence without arithmetic or joining live sources."""
    snapshot = row.provenance_snapshot
    if row.kind == 'measured':
        origin = dict(kind='measured', source_id=snapshot['source_id'],
            original_value=row.original_value_text, original_unit=row.original_unit)
    else:
        contributions = []
        for item in snapshot['contributions']:
            contributions.append(item | dict(start=timestamp(instant(item['start']), timezone),
                end=timestamp(instant(item['end']), timezone), energy_kwh=decimal_text(item['energy_kwh'])))
        origin = dict(kind='calculated', base_categories=snapshot['base_categories'], contributions=tuple(contributions))
    return DetailRow(record_id=row.record_id, revision=row.revision, start=timestamp(row.start, timezone),
        end=timestamp(row.end, timezone), energy_kwh=decimal_text(row.energy_kwh),
        first_incorporated_at=timestamp(row.first_incorporated_at, timezone),
        configuration_revision=snapshot.get('configuration_revision') or snapshot['configuration_segments'][0]['configuration_revision'],
        category_revision=snapshot['category_revision'], origin=origin)


def diagnostic_view(diagnostic, timezone):
    """Expose nonnumeric reason/segments and preserve the absence of next-admission evidence."""
    return Diagnostic(start=timestamp(diagnostic.start, timezone), end=timestamp(diagnostic.end, timezone),
        configuration_revision=diagnostic.configuration_segments[0].configuration_revision,
        category_revision=diagnostic.category_revision, reason_code=diagnostic.reason_code,
        missing_categories=diagnostic.missing_categories,
        next_admissible_at=timestamp(diagnostic.next_admissible_at, timezone) if diagnostic.next_admissible_at else None,
        configuration_segments=tuple(segment_view(s, timezone) for s in diagnostic.configuration_segments))


def warning(code, count, message):
    """Construct only static safe warnings; raw storage errors are never included."""
    return WarningView(code=code, count=count, message=message)


def evidence_revision(rows, segments, timezone):
    """Hash canonical immutable record/revision/interval/provenance identities plus pinned calendar rules."""
    import hashlib
    import json
    from ecs_ec.consumption.calendar import TZDATA_VERSION
    evidence = dict(timezone=timezone, tzdata_version=TZDATA_VERSION,
        records=sorted((str(getattr(r, 'record_id', None) or r.id), r.revision, r.start.isoformat(), r.end.isoformat()) for r in rows),
        segments=[s.model_dump(mode='json') for s in segments])
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class FunctionalSummary:
    """002 implementation of009's read-only summary boundary;008 composes this provider with other producers."""

    def __init__(self, consumption):
        """Bind the existing singleton facade and its concrete storage, without adding a writer or consumer."""
        self.consumption = consumption

    async def read(self, content_types, start, end, *, cutoff_at, permissions, unit_of_work):
        """Use current006 permissions and the caller's shared capture; return one item for every requested content."""
        return await self.consumption.read_functional_summary(content_types, start, end,
            cutoff_at=cutoff_at, permissions=permissions, unit_of_work=unit_of_work)
