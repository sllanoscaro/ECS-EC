"""Manual resend requires a new explicit administrative decision while preserving original indeterminate evidence."""

from uuid import uuid4

import pytest
from ecs_ec.identity.security import csrf
from ecs_ec.notifications import models
from ecs_ec.notifications.dispatcher import Dispatcher
from sqlalchemy import func, select

from backend.tests.integration.notifications.test_smtp_dispatch import (
    Outcomes,
    due_delivery,
)


async def failed_context(ctx, session_factory, settings):
    """Create an actual begun/indeterminate attempt, then authenticate a fresh administrator after the scheduled clock advance."""
    await due_delivery(ctx)
    dispatcher = Dispatcher(ctx["service"], transport=Outcomes("indeterminada"))
    try:
        await dispatcher.dispatch_once()
    finally:
        await dispatcher.close()
    bearer, _ = await session_factory(ctx["admin"])
    ctx["client"].cookies.set("ecs_ec_session", bearer)
    ctx["headers"]["X-CSRF-Token"] = csrf(settings, "session", bearer)
    async with ctx["service"].database.sessions() as session:
        return await session.scalar(select(models.Delivery.id))


async def test_resend_is_explicit_linked_idempotent_and_preserves_original(
    notification_context, session_factory, identity_settings
):
    """The same acknowledged decision creates exactly one new generation/Message-ID, and leaves the original result immutable."""
    ctx = notification_context
    parent = await failed_context(ctx, session_factory, identity_settings)
    key = str(uuid4())
    body = dict(
        reason="Revisado con el servicio de correo", acknowledge_possible_duplicate=True
    )
    path = "/api/v1/notifications/deliveries/" + str(parent) + "/resends"
    headers = ctx["headers"] | {"Idempotency-Key": key}
    response = await ctx["client"].post(path, json=body, headers=headers)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["possible_duplicate"] is True and result["parent_delivery_id"] == str(
        parent
    )
    assert result["delivery"]["parent_delivery_id"] == str(parent)
    assert (await ctx["client"].post(path, json=body, headers=headers)).json() == result
    assert (
        await ctx["client"].post(
            path, json=body | {"reason": "Otra decisión"}, headers=headers
        )
    ).status_code == 409
    async with ctx["service"].database.sessions() as session:
        original = await session.get(models.Delivery, parent)
        child = await session.scalar(
            select(models.Delivery).where(models.Delivery.parent_delivery_id == parent)
        )
        assert original.state == "indeterminada" and original.attempt_count == 1
        assert (
            child.generation == 1
            and child.attempt_count == 0
            and child.smtp_message_id != original.smtp_message_id
        )
        assert (
            await session.scalar(
                select(func.count()).select_from(models.ResendDecision)
            )
            == 1
        )


@pytest.mark.parametrize(
    "body",
    [
        dict(reason="", acknowledge_possible_duplicate=True),
        dict(reason="Revisado", acknowledge_possible_duplicate=False),
        dict(reason=" " * 3, acknowledge_possible_duplicate=True),
    ],
)
async def test_resend_invalid_decisions_are_rejected(
    notification_context, session_factory, identity_settings, body
):
    """Reason and acknowledgement are genuine required user decisions, never inferred from a click alone."""
    ctx = notification_context
    parent = await failed_context(ctx, session_factory, identity_settings)
    assert (
        await ctx["client"].post(
            "/api/v1/notifications/deliveries/" + str(parent) + "/resends",
            json=body,
            headers=ctx["headers"] | {"Idempotency-Key": str(uuid4())},
        )
    ).status_code == 422


async def test_operator_cannot_resend_and_new_decision_rejects_paused_rule(
    notification_context, session_factory, identity_settings
):
    """Server action permission precedes body parsing; pause prohibits a new decision while a confirmed replay remains the original resource."""
    ctx = notification_context
    parent = await failed_context(ctx, session_factory, identity_settings)
    path = "/api/v1/notifications/deliveries/" + str(parent) + "/resends"
    body = dict(reason="Revisado", acknowledge_possible_duplicate=True)
    key = str(uuid4())
    first = await ctx["client"].post(
        path, json=body, headers=ctx["headers"] | {"Idempotency-Key": key}
    )
    assert first.status_code == 201
    async with ctx["service"].database.sessions() as session:
        rule = await session.scalar(select(models.Rule))
    paused = await ctx["client"].post(
        "/api/v1/notifications/rules/" + str(rule.id) + "/pause",
        headers=ctx["headers"]
        | {"Idempotency-Key": str(uuid4()), "If-Match": '"' + str(rule.revision) + '"'},
    )
    assert paused.status_code == 200, paused.text
    assert (
        await ctx["client"].post(
            path, json=body, headers=ctx["headers"] | {"Idempotency-Key": str(uuid4())}
        )
    ).status_code == 409
    replay = await ctx["client"].post(
        path, json=body, headers=ctx["headers"] | {"Idempotency-Key": key}
    )
    assert (
        replay.status_code == 201
        and replay.json()["decision_id"] == first.json()["decision_id"]
    )
    bearer, _ = await session_factory(ctx["recipient"])
    ctx["client"].cookies.set("ecs_ec_session", bearer)
    headers = {
        "Origin": identity_settings.origin,
        "X-CSRF-Token": csrf(identity_settings, "session", bearer),
        "Idempotency-Key": str(uuid4()),
    }
    assert (await ctx["client"].post(path, json={}, headers=headers)).status_code == 403


async def test_downgraded_recipient_cannot_read_historical_administration_content(
    notification_context, account_factory, session_factory
):
    """Historical membership never preserves a removed current content grant, even for the delivery's own account."""
    from ecs_ec.identity.models import Account
    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.scheduler import Scheduler

    ctx = notification_context
    recipient = await account_factory(role="administrador_tecnico")
    await ctx["make_rule"](
        contents=["cambios_administrativos"], recipient_id=recipient.id
    )
    async with ctx["service"].database.sessions() as session:
        activation = await session.scalar(select(models.Activation))
    ctx["clock"].advance((activation.next_due_at - ctx["clock"].now()).total_seconds())
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        await scheduler.tick()
    finally:
        await scheduler.close()
    bearer, principal = await session_factory(ctx["admin"])
    await ctx["service"].identity.update_account(
        principal,
        recipient.id,
        AccountUpdate(email=recipient.email, role="operador", status="active"),
        recipient.revision,
    )
    async with ctx["service"].database.sessions() as session:
        updated = await session.get(Account, recipient.id)
        identifier = await session.scalar(select(models.Delivery.id))
    bearer, _ = await session_factory(updated)
    ctx["client"].cookies.set("ecs_ec_session", bearer)
    assert (
        await ctx["client"].get("/api/v1/notifications/deliveries/" + str(identifier))
    ).status_code == 404
    assert (await ctx["client"].get("/api/v1/notifications/deliveries")).json()[
        "items"
    ] == []
