"""008 minimum calendar retention follows protected dependency edges; reads and duplicates do not renew evidence."""

from sqlalchemy import select

from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.core.retention import anniversary
from ecs_ec.notifications import models


async def protect_delivery(service, session, identifier, registered_at):
    """Extend one delivery's captured parents to the maximum dependent anniversary in the building zone.

    Caller holds rule→account/delivery locks before entry. Definitions and attempts
    remain immutable; only retention deadlines move forward. There is no automatic
    purge and no dependency on the technical collectors' much shorter retention.
    """
    await protect_delivery_until(
        session, identifier, anniversary(registered_at, service.identity.timezone)
    )


async def protect_delivery_until(session, identifier, until):
    """Propagate an already resolved building-zone deadline inside a caller-owned/participant transaction."""
    await session.flush()
    visited = {}

    async def protect(cls, key, deadline):
        """Acquire a current protected row and propagate its existing/later deadline through owned parents."""
        if visited.get((cls, key)) is not None and visited[(cls, key)] >= deadline:
            return
        row = await session.scalar(
            select(cls)
            .where(cls.id == key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            return
        row.retain_until = max(row.retain_until, deadline)
        deadline = row.retain_until
        visited[(cls, key)] = deadline
        if cls is models.Delivery:
            attempts = list(
                await session.scalars(
                    select(models.Attempt)
                    .where(models.Attempt.delivery_id == row.id)
                    .order_by(models.Attempt.attempt_number)
                    .with_for_update()
                )
            )
            deadline = max([deadline, *[attempt.retain_until for attempt in attempts]])
            row.retain_until = deadline
            visited[(cls, key)] = deadline
            for attempt in attempts:
                attempt.retain_until = max(attempt.retain_until, deadline)
            await protect(models.Message, row.message_id, deadline)
            if row.parent_delivery_id:
                await protect(models.Delivery, row.parent_delivery_id, deadline)
            originals = list(
                await session.scalars(
                    select(models.RecoveryMember.original_delivery_id)
                    .where(models.RecoveryMember.recovery_delivery_id == row.id)
                    .order_by(models.RecoveryMember.original_delivery_id)
                )
            )
            for original in originals:
                await protect(models.Delivery, original, deadline)
        elif cls is models.Message:
            await protect(models.Occurrence, row.occurrence_id, deadline)
        elif cls is models.Occurrence:
            await protect(models.RuleVersion, row.version_id, deadline)
            if row.episode_id:
                await protect(models.Episode, row.episode_id, deadline)
        elif cls is models.Episode:
            await protect(models.Evidence, row.opening_evidence_id, deadline)
            if row.closing_evidence_id:
                await protect(models.Evidence, row.closing_evidence_id, deadline)
            if row.source_event_id:
                await protect(FunctionalEvent, row.source_event_id, deadline)
            evaluations = list(
                await session.scalars(
                    select(models.Evaluation.id)
                    .where(models.Evaluation.episode_id == row.id)
                    .order_by(models.Evaluation.id)
                )
            )
            for identifier in evaluations:
                await protect(models.Evaluation, identifier, deadline)
        elif cls is models.Evaluation:
            await protect(models.Evidence, row.evidence_id, deadline)
            if row.source_event_id:
                await protect(FunctionalEvent, row.source_event_id, deadline)

    await protect(models.Delivery, identifier, until)
