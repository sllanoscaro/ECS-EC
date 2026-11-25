"""008 concrete participant in006's neutral protocol: rules ordered→account→deliveries, no SMTP or commit."""

from dataclasses import dataclass

from sqlalchemy import select

from ecs_ec.identity.models import Account
from ecs_ec.identity.services import recipient_eligible
from ecs_ec.notifications.models import (
    Delivery,
    Message,
    Occurrence,
    Recipient,
    Rule,
    RuleVersion,
)


@dataclass(frozen=True)
class Plan:
    """Discovery signature rechecked after account locks; adding a reference requires a full producer retry."""

    account_id: object
    rules: tuple


class NotificationParticipant:
    """Coordinate all pending008 work with account mutation while preserving begun-attempt history."""

    name = "notifications008"
    before_range = (100, 199)
    after_range = (100, 199)

    def __init__(self, clock=None, timezone=None):
        """Receive the monolith clock/building retention zone at composition; protocol inspection needs no live dependencies."""
        self.clock, self.timezone = clock, timezone

    async def discover(self, mutation, uow):
        """Find all referencing rule heads and revisions without effects, sorted by immutable UUID."""
        rows = await uow.session.execute(
            select(Rule.id, Rule.revision)
            .join(RuleVersion, RuleVersion.rule_id == Rule.id)
            .join(Recipient, Recipient.version_id == RuleVersion.id)
            .where(Recipient.account_id == mutation.account_id)
            .distinct()
            .order_by(Rule.id)
        )
        return Plan(mutation.account_id, tuple(rows.all()))

    async def lock(self, plan, phase, uow):
        """Acquire only rules before006's account lock and deliveries after it; preserve the global order."""
        if phase == "before":
            await uow.session.execute(
                select(Rule)
                .where(Rule.id.in_([row[0] for row in plan.rules]))
                .order_by(Rule.id)
                .with_for_update()
            )
        elif phase == "after":
            await uow.session.execute(
                select(Delivery)
                .where(Delivery.account_id == plan.account_id)
                .order_by(Delivery.id)
                .with_for_update()
            )
        else:
            raise ValueError("Unknown coordination phase")

    async def revalidate(self, mutation, plan, uow):
        """Ask006 to roll back/redetect when a reference/revision changed; never acquire a newly found rule late."""
        return plan == await self.discover(mutation, uow)

    async def apply(self, mutation, plan, uow):
        """Cancel only pending deliveries now unauthorized; changed email remains resolved afresh on the next attempt."""
        account = await uow.session.scalar(
            select(Account).where(Account.id == plan.account_id)
        )
        rows = await uow.session.execute(
            select(Delivery, Message, Rule, RuleVersion)
            .join(Message, Message.id == Delivery.message_id)
            .join(Occurrence, Occurrence.id == Message.occurrence_id)
            .join(RuleVersion, RuleVersion.id == Occurrence.version_id)
            .join(Rule, Rule.id == RuleVersion.rule_id)
            .where(
                Delivery.account_id == plan.account_id, Delivery.state == "pendiente"
            )
        )
        for delivery, message, rule, version in rows:
            if (
                rule.status != "activa"
                or rule.current_version_id != version.id
                or not recipient_eligible(account, message.required_permissions)
            ):
                delivery.state = "cancelada"
                from ecs_ec.notifications.repository import cancellation_reason

                delivery.cancellation_reason = cancellation_reason(
                    rule, version, account
                )
                if self.clock is not None:
                    from ecs_ec.core.retention import anniversary
                    from ecs_ec.notifications.retention import protect_delivery_until

                    await protect_delivery_until(
                        uow.session,
                        delivery.id,
                        anniversary(self.clock.now(), self.timezone),
                    )
        await uow.session.flush()
