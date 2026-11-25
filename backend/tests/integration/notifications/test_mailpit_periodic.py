"""Opt-in real Mailpit capture verifies one current recipient, escaped content and protected environment links."""

import os

import httpx
import pytest
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.models import Attempt, Delivery
from ecs_ec.notifications.settings import NotificationSettings
from sqlalchemy import select

from backend.tests.integration.notifications.test_smtp_dispatch import due_delivery


async def test_real_mailpit_acceptance_is_local_only(notification_context):
    """Only the explicitly selected loopback test capturer receives these synthetic messages."""
    if os.environ.get("NOTIFICATION_TEST_SMTP") != "1":
        pytest.skip("Exclusive local Mailpit required")
    ctx = notification_context
    from ecs_ec.identity.schemas import AccountUpdate

    effective_email = "current-" + ctx["recipient"].id.hex + "@example.test"
    await ctx["service"].identity.update_account(
        ctx["principal"],
        ctx["recipient"].id,
        AccountUpdate(email=effective_email, role="operador", status="active"),
        ctx["recipient"].revision,
    )
    ctx["service"].settings = NotificationSettings(
        _env_file=None,
        environment="test",
        smtp_host="127.0.0.1",
        smtp_port=11025,
        app_public_base_url="http://localhost:8000",
    )
    await due_delivery(ctx)
    dispatcher = Dispatcher(ctx["service"])
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:18025", trust_env=False
    ) as mail:
        before = (await mail.get("/api/v1/messages")).json()["total"]
        try:
            assert await dispatcher.dispatch_once() == 1
        finally:
            await dispatcher.close()
        messages = (await mail.get("/api/v1/messages")).json()
        assert messages["total"] == before + 1
        matching = [
            m for m in messages["messages"] if m["To"][0]["Address"] == effective_email
        ]
        assert matching
        captured = (await mail.get("/api/v1/message/" + matching[0]["ID"])).json()
        assert len(captured["To"]) == 1 and not captured["Cc"] and not captured["Bcc"]
        assert "Correo local de prueba" in captured["Text"]
        assert "http://localhost:8000/notificaciones?entrega=" in captured["Text"]
        assert "Corte:" in captured["Text"] and "Período:" in captured["Text"]
    async with ctx["service"].database.sessions() as session:
        delivery = await session.scalar(select(Delivery))
        attempt = await session.scalar(select(Attempt))
        assert delivery.state == "aceptada" and attempt.outcome == "aceptada"
        assert attempt.effective_email == effective_email
