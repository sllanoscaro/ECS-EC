"""004 nondecreasing calendar retention and protection of immutable financial parents/children; no automatic purge."""

from sqlalchemy import select

from ecs_ec.core.retention import anniversary
from ecs_ec.costs.models import (Supply, ProfileVersion, ProfileSegment, ProfileCharge, BillingCycle,
    InputSnapshot, Calculation, CalculationComponent, Bill, BillRevision, BillLine, Comparison, ComparisonLine)


def deadline(created_at, timezone, previous=None):
    """Return at least twelve calendar months from the substantive revision, never365 days or query time."""
    value = anniversary(created_at, timezone)
    return max(previous, value) if previous is not None else value


async def protect(uow, row, until):
    """Extend a trusted dependent's entire owned evidence graph without shortening deadlines or deleting anything.

    Callers own the mutation UoW and must use the common building lock before changing
    this graph. Original002 payloads need not outlive their own policy:004 captures all
    reproduction values, while the source ledger/configuration references stay permanent.
    """
    pending, seen = [row], set()
    while pending:
        current = pending.pop()
        identity = (type(current), current.id)
        if identity in seen:
            continue
        seen.add(identity)
        current.retain_until = max(current.retain_until, until)
        references, children = [], []
        if isinstance(current, Comparison):
            references = [(Calculation,current.calculation_id),(BillRevision,current.bill_revision_id)]
            children = [(ComparisonLine, ComparisonLine.comparison_id)]
        elif isinstance(current, Calculation):
            references = [(InputSnapshot,current.snapshot_id),(BillingCycle,current.cycle_id),(Calculation,current.previous_id)]
            children = [(CalculationComponent, CalculationComponent.calculation_id)]
        elif isinstance(current, InputSnapshot):
            references = [(ProfileVersion,current.profile_version_id),(BillingCycle,current.cycle_id)]
        elif isinstance(current, ProfileVersion):
            references = [(Supply,current.supply_id),(ProfileVersion,current.previous_version_id)]
            children = [(ProfileSegment, ProfileSegment.profile_version_id)]
        elif isinstance(current, ProfileSegment):
            children = [(ProfileCharge, ProfileCharge.segment_id)]
        elif isinstance(current, BillRevision):
            references = [(Bill,current.bill_id),(BillingCycle,current.cycle_id),(BillRevision,current.previous_id)]
            children = [(BillLine, BillLine.bill_revision_id)]
        elif isinstance(current, (Bill, BillingCycle)):
            references = [(Supply,current.supply_id)]
        for model, identifier in references:
            if identifier is not None:
                parent = await uow.session.get(model, identifier)
                if parent is None:
                    raise ValueError('financial_evidence_missing')
                pending.append(parent)
        for model, foreign_key in children:
            pending.extend((await uow.session.scalars(select(model).where(foreign_key == current.id))).all())
