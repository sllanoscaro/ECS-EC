"""004 manual invoice append/correction; no OCR, uploads, meter changes or automatic comparisons."""

import unicodedata
from uuid import uuid4
from sqlalchemy import select

from ecs_ec.costs.models import Bill, BillRevision, BillLine, BillingCycle
from ecs_ec.costs.money import number
from ecs_ec.costs.repository import CostsProblem
from ecs_ec.costs.schemas import BillInput
from ecs_ec.core.retention import anniversary


def normalize_identifier(value):
    """NormalizeNFKC/casefold and collapsed whitespace for document identity, retaining original text in each revision."""
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


async def append_bill(uow, supply, command, actor_ref, clock, *, bill_id=None, expected_revision=None):
    """Append an immutable document revision under the caller's building lock; identical registrations reuse a resource."""
    command = BillInput.model_validate(command)
    body = command.model_dump(mode='json')
    identifier = normalize_identifier(command.external_identifier)
    if not identifier:
        raise CostsProblem('bill_identifier_required', 422)
    if bill_id:
        bill = await uow.session.get(Bill, bill_id)
        if bill is None or bill.supply_id != supply.id:
            raise CostsProblem('bill_not_found', 404)
        if identifier != bill.external_identifier_normalized:
            raise CostsProblem('bill_identifier_immutable', 422)
    else:
        bill = await uow.session.scalar(select(Bill).where(Bill.supply_id == supply.id, Bill.external_identifier_normalized == identifier))
    previous = await uow.session.scalar(select(BillRevision).where(BillRevision.bill_id == bill.id).order_by(BillRevision.revision.desc()).limit(1)) if bill else None
    if bill_id:
        if expected_revision != previous.revision:
            raise CostsProblem('bill_revision_conflict', 412)
    elif previous:
        if (previous.data | {'external_identifier': identifier}) == (body | {'external_identifier': identifier}):
            return previous, False
        raise CostsProblem('bill_identifier_conflict')
    now = clock.now()
    retained = dict(created_at=now, actor_ref=actor_ref, retain_until=anniversary(now, command.timezone))
    if bill is None:
        bill = Bill(id=uuid4(), supply_id=supply.id, external_identifier_normalized=identifier, **retained)
        uow.session.add(bill)
        await uow.session.flush()
    cycle = await uow.session.scalar(select(BillingCycle).where(BillingCycle.supply_id == supply.id,
        BillingCycle.start_at == command.start, BillingCycle.end_at == command.end))
    if cycle is None:
        cycle = BillingCycle(id=uuid4(), supply_id=supply.id, start_at=command.start, end_at=command.end, timezone=command.timezone,
            data=dict(boundary_criterion=command.boundary_criterion, boundary_limited=command.boundary_limited,
                declared_start=command.declared_start, declared_end=command.declared_end), **retained)
        uow.session.add(cycle)
        await uow.session.flush()
    revision = BillRevision(id=uuid4(), bill_id=bill.id, cycle_id=cycle.id, revision=previous.revision + 1 if previous else 1,
        previous_id=previous.id if previous else None, data=body, **retained)
    uow.session.add(revision)
    await uow.session.flush()
    for line in command.lines:
        uow.session.add(BillLine(id=uuid4(), bill_revision_id=revision.id, code=line.code, amount=number(line.amount),
            quantity=number(line.quantity) if line.quantity is not None else None,
            tax_amount=number(line.tax_amount) if line.tax_amount is not None else None,
            data=line.model_dump(mode='json'), **retained))
    for parent in (bill, cycle, supply):
        parent.retain_until = max(parent.retain_until, revision.retain_until)
    return revision, previous is None
