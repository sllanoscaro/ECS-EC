"""008 uses the installed007 safe emitter/catalog; operation cycles and individual SMTP attempts remain different units."""

import json

from ecs_ec.notifications import models
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.observability.lifecycle import Policy, Telemetry
from sqlalchemy import select

from backend.tests.integration.notifications.test_smtp_dispatch import (
    Outcomes,
    due_delivery,
)


async def test_terminal_attempt_correlation_and_sanitization(
    notification_context, tmp_path
):
    """One durable SMTP invocation emits one attempt terminal with only trusted opaque references and its own trace."""
    ctx = notification_context
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "safe"), autostart=False
    )
    ctx["service"].telemetry = telemetry
    ctx["client"]._transport.app.state.telemetry = telemetry
    try:
        await due_delivery(ctx)
        dispatcher = Dispatcher(ctx["service"], transport=Outcomes("aceptada"))
        try:
            assert await dispatcher.dispatch_once() == 1
        finally:
            await dispatcher.close()
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        events = [json.loads(p) for p in payloads]
        attempts = [
            e for e in events if e["event"] == "notification.delivery.attempt.completed"
        ]
        cycles = [e for e in events if e["event"] == "notification.scheduler.tick"]
        waves = [
            e
            for e in events
            if e["event"] == "notification.operation.completed"
            and e["operation"] == "notification.dispatch"
        ]
        assert len(attempts) == len(cycles) == len(waves) == 1
        async with ctx["service"].database.sessions() as session:
            attempt = await session.scalar(select(models.Attempt))
            assert attempts[0]["operation_ref"] == str(
                attempt.delivery_id
            ) and attempts[0]["attempt_ref"] == str(attempt.id)
        assert attempts[0]["code"] == "smtp_accepted" and attempts[0]["trace_id"]
        rendered = json.dumps(events)
        assert (
            ctx["recipient"].email not in rendered
            and "Resumen diario" not in rendered
            and "functional_content" not in rendered
            and "kWh" not in rendered
        )
        assert telemetry.logs.schema_rejected == 0
    finally:
        ctx["client"]._transport.app.state.telemetry = None
        ctx["service"].telemetry = None
        telemetry.shutdown()


async def test_full_technical_queue_cannot_change_rule_reads(
    notification_context, tmp_path
):
    """The actual bounded007 queue reports loss; it cannot become a functional readiness/transaction dependency."""
    ctx = notification_context
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "bounded"), autostart=False
    )
    ctx["client"]._transport.app.state.telemetry = telemetry
    try:
        for _ in range(1100):
            telemetry.complete(
                telemetry.begin("notification.query", "notifications"),
                event="notification.operation.completed",
            )
        assert telemetry.logs.dropped > 0 and telemetry.logs.depth <= 1024
        assert (
            await ctx["client"].get("/api/v1/notifications/rules")
        ).status_code == 200
    finally:
        ctx["client"]._transport.app.state.telemetry = None
        telemetry.shutdown()
