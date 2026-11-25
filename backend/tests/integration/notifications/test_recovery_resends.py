"""Recovery preserves uncertain starts and excludes attempted periods from consolidated history."""

from uuid import uuid4

from ecs_ec.notifications import models
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.recovery import consolidate, reconcile_attempts
from ecs_ec.notifications.repository import prepare_attempt
from ecs_ec.notifications.scheduler import Scheduler
from sqlalchemy import func, select

from backend.tests.integration.notifications.test_smtp_dispatch import (
    Outcomes,
    due_delivery,
)


async def test_open_attempt_of_lost_process_is_indeterminate(notification_context):
    """A durable begin without a recorded result cannot return to the automatic retry queue."""
    ctx = notification_context
    await due_delivery(ctx)
    async with ctx["service"].database.sessions() as session:
        identifier = await session.scalar(select(models.Delivery.id))
    assert await prepare_attempt(ctx["service"], identifier, uuid4())
    assert await reconcile_attempts(ctx["service"]) == 1
    assert await reconcile_attempts(ctx["service"]) == 0
    async with ctx["service"].database.sessions() as session:
        delivery = await session.get(models.Delivery, identifier)
        assert delivery.state == "indeterminada" and delivery.attempt_count == 1


async def test_live_dispatcher_is_not_reconciled_by_peer(notification_context):
    """Session liveness protects a currently executing peer from startup recovery."""
    ctx = notification_context
    await due_delivery(ctx)
    dispatcher = Dispatcher(ctx["service"], transport=Outcomes("aceptada"))
    try:
        await dispatcher.start()
        async with ctx["service"].database.sessions() as session:
            identifier = await session.scalar(select(models.Delivery.id))
        assert await prepare_attempt(ctx["service"], identifier, dispatcher.process_ref)
        assert await reconcile_attempts(ctx["service"]) == 0
    finally:
        await dispatcher.close()
    assert await reconcile_attempts(ctx["service"]) == 1


async def test_only_untouched_periodic_members_are_consolidated(notification_context):
    """Two missed daily slots share one recovery, with both original immutable periods retained."""
    ctx = notification_context
    await due_delivery(ctx)
    ctx["clock"].advance(86401)
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        assert await scheduler.tick() == 1
    finally:
        await scheduler.close()
    assert await consolidate(ctx["service"]) == 1
    assert await consolidate(ctx["service"]) == 0
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(models.RecoveryMember)
            )
            == 2
        )
        delivery = await session.scalar(
            select(models.Delivery).where(models.Delivery.state == "pendiente")
        )
        message = await session.get(models.Message, delivery.message_id)
        assert len(message.functional_content["recovered_periods"]) == 2
        assert message.functional_content["type"] == "resumen_recuperacion"


async def test_real_acceptance_without_result_commit_recovers_indeterminate(
    notification_context, monkeypatch
):
    """Mailpit accepts actual DATA; loss before the result commit cannot be converted into confirmed nonacceptance."""
    import os

    import pytest
    from ecs_ec.notifications.settings import NotificationSettings

    if os.environ.get("NOTIFICATION_TEST_SMTP") != "1":
        pytest.skip("Exclusive local Mailpit required")
    ctx = notification_context
    ctx["service"].settings = NotificationSettings(
        _env_file=None, environment="test", smtp_host="127.0.0.1", smtp_port=11025
    )
    await due_delivery(ctx)
    dispatcher = Dispatcher(ctx["service"])

    async def lose_result(claim, result):
        """Fail the persistence boundary only after verifying a real positive SMTP acknowledgement."""
        assert result.outcome == "aceptada"
        raise OSError("synthetic result persistence failure")

    monkeypatch.setattr(dispatcher, "finish", lose_result)
    try:
        with pytest.raises(OSError):
            await dispatcher.dispatch_once()
    finally:
        await dispatcher.close()
    assert await reconcile_attempts(ctx["service"]) == 1
    async with ctx["service"].database.sessions() as session:
        row = await session.scalar(select(models.Delivery))
        assert row.state == "indeterminada" and row.attempt_count == 1
