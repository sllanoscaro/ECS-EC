"""004 repository primitives: deterministic published selection and coherent resource projections."""

from sqlalchemy import select

from ecs_ec.costs.models import ProfileVersion


async def selected_profile(uow, supply_id, cutoff_at, *, published=True):
    """Select exactly one latest visible complete revision; drafts never contribute segments to a publication."""
    query = select(ProfileVersion).where(ProfileVersion.supply_id == supply_id, ProfileVersion.created_at <= cutoff_at)
    if published:
        query = query.where(ProfileVersion.publication_state == 'published')
    return await uow.session.scalar(query.order_by(ProfileVersion.revision.desc()).limit(1))


def view(row):
    """Detach a JSON-compatible resource projection; internal ORM state and credentials never cross HTTP."""
    return dict(id=str(row.id), revision=row.revision, created_at=row.created_at.isoformat(),
        retain_until=row.retain_until.isoformat(), **row.data)


class CostsProblem(Exception):
    """Fixed code/status domain failure; HTTP adapters provide the safe static explanation."""

    def __init__(self, code, status=409):
        """Store a trusted bounded code, never stringify submitted data or a caught infrastructure exception."""
        self.code, self.status = code, status
        super().__init__(code)


async def replay(uow, actor_ref, operation, key, body):
    """Serialize a trusted actor/operation/key and replay its original response before new preconditions.

    Authorization belongs to the caller and must precede this method. The database lock
    also covers the initially absent row, so concurrent replays cannot create two revisions.
    """
    from sqlalchemy import text
    from ecs_ec.costs.money import digest
    from ecs_ec.costs.models import Idempotency
    if not isinstance(key, str) or not 1 <= len(key) <= 128 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise CostsProblem('idempotency_key_required', 422)
    lock = int(digest([actor_ref, operation, key])[:16], 16)
    if lock >= 2**63:
        lock -= 2**64
    await uow.session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock})
    row = await uow.session.scalar(select(Idempotency).where(Idempotency.actor_ref == actor_ref,
        Idempotency.operation == operation, Idempotency.key == key))
    if row and row.request_hash != digest(body):
        raise CostsProblem('idempotency_conflict')
    return row


async def remember(uow, actor_ref, operation, key, body, response, status, clock, timezone):
    """Persist the idempotent response together with its resource/evidence, never independently commit."""
    from uuid import UUID, uuid4
    from ecs_ec.costs.models import Idempotency
    from ecs_ec.costs.money import digest
    from ecs_ec.core.retention import anniversary
    now = clock.now()
    row = Idempotency(id=uuid4(), actor_ref=actor_ref, operation=operation, key=key,
        request_hash=digest(body), resource_id=UUID(response['id']), http_status=status, response=response,
        created_at=now, retain_until=anniversary(now, timezone))
    uow.session.add(row)
    return row


async def selected_pair(uow, cycle_id, cutoff_at):
    """Select latest calculation/bill first, then only the comparison of that exact pair; never backtrack."""
    from ecs_ec.costs.models import Calculation, BillRevision, Comparison
    calculation = await uow.session.scalar(select(Calculation).where(Calculation.cycle_id == cycle_id,
        Calculation.created_at <= cutoff_at).order_by(Calculation.revision.desc()).limit(1))
    bill = await uow.session.scalar(select(BillRevision).where(BillRevision.cycle_id == cycle_id,
        BillRevision.created_at <= cutoff_at).order_by(BillRevision.created_at.desc(), BillRevision.revision.desc(), BillRevision.id.desc()).limit(1))
    comparison = await uow.session.scalar(select(Comparison).where(Comparison.calculation_id == calculation.id,
        Comparison.bill_revision_id == bill.id, Comparison.created_at <= cutoff_at).order_by(Comparison.revision.desc()).limit(1)) if calculation and bill else None
    status = ('no_calculation' if calculation is None else 'no_bill' if bill is None else
        'available' if comparison is not None else 'missing_for_selected_revisions')
    return calculation, bill, comparison, status


async def page_rows(uow, query, model, *, settings, scope, filters, limit, cursor, now):
    """Read a signed deterministic created_at/id page, preserving the original cutoff between requests."""
    from sqlalchemy import tuple_
    from uuid import UUID
    from ecs_ec.consumption.models import instant
    from ecs_ec.identity.pagination import encode_cursor, decode_cursor
    if not 1 <= limit <= 100:
        raise CostsProblem('invalid_limit', 422)
    last = decode_cursor(settings, cursor, scope, filters) if cursor else None
    cutoff = instant(last['cutoff']) if last else now
    query = query.where(model.created_at <= cutoff)
    if last:
        query = query.where(tuple_(model.created_at, model.id) > tuple_(instant(last['at']), UUID(last['id'])))
    rows = (await uow.session.scalars(query.order_by(model.created_at, model.id).limit(limit+1))).all()
    selected = rows[:limit]
    continuation = encode_cursor(settings, scope, filters,
        dict(at=selected[-1].created_at.isoformat(), id=str(selected[-1].id), cutoff=cutoff.isoformat())) if len(rows) > limit else None
    return selected, continuation, cutoff
