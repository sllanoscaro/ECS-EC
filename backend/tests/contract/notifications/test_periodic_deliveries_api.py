"""Notification history honors current006 account scope before revealing any delivery metadata."""

from uuid import uuid4

from backend.tests.integration.notifications.test_smtp_dispatch import due_delivery


async def test_history_excludes_other_accounts(
    notification_context, session_factory, identity_settings
):
    """Admin sees all; eligible recipient sees its own rows, and a different account gets404."""
    ctx = notification_context
    await due_delivery(ctx)
    client = ctx["client"]
    bearer, _ = await session_factory(ctx["admin"])
    client.cookies.set("ecs_ec_session", bearer)
    response = await client.get("/api/v1/notifications/deliveries")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    item = response.json()["items"][0]
    identifier = item["id"]
    assert "email" not in str(item)
    bearer, _ = await session_factory(ctx["recipient"])
    client.cookies.set("ecs_ec_session", bearer)
    detail = await client.get("/api/v1/notifications/deliveries/" + identifier)
    assert detail.status_code == 200, detail.text
    assert detail.json()["content"]["type"] == "resumen_periodico"
    assert detail.json()["attempts"] == []
    assert (
        await client.get(
            "/api/v1/notifications/deliveries?recipient_id=" + str(ctx["admin"].id)
        )
    ).status_code == 403
    assert (
        await client.get("/api/v1/notifications/deliveries/" + str(uuid4()))
    ).status_code == 404
    bearer, _ = await session_factory(ctx["admin"])
    client.cookies.set("ecs_ec_session", bearer)
    assert (
        await client.get("/api/v1/notifications/deliveries?limit=0")
    ).status_code == 422


async def test_unknown_delivery_does_not_disclose_metadata(
    notification_context, account_factory, session_factory
):
    """A different active operator sees an empty own history and404 for an existing foreign object."""
    ctx = notification_context
    await due_delivery(ctx)
    client = ctx["client"]
    bearer, _ = await session_factory(ctx["admin"])
    client.cookies.set("ecs_ec_session", bearer)
    identifier = (await client.get("/api/v1/notifications/deliveries")).json()["items"][
        0
    ]["id"]
    other = await account_factory()
    bearer, _ = await session_factory(other)
    client.cookies.set("ecs_ec_session", bearer)
    assert (await client.get("/api/v1/notifications/deliveries")).json()["items"] == []
    response = await client.get("/api/v1/notifications/deliveries/" + identifier)
    assert response.status_code == 404 and "content" not in response.json()
