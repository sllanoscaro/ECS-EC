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
            if stored.crossing_record_ids:
                warnings.append(warning('crossing_intervals_excluded', len(set(stored.crossing_record_ids)), 'Se excluyeron intervalos que cruzan los límites.'))
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
