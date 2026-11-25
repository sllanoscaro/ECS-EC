"""Opt-in actual007 transport stack for008, isolated from the step4 retention trial."""

import asyncio

from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.observability.lifecycle import Policy, Telemetry

from backend.tests.integration.notifications.test_smtp_dispatch import (
    Outcomes,
    due_delivery,
)


async def test_notification_signals_reach_real_loki_jaeger(
    notification_context, gateway_root, gateway_client, deliver_telemetry
):
    """Actual Alloy/Loki and OTLP/Jaeger persist safe008 events/spans behind current Programador authorization."""
    ctx = notification_context
    telemetry = Telemetry(
        Policy(environment="test", spool=gateway_root / "spool"), autostart=False
    )
    ctx["service"].telemetry = telemetry
    ctx["client"]._transport.app.state.telemetry = telemetry
    try:
        await due_delivery(ctx)
        dispatcher = Dispatcher(ctx["service"], transport=Outcomes("aceptada"))
        try:
            await dispatcher.dispatch_once()
        finally:
            await dispatcher.close()
        emitted, observed = await deliver_telemetry(telemetry)
        attempts = [
            event
            for event in observed
            if event["event"] == "notification.delivery.attempt.completed"
        ]
        assert len(attempts) == 1 and any(
            event["event"] == "notification.scheduler.tick" for event in observed
        )
        reference = attempts[0]["trace_id"]
        assert reference
        for _ in range(40):
            trace = await gateway_client.get("/jaeger/api/v3/traces/" + reference)
            if trace.status_code == 200:
                break
            await asyncio.sleep(0.5)
        assert trace.status_code == 200, trace.text[:200]
        assert reference.lower() in trace.text.lower() or trace.json().get("result")
        assert (
            await gateway_client.get("/grafana/api/frontend/settings")
        ).status_code == 200
        dashboard = await gateway_client.get(
            "/grafana/api/dashboards/uid/ecs-notifications"
        )
        assert dashboard.status_code == 200, dashboard.text[:200]
        assert (
            await gateway_client.get("/grafana/api/dashboards/uid/foreign-dashboard")
        ).status_code == 403
        assert (
            await gateway_client.post("/grafana/api/dashboards/db", json={})
        ).status_code in {403, 405}
    finally:
        ctx["client"]._transport.app.state.telemetry = None
        ctx["service"].telemetry = None
        telemetry.shutdown()
