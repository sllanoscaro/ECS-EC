"""Manual OTel spans with allowlisted attributes and independently bounded OTLP export.

No automatic HTTP/SQL instrumentation, body/header propagation or exception recording.
A private provider avoids ambient global processors and untrusted public parents.
"""

import asyncio
from collections import deque
import logging
import ssl
import threading
import time
from uuid import UUID

import httpx
from opentelemetry import trace
from opentelemetry.context import Context as OTelContext
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanLimits, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Link, SpanContext, Status, StatusCode

from ecs_ec.core.clock import SystemClock
from ecs_ec.observability.events import CODES, MODULES, OPERATIONS, STAGES


class DeadlineExporter(OTLPSpanExporter):
    """OTLP/HTTP exporter with <=3 attempts inside a real total5s deadline.

    The pinned base exporter is initialized with timeout=5, but its retry path is
    replaced to avoid nested retry budgets and raw response/exception diagnostics.
    Protobuf serialization happens only on sanitized SDK spans in the worker.
    """

    def __init__(self, endpoint="https://technical-gateway:8444/v1/traces", *, ca=None, cert=None,
                 key=None, transport=None, budget=5):
        """Prepare trusted TLS configuration; test transports/budgets are internal seams only."""
        # SDK transport diagnostics may include raw exceptions. No default handlers or
        # ambient OTLP logging may emit them, including errors during base shutdown.
        for name in ("opentelemetry.exporter.otlp", "opentelemetry.exporter.http", "httpx", "httpcore"):
            diagnostic = logging.getLogger(name)
            diagnostic.handlers = [logging.NullHandler()]
            diagnostic.propagate = False
        super().__init__(endpoint=endpoint, timeout=5)
        self.endpoint, self.budget, self.transport = endpoint, min(5, budget), transport
        self.tls = ssl.create_default_context(cafile=str(ca) if ca else None)
        if cert and key:
            self.tls.load_cert_chain(str(cert), str(key))

    async def send(self, payload):
        """Export immutable protobuf with finite response handling; return only safe success/failure."""
        try:
            async with asyncio.timeout(self.budget):
                async with httpx.AsyncClient(verify=self.tls, transport=self.transport, trust_env=False,
                                            follow_redirects=False, timeout=self.budget) as client:
                    for attempt in range(3):
                        try:
                            async with client.stream("POST", self.endpoint, content=payload,
                                                     headers={"Content-Type": "application/x-protobuf"}) as response:
                                # Ignore response body/reason entirely. No redirects can
                                # leak client credentials or extend the ingestion scope.
                                if response.status_code == 200:
                                    # OTLP partial_success is not a confirmed full batch.
                                    body = b""
                                    async for chunk in response.aiter_bytes():
                                        body += chunk
                                        if len(body) > 65536:
                                            return SpanExportResult.FAILURE
                                    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceResponse
                                    result = ExportTraceServiceResponse.FromString(body)
                                    if result.partial_success.rejected_spans:
                                        return SpanExportResult.FAILURE
                                    return SpanExportResult.SUCCESS
                                if response.status_code not in {429, 502, 503, 504}:
                                    return SpanExportResult.FAILURE
                        except httpx.TransportError:
                            pass
                        if attempt < 2:
                            await asyncio.sleep(0.02 * (attempt + 1))
        except Exception:
            pass
        return SpanExportResult.FAILURE

    def export(self, spans):
        """Worker-only bounded serialization/export; never allow SDK failures into business calls."""
        try:
            return asyncio.run(self.send(encode_spans(spans).SerializeToString()))
        except Exception:
            return SpanExportResult.FAILURE


class _QueueProcessor(SpanProcessor):
    """Private SDK callback; puts sanitized finished spans into the bounded owner queue."""

    def __init__(self, owner):
        """Keep only the owning bounded transport, never a domain service."""
        self.owner = owner

    def on_start(self, span, parent_context=None):
        """Start has no export side effects; active capacity was reserved before SDK creation."""

    def on_end(self, span):
        """Queue one readable span or count its loss; no synchronous network/flush."""
        self.owner._enqueue(span)

    def shutdown(self):
        """Owner shutdown handles queue/export resources with its shared deadline."""

    def force_flush(self, timeout_millis=30000):
        """Never request a per-operation flush; callers receive no durability guarantee."""
        return False


class Traces:
    """Bound <=256 active/2048 pending spans, batches512, safe transport counters per boot."""

    def __init__(self, *, exporter=None, clock=None, autostart=True, active_limit=256,
                 pending_limit=2048, ratio=1.0, environment="local", version="0.1.0"):
        """Create a private SDK provider; optional daemon owns all OTLP network operations."""
        if not 1 <= active_limit <= 256 or not 1 <= pending_limit <= 2048 or not 0 <= ratio <= 1:
            raise ValueError("Invalid trace limits")
        self.clock, self.exporter = clock or SystemClock(), exporter or DeadlineExporter()
        self.active_limit, self.pending_limit = active_limit, pending_limit
        self._lock, self._wake, self._stop = threading.Lock(), threading.Event(), threading.Event()
        self._queue, self._active = deque(), {}
        self._closed = False
        self._inflight = 0
        self.dropped = self.failures = self.exported = 0
        self.status, self.last_success = "unknown", None
        self.provider = TracerProvider(resource=Resource({"service.name": "ecs-ec", "environment": environment,
                                                         "service.version": version}),
                                       sampler=ParentBased(TraceIdRatioBased(ratio)),
                                       span_limits=SpanLimits(max_attributes=32, max_attribute_length=128, max_events=0, max_links=1),
                                       shutdown_on_exit=False)
        self.provider.add_span_processor(_QueueProcessor(self))
        self.tracer = self.provider.get_tracer("ecs_ec.observability", "1")
        self._thread = threading.Thread(target=self._run, name="telemetry-otlp", daemon=True) if autostart else None
        if self._thread:
            self._thread.start()

    @property
    def depth(self):
        """Read pending span count without doing network or SDK work."""
        with self._lock:
            return len(self._queue)

    def begin(self, operation, attributes, *, parent=None, links=()):
        """Create only catalog-named manual spans from strict allowlisted primitive attributes.

        Parent is an internally held span, never public propagation. Roots start from
        empty OTel context even when ambient instrumentation has untrusted context.
        """
        try:
            if operation not in OPERATIONS or type(attributes) is not dict or len(attributes) > 28:
                raise ValueError()
            allowed = {"operation_ref", "attempt_ref", "execution_ref", "publication_ref", "parent_operation_ref",
                       "context_status", "stage", "source_module", "policy_revision"}
            if not attributes.keys() <= allowed:
                raise ValueError()
            for key, value in attributes.items():
                if type(value) is not str or len(value) > 128:
                    raise ValueError()
                if key.endswith("_ref"):
                    UUID(value)
                if key == "stage" and value not in STAGES or key == "source_module" and value not in MODULES:
                    raise ValueError()
                if key == "context_status" and value not in {"available", "unavailable", "recovered"}:
                    raise ValueError()
            if type(links) is not tuple or len(links) > 1 or any(type(link) is not SpanContext or not link.is_valid or link.is_remote for link in links):
                raise ValueError()
            safe_links = tuple(Link(link) for link in links)
            with self._lock:
                if self._closed or len(self._active) >= self.active_limit:
                    self.dropped += 1
                    return None
                # Reserve before constructing SDK state; no lock is held by network.
                reservation = object()
                self._active[reservation] = None
            context = trace.set_span_in_context(parent, OTelContext()) if parent else OTelContext()
            started = int(self.clock.now().timestamp() * 1_000_000_000)
            monotonic = self.clock.monotonic()
            span = self.tracer.start_span(operation, context=context, attributes=attributes, links=safe_links, start_time=started)
            with self._lock:
                del self._active[reservation]
                self._active[id(span)] = (span, started, monotonic)
            return span
        except Exception:
            self.dropped += 1
            return None

    def end(self, span, outcome, code):
        """Finish once with common outcome/status; record no raw exception, stack or status text."""
        if span is None:
            return
        with self._lock:
            if id(span) not in self._active:
                return
            _, started, monotonic = self._active.pop(id(span))
        if type(outcome) is not str or outcome not in {"success", "expected_rejection", "unexpected_error"} or type(code) is not str or (outcome == "unexpected_error" and code == "ok"):
            self.dropped += 1
            return
        span.set_attribute("outcome", outcome)
        span.set_attribute("code", code if type(code) is str and code in CODES else "unclassified")
        span.set_status(Status({"success": StatusCode.OK, "expected_rejection": StatusCode.UNSET,
                                "unexpected_error": StatusCode.ERROR}[outcome]))
        # A wall-clock correction must not produce a negative technical span duration.
        elapsed = max(0, int((self.clock.monotonic() - monotonic) * 1_000_000_000))
        span.end(end_time=started + elapsed)

    def _enqueue(self, span):
        """Enforce encoded span size and pending capacity before export admission."""
        try:
            size = len(encode_spans([span]).SerializeToString())
            if size > 16384:
                raise ValueError()
            with self._lock:
                if self._closed or len(self._queue) >= self.pending_limit:
                    self.dropped += 1
                    return
                self._queue.append(span)
            self._wake.set()
        except Exception:
            self.dropped += 1

    def take_batch(self):
        """Pop at most512 already sanitized readable spans without waiting for network."""
        with self._lock:
            return [self._queue.popleft() for _ in range(min(512, len(self._queue)))]

    def observe_batch(self, count, result):
        """Record final batch outcome once, independently of its internal transport retries."""
        with self._lock:
            if result is SpanExportResult.SUCCESS:
                self.exported += count
                self.status = "available"
                self.last_success = self.clock.now().isoformat().replace("+00:00", "Z")
            else:
                self.failures += 1
                self.status = "degraded"

    def _run(self):
        """Export finite batches in a daemon; failures never reenter the technical log emitter."""
        while not self._stop.is_set():
            self._wake.wait(0.2)
            self._wake.clear()
            batch = self.take_batch()
            if batch:
                with self._lock:
                    self._inflight = len(batch)
                try:
                    result = self.exporter.export(batch)
                except Exception:
                    result = SpanExportResult.FAILURE
                with self._lock:
                    observe = not self._closed
                    self._inflight = 0
                if observe:
                    self.observe_batch(len(batch), result)

    def shutdown(self, budget=5):
        """Drain up to remaining shared budget; count queued/active residual losses without fake success."""
        deadline = time.monotonic() + max(0, min(5, budget))
        self._wake.set()
        while self._thread and self.depth and time.monotonic() < deadline:
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        self._stop.set()
        with self._lock:
            self._closed = True
            self.dropped += len(self._queue) + len(self._active) + self._inflight
            self._inflight = 0
            self._queue.clear()
            self._active.clear()
        self._wake.set()
        if self._thread:
            self._thread.join(max(0, deadline - time.monotonic()))
        # Avoid unbounded provider/HTTP shutdown if a foreign test transport is stuck.
        if not self._thread or not self._thread.is_alive():
            self.exporter.shutdown()
            self.provider.shutdown()
