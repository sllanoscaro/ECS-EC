"""002 PostgreSQL ledger primitives and read providers; caller owns locks, capture and commit."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from ecs_ec.consumption.aggregates import contribute, energy_quanta
from ecs_ec.consumption.calendar import TZDATA_VERSION
from ecs_ec.consumption.catalog import CATEGORY_IDS
from ecs_ec.consumption.catalog_storage import lock_configuration, read_revisions
from ecs_ec.consumption.models import (AcceptedMeasurement, BuildingReceptionState, CategoryReceptionState,
    IncorporatedRecord, IncorporatedTotal, ReconfigurationBounds, TotalCalculationState)
from ecs_ec.consumption.ports import CalculationDiagnostic, DetailRead, HistoryExtent, StoredDetail, UpdateState
from ecs_ec.consumption.retention import retention_deadline


async def lock_history(uow, building_id, category_ids=CATEGORY_IDS):
    """Acquire001 context/category locks, verify all seven durable states, return context and history.

    Missing state is corruption/unavailable evidence, never an empty history. The migration
    initializes existing/new contexts without fabricating acceptances. All writes must call
    this before reading configuration, requests, identities, aggregates or the current clock.
    """
    building = await lock_configuration(uow, building_id, category_ids)
    if building is None: raise ValueError('building_context_missing')
    states = (await uow.session.scalars(select(CategoryReceptionState).where(
        CategoryReceptionState.building_id == building_id).order_by(CategoryReceptionState.category_id).with_for_update())).all()
    global_state = await uow.session.get(BuildingReceptionState, building_id)
    if global_state is None or tuple(s.category_id for s in states) != CATEGORY_IDS:
        raise ValueError('history_state_unavailable')
    return building, {s.category_id: s for s in states}, global_state, await read_revisions(uow, building_id)


async def classify(uow, measurement):
    """Compare normalized identity/value before timing; return durable duplicate/conflict/overlap or new."""
    overlapping = (await uow.session.scalars(select(IncorporatedRecord).where(
        IncorporatedRecord.building_id == measurement.building_id,
        IncorporatedRecord.category_id == measurement.category_id,
        IncorporatedRecord.start < measurement.end, IncorporatedRecord.end > measurement.start))).all()
    for row in overlapping:
        if row.source_id == measurement.source_id and row.start == measurement.start and row.end == measurement.end:
            return ('duplicate' if row.energy_kwh == measurement.energy_kwh else 'conflicting_duplicate'), row
    return ('overlapping_interval', None) if overlapping else ('new', None)


def advance_state(state, global_state, records, now):
    """Advance once for committed novelties; caller must include this in their category transaction."""
    if not records: return
    state.last_new_data_at = now
    state.next_admissible_at = now + timedelta(seconds=900)
    state.latest_interval_end = max([r.end for r in records] + ([state.latest_interval_end] if state.latest_interval_end else []))
    state.revision += 1
    global_state.has_accepted_history = True
    global_state.first_new_data_at = global_state.first_new_data_at or now


async def incorporate_measurement(uow, measurement, update, now, timezone):
    """Persist first original, ledger and all direct aggregates in caller UoW; no independent commit."""
    deadline = retention_deadline(now, timezone)
    row = IncorporatedRecord(id=uuid4(), revision=1, building_id=measurement.building_id,
        category_id=measurement.category_id, kind='measured', source_id=measurement.source_id, logical_source_key=None,
        start=measurement.start, end=measurement.end, energy_kwh=measurement.energy_kwh,
        energy_quanta=energy_quanta(measurement.energy_kwh), configuration_revision=measurement.configuration_revision,
        category_revision=measurement.category_revision, first_incorporated_at=now, update_id=update.id,
        source_evidence_ref=measurement.source_evidence_ref, correlation_ref=measurement.correlation_ref,
        provenance_snapshot=dict(mode='measured', source_id=str(measurement.source_id), category_revision=measurement.category_revision,
            configuration_revision=measurement.configuration_revision), detail_state='retained', detail_withdrawn_at=None,
        retain_until=deadline, retention_timezone=timezone, tzdata_version=TZDATA_VERSION)
    uow.session.add(row)
    await uow.session.flush()
    uow.session.add(AcceptedMeasurement(record_id=row.id, original_value=measurement.original_value,
        original_unit=measurement.original_unit, original_value_text=measurement.original_value_text,
        first_accepted_at=now, retain_until=deadline))
    await contribute(uow, row, now)
    return row


class MeasurementStore:
    """Read-only002 provider for001 and consumers; UoW/cutoff come from the composed caller."""

    async def read_reconfiguration_bounds(self, building_id, category_ids, unit_of_work):
        """Read permanent exact maxima after shared locks; missing provider state raises instead of null."""
        from sqlalchemy import text
        if await unit_of_work.session.scalar(text('SHOW transaction_isolation')) != 'read committed':
            raise ValueError('bounds_require_read_committed')
        if any(c not in CATEGORY_IDS for c in category_ids): raise ValueError('unknown_category')
        global_state = await unit_of_work.session.get(BuildingReceptionState, building_id)
        rows = (await unit_of_work.session.scalars(select(CategoryReceptionState).where(
            CategoryReceptionState.building_id == building_id, CategoryReceptionState.category_id.in_(category_ids)))).all()
        if global_state is None or len(rows) != len(set(category_ids)): raise ValueError('history_state_unavailable')
        return ReconfigurationBounds(has_accepted_history=global_state.has_accepted_history,
            latest_interval_end_by_category={r.category_id: r.latest_interval_end for r in rows})

    async def read_detail(self, building_id, category_id, start, end, cutoff_at, unit_of_work):
        """Copy contained retained payloads; report boundary crossings and withdrawn IDs without recreating originals."""
        from ecs_ec.consumption.models import Period
        period = Period(start=start, end=end)
        rows = (await unit_of_work.session.scalars(select(IncorporatedRecord).where(
            IncorporatedRecord.building_id == building_id, IncorporatedRecord.category_id == category_id,
            IncorporatedRecord.start < period.end, IncorporatedRecord.end > period.start,
            IncorporatedRecord.first_incorporated_at <= cutoff_at).order_by(IncorporatedRecord.start))).all()
        details, crossings, withdrawn = [], [], []
        for row in rows:
            if row.start < period.start or row.end > period.end:
                crossings.append(row.id)
                continue
            if row.detail_state == 'withdrawn':
                withdrawn.append(row.id)
                continue
            original = await unit_of_work.session.get(AcceptedMeasurement, row.id) if row.kind == 'measured' else None
            if row.kind == 'measured' and original is None: raise ValueError('retained_payload_unavailable')
            if row.kind == 'calculated' and await unit_of_work.session.get(IncorporatedTotal, row.id) is None:
                raise ValueError('retained_payload_unavailable')
            details.append(StoredDetail(record_id=row.id, revision=row.revision, category_id=row.category_id, kind=row.kind,
                start=row.start, end=row.end, energy_kwh=row.energy_kwh,
                original_value_text=original.original_value_text if original else None,
                original_unit=original.original_unit if original else None,
                first_incorporated_at=row.first_incorporated_at, retain_until=row.retain_until,
                provenance_snapshot=row.provenance_snapshot))
        diagnostics = (await unit_of_work.session.scalars(select(TotalCalculationState).where(
            TotalCalculationState.building_id == building_id, TotalCalculationState.start < period.end,
            TotalCalculationState.end > period.start, TotalCalculationState.updated_at <= cutoff_at,
            TotalCalculationState.status != 'incorporated').order_by(TotalCalculationState.start))).all() if category_id == 'CAT-01' else []
        projected = tuple(CalculationDiagnostic(id=d.id, revision=d.revision, start=d.start, end=d.end, status=d.status,
            reason_code=d.reason_code, category_revision=None if d.reason_code == 'calculation_configuration_changed' else d.configuration_segments[0]['category_revision'],
            configuration_segments=tuple(d.configuration_segments), base_categories=tuple(d.base_categories),
            contributions=tuple(d.contribution_refs), missing_categories=tuple(d.missing_categories),
            next_admissible_at=d.next_admissible_at) for d in diagnostics if d.start >= period.start and d.end <= period.end)
        crossing_diagnostics = tuple(d.id for d in diagnostics if d.start < period.start or d.end > period.end)
        return DetailRead(rows=tuple(details), crossing_record_ids=tuple(crossings), withdrawn_record_ids=tuple(withdrawn), diagnostics=projected, crossing_diagnostic_ids=crossing_diagnostics)

    async def read_extent(self, building_id, cutoff_at, unit_of_work):
        """Return global retained payload extent; permanent withdrawn history does not fabricate detail."""
        start, end = (await unit_of_work.session.execute(select(func.min(IncorporatedRecord.start), func.max(IncorporatedRecord.end)).where(
            IncorporatedRecord.building_id == building_id, IncorporatedRecord.detail_state == 'retained',
            IncorporatedRecord.first_incorporated_at <= cutoff_at))).one()
        return HistoryExtent(start=start, end=end)

    async def read_update_state(self, building_id, category_id, cutoff_at, unit_of_work):
        """Return durable category state in the caller's coherent capture; cutoff is capture metadata, not time travel."""
        row = await unit_of_work.session.get(CategoryReceptionState, (building_id, category_id))
        if row is None: raise ValueError('history_state_unavailable')
        return UpdateState(last_new_data_at=row.last_new_data_at, next_admissible_at=row.next_admissible_at,
            latest_interval_end=row.latest_interval_end, revision=row.revision)
