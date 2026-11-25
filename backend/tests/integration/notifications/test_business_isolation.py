"""Actual001/002/004/005 business results survive refused loopback SMTP and failures at the installed007 emitter boundary."""

import socket

from ecs_ec.notifications import models
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.settings import NotificationSettings
from ecs_ec.observability.lifecycle import Policy, Telemetry
from sqlalchemy import func, select

from backend.tests.contract.costs.test_calculations_api import (
    test_calculation_persistence_replay_and_read_only as actual_costs,
)
from backend.tests.integration.notifications.test_smtp_dispatch import due_delivery
from backend.tests.integration.reports.test_observability import (
    test_technical_failure_cannot_change_pdf as actual_pdf,
)


async def test_business_with_unavailable_mail_and_telemetry(
    notification_context,
    history_environment,
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
):
    """Mailbox failure stays in one bounded delivery; actual reception/cost queries/PDF keep their ordinary results and permissions."""
    ctx = notification_context
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
    ctx["service"].settings = NotificationSettings(
        _env_file=None, environment="test", smtp_host="127.0.0.1", smtp_port=port
    )
    await due_delivery(ctx)
    dispatcher = Dispatcher(ctx["service"])
    try:
        assert await dispatcher.dispatch_once() == 1
    finally:
        await dispatcher.close()
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "isolated"), autostart=False
    )

    def unavailable(*args, **kwargs):
        """Break only the installed optional technical admission boundary, with no fabricated functional provider."""
        raise OSError("synthetic technical unavailability")

    monkeypatch.setattr(telemetry, "begin", unavailable)
    history_environment.telemetry = telemetry
    costs_client._transport.app.state.telemetry = telemetry
    try:
        await actual_costs(
            costs_client,
            costs_environment,
            account_factory,
            session_factory,
            identity_settings,
        )
        await actual_pdf(
            costs_client,
            costs_environment,
            account_factory,
            session_factory,
            identity_settings,
            tmp_path / "pdf",
            monkeypatch,
            "saturation",
        )
        async with ctx["service"].database.sessions() as session:
            assert (
                await session.scalar(select(func.count()).select_from(models.Delivery))
                == 1
            )
            delivery = await session.scalar(select(models.Delivery))
            attempt = await session.scalar(select(models.Attempt))
            assert (
                delivery.state == "pendiente"
                and attempt.outcome == "no_aceptada_transitoria"
                and delivery.attempt_count == 1
            )
        assert telemetry.logs.depth <= 1024
    finally:
        history_environment.telemetry = None
        costs_client._transport.app.state.telemetry = None
        telemetry.shutdown()
