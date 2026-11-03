"""Verify bounded manual OTel spans and total-deadline transport without private attributes."""

import asyncio
import time
import httpx
from opentelemetry.sdk.trace.export import SpanExportResult


def test_span_limits_results_and_sanitization():
    """Only catalog fields reach SDK; active/pending limits shed spans without blocking."""
    from ecs_ec.observability.tracing import Traces
    traces = Traces(autostart=False, active_limit=2, pending_limit=2)
    a = traces.begin("cost.calculate", {"operation_ref": "11111111-1111-4111-8111-111111111111"})
    b = traces.begin("cost.compare", {})
    assert traces.begin("cost.query", {}) is None
    traces.end(a, "success", "ok")
    traces.end(b, "expected_rejection", "permission_denied")
    c = traces.begin("cost.calculate", {})
    traces.end(c, "unexpected_error", "calculation_failed")
    assert traces.depth == 2
    assert traces.dropped == 2
    spans = traces.take_batch()
    assert len(spans) == 2
    assert spans[0].status.status_code.name == "OK"
    assert spans[1].status.status_code.name == "UNSET"
    assert all(len(s.attributes) <= 32 and "exception" not in str(s.attributes) for s in spans)
    assert traces.begin("public-name-SECRET", {}) is None
    assert traces.begin("cost.query", {"password": "SECRET"}) is None
    traces.shutdown(0)


async def test_total_deadline_retries_and_independent_batch_counters(telemetry_clock):
    """Retry attempts share a real deadline and count a failed/confirmed batch only once."""
    from ecs_ec.observability.tracing import DeadlineExporter, Traces
    calls = []
    async def unavailable(request):
        """Return a retryable failure with private response text that must stay unobserved."""
        calls.append(1)
        return httpx.Response(503, text="SECRET")
    exporter = DeadlineExporter(transport=httpx.MockTransport(unavailable), budget=0.1)
    result = await exporter.send(b"safe-protobuf")
    assert result == SpanExportResult.FAILURE
    assert 1 <= len(calls) <= 3
    async def stalled(request):
        """Simulate a network peer that never responds inside the total deadline."""
        await asyncio.sleep(2)
        return httpx.Response(200)
    exporter = DeadlineExporter(transport=httpx.MockTransport(stalled), budget=0.05)
    start = time.monotonic()
    assert await exporter.send(b"safe") == SpanExportResult.FAILURE
    assert time.monotonic() - start < 0.5
    traces = Traces(autostart=False, clock=telemetry_clock)
    traces.observe_batch(3, SpanExportResult.FAILURE)
    assert traces.failures == 1 and traces.exported == 0
    assert traces.status == "degraded" and traces.last_success is None
    traces.observe_batch(3, SpanExportResult.SUCCESS)
    assert traces.failures == 1 and traces.exported == 3
    assert traces.status == "available" and traces.last_success.endswith("Z")


def test_export_worker_stall_and_shutdown_counts_inflight():
    """A stalled exporter is isolated to its daemon; bounded shutdown counts in-flight losses."""
    import threading
    from ecs_ec.observability.tracing import Traces
    entered, release = threading.Event(), threading.Event()
    class Exporter:
        """Controlled sink used only to simulate a real worker stalled outside business locks."""
        def export(self, spans):
            """Wait for test release and return a transport failure, never private diagnostics."""
            entered.set()
            release.wait(2)
            return SpanExportResult.FAILURE
        def shutdown(self):
            """No external resources exist in this synthetic sink."""
    traces = Traces(exporter=Exporter())
    span = traces.begin("cost.query", {})
    traces.end(span, "success", "ok")
    assert entered.wait(1)
    start = time.monotonic()
    traces.shutdown(0.05)
    assert time.monotonic() - start < 0.5
    assert traces.dropped == 1
    release.set()


async def test_otlp_partial_success_is_not_full_confirmation():
    """Partial OTLP acceptance is conservatively failed; a complete response confirms the batch."""
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
    from ecs_ec.observability.tracing import DeadlineExporter
    response = ExportTraceServiceResponse()
    response.partial_success.rejected_spans = 1
    async def partial(request):
        """Return a valid partial-success protobuf without exposing server diagnostic text."""
        return httpx.Response(200, content=response.SerializeToString())
    exporter = DeadlineExporter(transport=httpx.MockTransport(partial))
    assert await exporter.send(b"safe") == SpanExportResult.FAILURE
    response.partial_success.rejected_spans = 0
    assert await exporter.send(b"safe") == SpanExportResult.SUCCESS


def test_span_timestamps_and_duration_use_common_clock(telemetry_clock):
    """Trace timing shares the injected UTC/monotonic clock, including wall-clock-independent duration."""
    from ecs_ec.observability.tracing import Traces
    traces = Traces(autostart=False, clock=telemetry_clock)
    start = int(telemetry_clock.now().timestamp() * 1_000_000_000)
    span = traces.begin("cost.query", {})
    telemetry_clock.advance(0.25)
    traces.end(span, "success", "ok")
    exported = traces.take_batch()[0]
    assert exported.start_time == start
    assert exported.end_time - exported.start_time == 250_000_000
    traces.shutdown(0)


def test_invalid_final_result_never_reaches_sdk_export_queue():
    """Malformed results or missing failure code abort the technical span without domain exceptions."""
    from ecs_ec.observability.tracing import Traces
    traces = Traces(autostart=False)
    for outcome, code in (({}, "ok"), ("unexpected_error", "ok"), ("success", object())):
        span = traces.begin("cost.query", {})
        traces.end(span, outcome, code)
    assert traces.depth == 0
    assert traces.dropped == 3
    traces.shutdown(0)
