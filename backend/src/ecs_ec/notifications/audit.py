"""008 safe functional administrative evidence through009's transaction-owned writers."""

from typing import Literal
from uuid import UUID, uuid4

from ecs_ec.audit.events import EventInput, EventWriter, PayloadRegistry, SafePayload
from ecs_ec.audit.services import AuditInput, FunctionalAudit

ACTIONS = frozenset(
    {
        "notifications.rule.created",
        "notifications.rule.revised",
        "notifications.rule.activated",
        "notifications.rule.paused",
        "notifications.delivery.resent",
    }
)


class Payload(SafePayload):
    """Only opaque identities/revision/fixed action; no rule names, emails, energy or free explanations."""

    rule_id: UUID
    version_id: UUID
    revision: int
    action: Literal["created", "revised", "activated", "paused", "resent"]


class NotificationAudit:
    """Append audit and administration.changed inside the same successful business transaction."""

    def __init__(self, clock, timezone):
        """Register own bounded safe payloads without modifying another producer's schema."""
        self.clock = clock
        registry = PayloadRegistry()
        for code in ACTIONS:
            registry.register(code, Payload, results={"allowed"})
        registry.register("administration.changed", Payload)
        self.audit = FunctionalAudit(registry, clock, timezone)
        self.events = EventWriter(registry, clock, timezone)

    async def changed(self, uow, actor, rule, action, *, operation_id=None):
        """Keep provenance and durable event atomic with the rule/result; no callback or SMTP here."""
        payload = Payload(
            rule_id=rule.id,
            version_id=rule.current_version_id,
            revision=rule.revision,
            action=action,
        ).model_dump()
        await self.audit.append(
            uow,
            AuditInput(
                actor_ref="account:" + str(actor),
                action="notifications.rule." + action
                if action != "resent"
                else "notifications.delivery.resent",
                entity_type="notification_resend_decision"
                if operation_id
                else "notification_rule",
                entity_id=operation_id or rule.id,
                entity_revision=1 if operation_id else rule.revision,
                occurred_at=self.clock.now(),
                result="allowed",
                safe_payload=payload,
            ),
        )
        await self.events.append(
            uow,
            EventInput(
                event_id=uuid4(),
                event_type="administration.changed",
                source_module="notifications",
                source_entity_id=operation_id or rule.id,
                source_revision=1 if operation_id else rule.revision,
                occurred_at=self.clock.now(),
                safe_payload=payload,
            ),
        )
