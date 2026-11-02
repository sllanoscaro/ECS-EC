"""Identity's safe action vocabulary on platform009 FunctionalAudit/EventWriter; no new store."""

from typing import Literal
from uuid import UUID, uuid4

from ecs_ec.audit.events import Code, EventInput, EventWriter, PayloadRegistry, SafePayload
from ecs_ec.audit.services import AuditInput, FunctionalAudit
from ecs_ec.identity.permissions import ADMIN
from ecs_ec.identity.schemas import Role, Status

ACTIONS = frozenset({"identity.account.created", "identity.account.updated", "identity.account.reset",
                     "identity.password.changed", "identity.bootstrap", "identity.recovery"}) | ADMIN


class IdentityPayload(SafePayload):
    """Approved identifiers, codes and changed-field names only, excluding emails and credential values."""

    account_id: UUID | None
    revision: int | None
    changed_fields: list[Literal["email", "role", "status", "credential", "renewal"]]
    role: Role | None
    status: Status | None
    renewal_required: bool | None
    actor_kind: Literal["account", "process", "unauthenticated"]
    process_code: Code | None
    reason_code: Code
    operation_ref: UUID


def actor_kind(actor_ref):
    """Classify only server-produced opaque references; request bodies never supply actors."""
    if actor_ref.startswith("account:"):
        return "account", None
    if actor_ref.startswith("process:"):
        return "process", actor_ref.split(":", 1)[1]
    return "unauthenticated", None


class IdentityAudit:
    """Append sanitized evidence inside account changes and separately after rejected transactions."""

    def __init__(self, clock, timezone):
        """Register only identity-owned actions/types against the shared strict payload registry."""
        self.clock = clock
        registry = PayloadRegistry()
        for action in ACTIONS:
            registry.register(action, IdentityPayload, results={"allowed", "denied", "rejected"})
        for event_type in ("identity.changed", "administration.changed"):
            registry.register(event_type, IdentityPayload)
        self.audit = FunctionalAudit(registry, clock, timezone)
        self.events = EventWriter(registry, clock, timezone)

    async def changed(self, uow, *, account_id, revision, actor_ref, action, fields, role, status, renewal,
                      operation_ref, administrative=True, reason_code="changed"):
        """Write one action and identity/provenance events atomically, never raw account/credential objects."""
        kind, process = actor_kind(actor_ref)
        payload = IdentityPayload(account_id=account_id, revision=revision, changed_fields=list(fields), role=role,
                                  status=status, renewal_required=renewal, actor_kind=kind, process_code=process,
                                  reason_code=reason_code, operation_ref=operation_ref).model_dump()
        await self.audit.append(uow, AuditInput(actor_ref=actor_ref, action=action, entity_type="account",
            entity_id=account_id, entity_revision=revision, occurred_at=self.clock.now(), result="allowed", safe_payload=payload))
        for event_type in (("identity.changed", "administration.changed") if administrative else ("identity.changed",)):
            await self.events.append(uow, EventInput(event_id=uuid4(), event_type=event_type, source_module="identity",
                source_entity_id=account_id, source_revision=revision, occurred_at=self.clock.now(),
                safe_payload=payload, correlation_ref=str(operation_ref)))

    async def attempt(self, uow, *, actor_ref, action, target_id, result, reason_code, operation_ref):
        """Record a denied/rejected administrative attempt after rollback; no account change events."""
        kind, process = actor_kind(actor_ref)
        payload = IdentityPayload(account_id=target_id, revision=None, changed_fields=[], role=None, status=None,
            renewal_required=None, actor_kind=kind, process_code=process, reason_code=reason_code,
            operation_ref=operation_ref).model_dump()
        return await self.audit.append(uow, AuditInput(actor_ref=actor_ref, action=action, entity_type="account",
            entity_id=target_id or UUID(int=0), entity_revision=None, occurred_at=self.clock.now(), result=result,
            safe_payload=payload))
