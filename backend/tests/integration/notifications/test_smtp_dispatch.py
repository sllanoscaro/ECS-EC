"""Real durable PostgreSQL attempt boundaries with privately injected deterministic transport outcomes."""

from datetime import timedelta

from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.models import Activation, Attempt, Delivery
from ecs_ec.notifications.scheduler import Scheduler
from ecs_ec.notifications.transports import TransportResult
from sqlalchemy import select


class Outcomes:
    """A private synchronous transport which observes the already committed durable attempt."""

    def __init__(self, *outcomes):
        """Store only approved result codes for this test's independent invocations."""
        self.outcomes = iter(outcomes)
        self.calls = 0

    def send(self, *args):
        """No SMTP/network effects; integration with the real local relay is tested separately."""
        self.calls += 1
        return TransportResult(next(self.outcomes), "synthetic_confirmed_result")


async def due_delivery(ctx):
    """Use the real scheduler/summary source instead of constructing an untyped message fixture."""
    await ctx["make_rule"]()
    async with ctx["service"].database.sessions() as session:
        activation = await session.scalar(
            select(Activation).where(Activation.ended_at.is_(None))
        )
    ctx["clock"].advance((activation.next_due_at - ctx["clock"].now()).total_seconds())
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        assert await scheduler.tick() == 1
    finally:
        await scheduler.close()


async def test_three_transient_attempts_wait_one_then_five_minutes(
    notification_context,
):
    """Retries keep delivery/Message-ID and are due relative to each confirmed completion."""
    ctx = notification_context
    await due_delivery(ctx)
    transport = Outcomes(*(["no_aceptada_transitoria"] * 3))
    dispatcher = Dispatcher(ctx["service"], transport=transport)
    try:
        for number, wait in [(1, 60), (2, 300), (3, None)]:
            assert await dispatcher.dispatch_once() == 1
            async with ctx["service"].database.sessions() as session:
                delivery = await session.scalar(select(Delivery))
                attempt = await session.scalar(
                    select(Attempt).where(Attempt.attempt_number == number)
                )
                assert (
                    attempt.finished_at == ctx["clock"].now()
                    and delivery.attempt_count == number
                )
                if wait:
                    assert (
                        delivery.state == "pendiente"
                        and delivery.next_attempt_at
                        == attempt.finished_at + timedelta(seconds=wait)
                    )
                    assert await dispatcher.dispatch_once() == 0
                    ctx["clock"].advance(wait)
                else:
                    assert delivery.state == "fallida"
        assert transport.calls == 3 and await dispatcher.dispatch_once() == 0
    finally:
        await dispatcher.close()


async def test_unknown_has_no_automatic_retry(notification_context):
    """Lost confirmation is durable indeterminate even after an arbitrarily long retry interval."""
    ctx = notification_context
    await due_delivery(ctx)
    transport = Outcomes("indeterminada")
    dispatcher = Dispatcher(ctx["service"], transport=transport)
    try:
        assert await dispatcher.dispatch_once() == 1
        ctx["clock"].advance(3600)
        assert await dispatcher.dispatch_once() == 0
        async with ctx["service"].database.sessions() as session:
            delivery = await session.scalar(select(Delivery))
            assert delivery.state == "indeterminada" and delivery.attempt_count == 1
    finally:
        await dispatcher.close()


async def test_capacity_is_reserved_before_claim_without_blocking_api(
    notification_context,
):
    """Four live transport calls hold four durable starts, with no fifth claim while those sockets remain active."""
    import asyncio
    import threading
    from uuid import uuid4

    ctx = notification_context
    await due_delivery(ctx)
    async with ctx["service"].database.sessions() as session:
        original = await session.scalar(select(Delivery))
        for generation in range(1, 7):
            identifier = uuid4()
            session.add(
                Delivery(
                    id=identifier,
                    message_id=original.message_id,
                    account_id=original.account_id,
                    generation=generation,
                    next_attempt_at=ctx["clock"].now(),
                    smtp_message_id=f"<{identifier}@example.test>",
                    transport_kind="local_prueba",
                    created_at=ctx["clock"].now(),
                    retain_until=original.retain_until,
                )
            )
        await session.commit()
    release = threading.Event()
    started = 0
    lock = threading.Lock()

    class Blocking:
        """Private bounded synthetic socket call; production uses the dedicated SMTP adapter."""

        def send(self, *args):
            """Retain capacity until explicit completion, with a bounded test cleanup deadline."""
            nonlocal started
            with lock:
                started += 1
            assert release.wait(5)
            return TransportResult("aceptada", "synthetic_confirmed_result")

    dispatcher = Dispatcher(ctx["service"], transport=Blocking())
    task = asyncio.create_task(dispatcher.dispatch_once())
    try:
        async with asyncio.timeout(3):
            while started < 4:
                await asyncio.sleep(0.01)
        async with ctx["service"].database.sessions() as session:
            assert len(list(await session.scalars(select(Attempt)))) == 4
            assert (
                len(
                    list(
                        await session.scalars(
                            select(Delivery).where(Delivery.state == "pendiente")
                        )
                    )
                )
                == 3
            )
        assert (await ctx["client"].get("/api/v1/health/ready")).status_code == 200
    finally:
        release.set()
        await task
        await dispatcher.close()
