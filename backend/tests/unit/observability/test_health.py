"""Health has separate evidence for logs and traces; inactivity is never invented failure."""


def test_no_evidence_and_independent_success(telemetry_clock, tmp_path):
    """Observe signal-specific success/failure and preserve last success across later failures."""
    from ecs_ec.observability.health import Health
    from ecs_ec.observability.logging import LogEmitter
    from ecs_ec.observability.tracing import Traces
    from opentelemetry.sdk.trace.export import SpanExportResult
    log = LogEmitter(tmp_path, autostart=False, clock=telemetry_clock)
    traces = Traces(autostart=False, clock=telemetry_clock)
    health = Health(log, traces, clock=telemetry_clock)
    assert health.snapshot()["trace_export_status"] == "unknown"
    assert health.snapshot()["log_collector_status"] == "unknown"
    health.observe_collector(success=True, dropped=0)
    snapshot = health.snapshot()
    assert snapshot["log_collector_status"] == "available"
    assert snapshot["last_log_collector_success"].endswith("Z")
    assert snapshot["trace_export_status"] == "unknown"
    traces.observe_batch(2, SpanExportResult.SUCCESS)
    previous = health.snapshot()["last_trace_export_success"]
    telemetry_clock.advance(60)
    assert health.snapshot()["trace_export_status"] == "available"
    traces.observe_batch(1, SpanExportResult.FAILURE)
    assert health.snapshot()["trace_export_status"] == "degraded"
    assert health.snapshot()["last_trace_export_success"] == previous
    health.observe_collector(success=False)
    assert health.snapshot()["log_collector_status"] == "degraded"


def test_heartbeat_unknown_after_45_seconds(telemetry_clock, tmp_path):
    """Missing heartbeat is unknown after45s, independently of measured operation count."""
    from ecs_ec.observability.health import heartbeat_continuity
    assert heartbeat_continuity(None, telemetry_clock.now()) == "unknown"
    last = telemetry_clock.now()
    telemetry_clock.advance(45)
    assert heartbeat_continuity(last, telemetry_clock.now()) == "observed"
    telemetry_clock.advance(0.001)
    assert heartbeat_continuity(last, telemetry_clock.now()) == "unknown"


async def test_poll_filters_metrics_and_requires_delivery(telemetry_clock, tmp_path, monkeypatch):
    """A healthy HTTP response is insufficient; only increasing sent counters establish log success."""
    import httpx
    from ecs_ec.observability import health as module
    from ecs_ec.observability.health import Health
    from ecs_ec.observability.logging import LogEmitter
    from ecs_ec.observability.tracing import Traces
    log = LogEmitter(tmp_path, autostart=False)
    traces = Traces(autostart=False)
    health = Health(log, traces, clock=telemetry_clock)
    replies = ["# healthy\nprivate_metric{password=\"SECRET\"} 5\n",
               "loki_write_sent_entries_total{endpoint=\"private\"} 2\nloki_write_dropped_entries_total 1\n",
               "loki_write_sent_entries_total 2\n", None]
    async def serve(request):
        """Yield finite synthetic Alloy metrics or an observed HTTP failure."""
        text = replies.pop(0)
        return httpx.Response(200, text=text) if text else httpx.Response(503)
    real_client = httpx.AsyncClient
    def client(**kwargs):
        """Inject transport only; no network/TLS bypass or production collector is contacted."""
        return real_client(**kwargs, transport=httpx.MockTransport(serve))
    monkeypatch.setattr(module.httpx, "AsyncClient", client)
    await health.poll("https://technical-gateway:8446/collector-health", True)
    assert health.snapshot()["log_collector_status"] == "unknown"
    await health.poll("https://technical-gateway:8446/collector-health", True)
    assert health.snapshot()["log_collector_status"] == "available"
    assert health.snapshot()["collector_dropped_total"] == 1
    assert "SECRET" not in str(health.snapshot())
    assert health.snapshot()["trace_export_status"] == "unknown"
    previous = health.snapshot()["last_log_collector_success"]
    telemetry_clock.advance(15)
    await health.poll("https://technical-gateway:8446/collector-health", True)
    assert health.snapshot()["last_log_collector_success"] == previous
    await health.poll("https://technical-gateway:8446/collector-health", True)
    assert health.snapshot()["log_collector_status"] == "degraded"
    assert health.snapshot()["last_log_collector_success"] == previous
    log.shutdown(0)
    traces.shutdown(0)
