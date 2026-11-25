"""Reconcile installed tzdata under session leadership, before any new scheduling."""

from sqlalchemy import delete, select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.notifications.calendar import next_occurrences, tzdata_version
from ecs_ec.notifications.models import Activation, Preview, RuleVersion
from ecs_ec.notifications.repository import lock_rule
from ecs_ec.notifications.schemas import instant


async def reconcile(scheduler):
    """Commit one rule at a time; old due slots remain due and immutable captures are never rewritten."""
    installed = tzdata_version()
    async with scheduler.service.database.sessions() as session:
        ids = list(
            await session.execute(
                select(Activation.id, Activation.rule_id)
                .where(
                    Activation.ended_at.is_(None),
                    Activation.tzdata_version != installed,
                )
                .order_by(Activation.rule_id)
            )
        )
    for identifier, rule_id in ids:
        await scheduler.check_leadership()
        async with UnitOfWork(scheduler.service.database.sessions) as uow:
            await lock_rule(uow.session, rule_id)
            activation = await uow.session.get(
                Activation, identifier, with_for_update=True
            )
            if (
                activation.ended_at is not None
                or activation.tzdata_version == installed
            ):
                continue
            version = await uow.session.get(RuleVersion, activation.version_id)
            now = scheduler.service.clock.now()
            if activation.next_due_at and activation.next_due_at > now:
                base = max(now, activation.activated_at)
                activation.next_slot = next_occurrences(
                    version.config["schedule"], version.timezone, base, 1
                )[0]
                activation.next_due_at = instant(activation.next_slot["resolved_at"])
            activation.tzdata_version = installed
            activation.revision += 1
            # Every old token is already version-bound; deleting only outdated tokens makes invalidation explicit.
            await uow.session.execute(
                delete(Preview).where(Preview.tzdata_version != installed)
            )
            await scheduler.check_leadership()
            await uow.commit()
