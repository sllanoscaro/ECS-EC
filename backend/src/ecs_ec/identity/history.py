"""Read shared administrative evidence using fresh access, fixed cutoff and signed filter-bound pagination."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, tuple_

from ecs_ec.audit.events import Code
from ecs_ec.audit.models import AuditRecord
from ecs_ec.core.clock import utc
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.pagination import decode_cursor, encode_cursor
from ecs_ec.identity.schemas import AdministrationActor, AdministrationEntry, AdministrationTarget, HistoryPage


def actor_projection(reference):
    """Interpret only stored trusted opaque actor conventions; never look at request-declared identity."""
    if reference.startswith("account:"):
        try:
            return AdministrationActor(kind="account", account_id=UUID(reference[8:]), process_code=None)
        except ValueError:
            pass
    if reference.startswith("process:"):
        return AdministrationActor(kind="process", account_id=None, process_code=reference[8:])
    return AdministrationActor(kind="unauthenticated", account_id=None, process_code=None)


def project_entry(row):
    """Select typed metadata only; original JSONB, credential details and unknown fields are excluded."""
    payload = row.safe_payload
    operation = UUID(payload["operation_ref"]) if payload.get("operation_ref") else row.id
    module = "identity" if row.action.startswith("identity.") or row.action == "administration.history.read" else row.action.split(".", 1)[0]
    return AdministrationEntry(id=row.id, occurred_at=row.occurred_at, actor=actor_projection(row.actor_ref), action=row.action,
        target=AdministrationTarget(module=module, entity_type=row.entity_type, id=row.entity_id if row.entity_id.int else None,
                                    revision=row.entity_revision), result=row.result,
        reason_code=payload.get("reason_code", "recorded"), operation_ref=operation)


async def read_history(identity, principal, *, start=None, end=None, action=None, result=None,
                       actor_id=None, target_id=None, cursor=None, limit=25):
    """Read [start,end) at one cutoff; unavailable storage raises instead of inventing an empty history."""
    identity.authorize(principal, "administration.history.read", identity.settings.building_id)
    try:
        if not 1 <= limit <= 100 or bool(start) != bool(end):
            raise ValueError()
        start = utc(datetime.fromisoformat(start)) if start else None
        end = utc(datetime.fromisoformat(end)) if end else None
        if start and start >= end:
            raise ValueError()
        if action and action not in identity.history_actions:
            raise ValueError()
        filters = {"from": start.isoformat() if start else None, "to": end.isoformat() if end else None,
                   "action": action, "result": result, "actor_id": str(actor_id) if actor_id else None,
                   "target_id": str(target_id) if target_id else None}
        position = decode_cursor(identity.settings, cursor, "history", filters) if cursor else None
        cutoff = utc(datetime.fromisoformat(position["cutoff"])) if position else identity.clock.now()
        window_end = end or cutoff
        window_start = start or window_end-timedelta(hours=24)
        query = select(AuditRecord).where(AuditRecord.action.in_(identity.history_actions),
            AuditRecord.result.in_(("allowed", "denied", "rejected")), AuditRecord.recorded_at <= cutoff,
            AuditRecord.occurred_at >= window_start, AuditRecord.occurred_at < window_end)
        if action:
            query = query.where(AuditRecord.action == action)
        if result:
            query = query.where(AuditRecord.result == result)
        if actor_id:
            query = query.where(AuditRecord.actor_ref == "account:"+str(actor_id))
        if target_id:
            query = query.where(AuditRecord.entity_id == target_id)
        if position:
            query = query.where(tuple_(AuditRecord.occurred_at, AuditRecord.id) < tuple_(
                utc(datetime.fromisoformat(position["at"])), UUID(position["id"])))
    except (ValueError, KeyError, TypeError):
        raise IdentityProblem("invalid_input", 422) from None
    async with UnitOfWork(identity.database.sessions) as uow:
        rows = (await uow.session.scalars(query.order_by(AuditRecord.occurred_at.desc(), AuditRecord.id.desc()).limit(limit+1))).all()
        selected = rows[:limit]
        continuation = encode_cursor(identity.settings, "history", filters, {"at": selected[-1].occurred_at.isoformat(),
            "id": str(selected[-1].id), "cutoff": cutoff.isoformat()}) if len(rows) > limit else None
        return HistoryPage(items=[project_entry(row) for row in selected], next_cursor=continuation, cutoff_at=cutoff)
