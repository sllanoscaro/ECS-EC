"""004 physical input capture on001/002 and shared009 REPEATABLE READ UoW; no source reconstruction."""

from dataclasses import replace

from ecs_ec.costs.calendar import history_window, resolve_month
from ecs_ec.costs.models import Supply
from ecs_ec.costs.repository import selected_profile
from ecs_ec.costs.schemas import InputEvidence, ProfileInput, SupplyInput, PhysicalBlock


def copy_block(row):
    """Copy all original quantitative evidence needed after002's original payload expires."""
    return PhysicalBlock(record_id=row.record_id, revision=row.revision, category_revision=row.provenance_snapshot['category_revision'],
        configuration_revision=row.provenance_snapshot['configuration_revision'], source_id=row.provenance_snapshot['source_id'],
        start=row.start, end=row.end, energy_kwh=format(row.energy_kwh, 'f'), original_value=row.original_value_text,
        original_unit=row.original_unit)


async def capture(uow, *, consumption, supply_id, request, cutoff_at):
    """Capture actual supply, one published profile and physical inputs inside the caller's coherent read transaction."""
    supply = await uow.session.get(Supply, supply_id)
    profile = await selected_profile(uow, supply_id, cutoff_at)
    source, history, general_reason, history_reason = (), (), 'insufficient_evidence', 'insufficient_evidence'
    end = min(request.end, cutoff_at)
    if request.start < end:
        general = await consumption.read_general_snapshot(supply.building_id, request.start, end, cutoff_at, uow)
        source = tuple(copy_block(row) for row in general.rows)
        general_reason = general.reason_code
    evidence = InputEvidence(request=request, cutoff_at=cutoff_at, supply_id=supply.id, supply_revision=supply.revision,
        supply=SupplyInput.model_validate(supply.data), profile_id=profile.id if profile else None,
        profile_revision=profile.revision if profile else None, profile=ProfileInput.model_validate(profile.data) if profile else None,
        measurements=source, general_reason=general_reason, history=history, history_reason=history_reason,
        billing_month_ref=None, billing_month_source_ref=None, billing_month_policy_version=None)
    month, month_source, policy = resolve_month(evidence)
    if month:
        lower, upper = history_window(month, request.timezone)
        history_snapshot = await consumption.read_demand_history(supply.building_id, lower, upper, cutoff_at, uow)
        history = tuple(copy_block(row) for row in history_snapshot.rows)
        history_reason = history_snapshot.reason_code
    return evidence.model_copy(update=dict(billing_month_ref=month, billing_month_source_ref=month_source,
        billing_month_policy_version=policy, history=history, history_reason=history_reason))


async def read_snapshot(service, building_id, start, end, cutoff_at, principal, *, unit_of_work=None):
    """Read closed effective cycles for005 in a supplied or owned REPEATABLE READ UoW; never create resources."""
    from sqlalchemy import select, text
    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.consumption.models import Period, instant
    from ecs_ec.costs.models import BillingCycle
    from ecs_ec.costs.history import cycle_view, aggregates
    from ecs_ec.costs.schemas import CostsSnapshot
    from ecs_ec.costs.repository import CostsProblem
    service.authorize(principal)
    if building_id != service.building_id:
        raise CostsProblem('building_not_found', 404)
    period, cutoff = Period(start=start, end=end), instant(cutoff_at)
    if unit_of_work is None:
        async with UnitOfWork(service.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            return await read_snapshot(service, building_id, period.start, period.end, cutoff, principal, unit_of_work=uow)
    if await unit_of_work.session.scalar(text('SHOW transaction_isolation')) not in {'repeatable read', 'serializable'}:
        raise CostsProblem('snapshot_isolation_required', 503)
    supply = await unit_of_work.session.scalar(select(Supply).where(Supply.building_id == building_id))
    rows = (await unit_of_work.session.scalars(select(BillingCycle).where(BillingCycle.supply_id == supply.id,
        BillingCycle.end_at >= period.start, BillingCycle.end_at < period.end, BillingCycle.end_at <= cutoff,
        BillingCycle.created_at <= cutoff).order_by(BillingCycle.end_at, BillingCycle.id))).all() if supply else []
    cycles = []
    for row in rows:
        value = await cycle_view(service, unit_of_work, row, cutoff)
        limited = (value.calculation.snapshot.request.boundary_limited if value.calculation else
            value.bill.boundary_limited if value.bill else row.data.get('boundary_limited', False))
        if not limited:
            cycles.append(value)
    available, comparable = aggregates(cycles)
    reasons = []
    if not cycles:
        reasons.append('no_closed_cycles')
    if not any(cycle.bill for cycle in cycles):
        reasons.append('no_bills')
    if not comparable:
        reasons.append('no_comparable_pairs')
    return CostsSnapshot(building_id=building_id, supply_id=supply.id if supply else None,
        start=period.start, end=period.end, timezone=service.timezone, cutoff_at=cutoff, cycles=tuple(cycles),
        available_totals=available, comparison_totals=comparable,
        complete_cycle_count=sum(c.calculation is not None and c.calculation.sufficiency == 'completo' for c in cycles),
        partial_cycle_count=sum(c.calculation is not None and c.calculation.sufficiency == 'parcial' for c in cycles),
        uncalculable_cycle_count=sum(c.calculation is None or c.calculation.sufficiency == 'no_calculable' for c in cycles),
        failed_cycle_count=sum(c.calculation is not None and c.calculation.execution_state == 'fallido' for c in cycles), reason_codes=reasons)
