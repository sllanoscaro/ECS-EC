"""Two PostgreSQL consumers cannot materialize one logical periodic slot twice."""

from ecs_ec.notifications.models import Activation, Delivery, Occurrence
from ecs_ec.notifications.scheduler import Scheduler
from sqlalchemy import func, select


async def test_two_schedulers_share_session_leadership(notification_context):
    """A dedicated session lock excludes peers and is released on explicit shutdown."""
    ctx = notification_context
    first, second = Scheduler(ctx["service"]), Scheduler(ctx["service"])
    try:
        assert await first.acquire()
        assert not await second.acquire()
        await first.close()
        assert await second.acquire()
    finally:
        await first.close()
        await second.close()


async def test_due_slot_is_durable_and_idempotent(notification_context):
    """A fixed cutoff/message and one delivery survive repeated ticks and leader replacement."""
    ctx = notification_context
    await ctx["make_rule"]()
    async with ctx["service"].database.sessions() as session:
        activation = await session.scalar(
            select(Activation).where(Activation.ended_at.is_(None))
        )
        due = activation.next_due_at
    ctx["clock"].advance((due - ctx["clock"].now()).total_seconds() + 1)
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        assert await scheduler.tick() == 1
        assert await scheduler.tick() == 0
        async with ctx["service"].database.sessions() as session:
            assert (
                await session.scalar(select(func.count()).select_from(Occurrence)) == 1
            )
            assert await session.scalar(select(func.count()).select_from(Delivery)) == 1
            row = await session.scalar(select(Occurrence))
            assert row.scheduled_at == due
            assert row.cutoff_at == ctx["clock"].now()
    finally:
        await scheduler.close()
