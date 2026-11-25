"""007 actual independent source outages preserve the other signal and historical missing references."""

import asyncio
import subprocess
import pytest

pytestmark = pytest.mark.integration


def component(project, action, name):
    """Control only this explicitly isolated007 test project's named technical service."""
    assert project.startswith("ecs007-")
    assert action in {"stop", "start", "restart"} and name in {
        "jaeger",
        "alloy",
        "loki",
    }
    subprocess.run(
        ["docker", action, f"{project}-{name}-1"], capture_output=True, check=True
    )


async def ready(client, path):
    """Wait for a real source after private DNS/startup, within a finite test deadline."""
    for _ in range(40):
        response = await client.get(path)
        if response.status_code == 200:
            return response
        await asyncio.sleep(0.5)
    raise AssertionError("Technical source did not recover")


async def test_jaeger_only_failure_keeps_logs_and_missing_trace(
    gateway_project, gateway_client, live_telemetry, deliver_telemetry
):
    """OTLP failure is observable while logs remain queryable; restart does not fabricate the missing trace."""
    component(gateway_project, "stop", "jaeger")
    try:
        handle = live_telemetry.begin("cost.query", "costs")
        live_telemetry.complete(handle)
        events, stored = await deliver_telemetry(live_telemetry, traces_expected=False)
        terminal = next(
            event for event in events if event["event"] == "operation.completed"
        )
        assert terminal["event_id"] in {event["event_id"] for event in stored}
        assert live_telemetry.status.snapshot()["trace_export_status"] == "degraded"
        assert live_telemetry.traces.failures == 1
    finally:
        component(gateway_project, "start", "jaeger")
    await ready(gateway_client, "/jaeger/api/v3/services")
    assert (
        await gateway_client.get("/jaeger/api/v3/traces/" + terminal["trace_id"])
    ).status_code == 404


async def test_logs_only_failure_keeps_queryable_traces(
    gateway_project, gateway_client, live_telemetry, deliver_telemetry
):
    """Stopping Alloy/Loki cannot remove actual Jaeger evidence or convert missing logs to activity zero."""
    component(gateway_project, "stop", "alloy")
    component(gateway_project, "stop", "loki")
    try:
        handle = live_telemetry.begin("cost.query", "costs")
        live_telemetry.complete(handle)
        events, stored = await deliver_telemetry(live_telemetry, logs_expected=False)
        assert stored == [] and live_telemetry.traces.status == "available"
        terminal = next(
            event for event in events if event["event"] == "operation.completed"
        )
        assert (
            await gateway_client.get("/jaeger/api/v3/traces/" + terminal["trace_id"])
        ).status_code == 200
    finally:
        component(gateway_project, "start", "loki")
        component(gateway_project, "start", "alloy")
    await ready(gateway_client, "/logs/loki/api/v1/labels")
