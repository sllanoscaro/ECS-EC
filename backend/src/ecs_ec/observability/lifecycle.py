"""Optional monolith emitter facade; safe policy validation and <=5s shared technical shutdown."""

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path
import ssl
import sys
import threading
import time
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.lifecycle import Module
from ecs_ec.observability.context import Context, new_context, recover
from ecs_ec.observability.events import MODULES, OPERATIONS, STAGES
from ecs_ec.observability.health import Health
from ecs_ec.observability.logging import LogEmitter
from ecs_ec.observability.tracing import DeadlineExporter, Traces


class Policy(BaseModel):
    """Trusted configuration before activation; technical errors never become functional startup errors."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, frozen=True)
    environment: Literal["local", "test", "vps"] = "local"
    spool: Path
    version: str = Field(default="0.1.0", min_length=1, max_length=128)
    revision: str = Field(default="007-v1", min_length=1, max_length=128)
    retention_hours: Literal[24, 168] = 168
    trace_ratio: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)
    endpoint: str = "https://technical-gateway:8444/v1/traces"
    health_endpoint: str = "https://technical-gateway:8446/collector-health"
    ca: Path | None = None
    cert: Path | None = None
    key: Path | None = None
    health_cert: Path | None = None
    health_key: Path | None = None

    @model_validator(mode="after")
    def validate_transport(self):
        """Require exact HTTPS ingestion/health paths and complete distinct process credentials."""
        from urllib.parse import urlsplit
        for endpoint, path in ((self.endpoint, "/v1/traces"), (self.health_endpoint, "/collector-health")):
            url = urlsplit(endpoint)
            if url.scheme != "https" or not url.hostname or url.path != path or url.username or url.query or url.fragment:
                raise ValueError("Invalid telemetry endpoint")
        if self.environment != "test" and self.retention_hours != 168:
            raise ValueError("Disposable retention requires test environment")
        return self


@dataclass
class Operation:
    """Transient internal handle; producer owns durable transition uniqueness and commit timing."""

    operation: str
    source_module: str
    context: Context
    started: float
    span: object = None
    closed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class Telemetry:
    """Begin/stage/complete/continue/health/shutdown best-effort ports, isolated from business state.

    Each handle emits at most one terminal per execution. This is not a durable
    deduplicator: producer must call terminal only after winning its committed
    transition. A crash after commit may lose telemetry; never claim accounting accuracy.
    """

    def __init__(self, policy: Policy | None = None, *, clock=None, autostart=True):
        """Initialize safe policy/queues; a None policy is a no-resource disabled facade."""
        self.policy, self.clock = policy, clock or SystemClock()
        self.logs = self.traces = self.status = None
        self._stop = threading.Event()
        self._thread = None
        if policy is None:
            return
        exporter = DeadlineExporter(policy.endpoint, ca=policy.ca, cert=policy.cert, key=policy.key)
        self.logs = LogEmitter(policy.spool, clock=self.clock, autostart=autostart, ttl_seconds=policy.retention_hours * 3600)
        self.traces = Traces(exporter=exporter, clock=self.clock, autostart=autostart,
                             ratio=policy.trace_ratio, environment=policy.environment, version=policy.version)
        self.status = Health(self.logs, self.traces, clock=self.clock)
        self._emit(None, event="policy.changed", operation="telemetry", source_module="observability",
                   stage="observe", outcome="not_applicable")
        if autostart:
            self._thread = threading.Thread(target=self._heartbeat_loop, name="telemetry-health", daemon=True)
            self._thread.start()

    @classmethod
    def from_environment(cls, values=None, *, clock=None):
        """Validate external settings before enabling; errors disable only telemetry with fixed stderr.

        The composition root passes environment values (Compose injects .env values).
        Secrets are filesystem paths; their contents never enter configuration repr/logs.
        """
        values = os.environ if values is None else values
        if values.get("OBS_ENABLED", "false").lower() == "false":
            return cls(clock=clock)
        try:
            if values.get("OBS_ENABLED") != "true":
                raise ValueError()
            required = ["OBS_SPOOL", "OBS_CA", "OBS_APP_CERT", "OBS_APP_KEY", "OBS_HEALTH_CERT", "OBS_HEALTH_KEY"]
            if any(not values.get(key) for key in required):
                raise ValueError()
            policy = Policy(spool=values["OBS_SPOOL"], environment=values.get("OBS_ENVIRONMENT", "local"),
                            version=values.get("OBS_SERVICE_VERSION", "0.1.0"), revision=values.get("OBS_POLICY_REVISION", "007-v1"),
                            retention_hours=int(values.get("OBS_RETENTION_HOURS", "168")),
                            trace_ratio=float(values.get("OBS_TRACE_RATIO", "1.0")),
                            endpoint=values.get("OBS_OTLP_ENDPOINT", "https://technical-gateway:8444/v1/traces"),
                            health_endpoint=values.get("OBS_HEALTH_ENDPOINT", "https://technical-gateway:8446/collector-health"),
                            ca=values["OBS_CA"], cert=values["OBS_APP_CERT"], key=values["OBS_APP_KEY"],
                            health_cert=values["OBS_HEALTH_CERT"], health_key=values["OBS_HEALTH_KEY"])
            if policy.cert == policy.health_cert or policy.key == policy.health_key:
                raise ValueError()
            for path in (policy.ca, policy.cert, policy.key, policy.health_cert, policy.health_key):
                if not path.is_absolute() or not path.is_file():
                    raise ValueError()
            health_tls = ssl.create_default_context(cafile=str(policy.ca))
            health_tls.load_cert_chain(str(policy.health_cert), str(policy.health_key))
            return cls(policy, clock=clock)
        except Exception:
            print("telemetry_disabled: invalid_technical_configuration", file=sys.stderr)
            return cls(clock=clock)

    def _emit(self, handle, *, event, stage, outcome, operation=None, source_module=None, code="ok", duration_ms=None, counts=None, health=None, control=False):
        """Build only catalog primitives and admit safely; arbitrary domain data is never formatted."""
        if not self.logs:
            return "disabled"
        try:
            context = handle.context if handle else Context()
            span_context = handle.span.get_span_context() if handle and handle.span else None
            envelope = dict(schema_version=1, event_id=str(uuid4()), boot_id=self.logs.boot_id, sequence=1,
                            timestamp=self.clock.now().isoformat().replace("+00:00", "Z"),
                            environment=self.policy.environment, service_version=self.policy.version,
                            policy_revision=self.policy.revision, event=event, operation=operation or handle.operation,
                            source_module=source_module or handle.source_module, stage=stage,
                            severity="ERROR" if outcome == "unexpected_error" else "WARNING" if outcome == "expected_rejection" else "INFO",
                            outcome=outcome, code=code, duration_ms=duration_ms, counts=counts, health=health,
                            trace_id=f"{span_context.trace_id:032x}" if span_context and span_context.is_valid else None,
                            span_id=f"{span_context.span_id:016x}" if span_context and span_context.is_valid else None,
                            **context.fields())
            return self.logs.emit(envelope, control=control)
        except Exception:
            self.logs.schema_rejected += 1
            self.logs.dropped += 1
            return "dropped"

    def begin(self, operation, source_module, *, context=None, parent=None):
        """Begin a trusted catalog operation without adopting ambient/public propagation."""
        if not self.policy:
            return None
        if type(operation) is not str or operation not in OPERATIONS or type(source_module) is not str or source_module not in MODULES or context is not None and type(context) is not Context:
            self.logs.schema_rejected += 1
            return None
        try:
            context = context or new_context(parent_operation_ref=parent.context.operation_ref if parent else None)
            attributes = {k: v for k, v in context.fields().items() if v is not None}
            attributes.update(source_module=source_module, policy_revision=self.policy.revision)
            span = self.traces.begin(operation, attributes)
            handle = Operation(operation, source_module, context, self.clock.monotonic(), span)
            self._emit(handle, event="operation.started", stage="start", outcome="in_progress")
            return handle
        except Exception:
            self.logs.schema_rejected += 1
            return None

    def stage(self, handle, stage, *, outcome="success", code="ok", duration_ms=None):
        """Emit a registered completed stage as a child span/log, never another operation terminal."""
        if not self.policy or handle is None:
            return "disabled"
        if type(handle) is not Operation or type(stage) is not str or stage not in STAGES or handle.closed or type(outcome) is not str or outcome not in {"success", "expected_rejection", "unexpected_error"} or type(code) is not str:
            return "dropped"
        child = self.traces.begin(handle.operation, {"stage": stage}, parent=handle.span)
        self.traces.end(child, outcome, code)
        return self._emit(handle, event="stage.completed", stage=stage, outcome=outcome, code=code, duration_ms=duration_ms)

    def complete(self, handle, *, outcome="success", code="ok", counts=None, event="operation.completed"):
        """Close a transient handle once; logical transition/summary ownership stays with producer.

        Special reception/report terminal semantics are completed in007's US2 task,
        which requires real producers; this foundational facade accepts ordinary terminals.
        """
        if not self.policy or handle is None:
            return "disabled"
        if type(handle) is not Operation or type(outcome) is not str or outcome not in {"success", "expected_rejection", "unexpected_error"} or type(code) is not str:
            self.logs.schema_rejected += 1
            return "dropped"
        with handle.lock:
            if handle.closed or event != "operation.completed":
                return "dropped"
            handle.closed = True
        result = self._emit(handle, event=event, stage="complete", outcome=outcome, code=code,
                            counts=counts, duration_ms=max(0, (self.clock.monotonic() - handle.started) * 1000))
        self.traces.end(handle.span, outcome, code)
        return result

    def continue_operation(self, operation, source_module, context):
        """Continue a trusted durable attempt with fresh execution/tracing root; no invented parent."""
        try:
            return self.begin(operation, source_module, context=recover(context))
        except Exception:
            return None

    def health(self):
        """Admit the replaceable mandatory health snapshot; never imply functional readiness."""
        if not self.policy:
            return "disabled"
        return self._emit(None, event="telemetry.heartbeat", stage="observe", operation="telemetry",
                          source_module="observability", outcome="not_applicable", health=self.status.snapshot(), control=True)

    def _heartbeat_loop(self):
        """Poll only permitted health counters and emit every15s, independently of domain requests."""
        import asyncio
        tls = None
        try:
            if self.policy.ca and self.policy.health_cert and self.policy.health_key:
                tls = ssl.create_default_context(cafile=str(self.policy.ca))
                tls.load_cert_chain(str(self.policy.health_cert), str(self.policy.health_key))
        except Exception:
            self.status.observe_collector(success=False)
        next_tick = self.clock.monotonic()
        while not self._stop.is_set():
            if tls:
                asyncio.run(self.status.poll(self.policy.health_endpoint, tls))
            self.health()
            next_tick += 15
            now = self.clock.monotonic()
            if now > next_tick + 15:
                next_tick = now
            self._stop.wait(max(0, next_tick - now))

    def shutdown(self):
        """Stop health and drain both signals within one total5s budget; residual losses are counted."""
        deadline = time.monotonic() + 5
        self._stop.set()
        if self._thread:
            self._thread.join(max(0, deadline - time.monotonic()))
        if self.logs:
            self.logs.shutdown(max(0, deadline - time.monotonic()))
        if self.traces:
            self.traces.shutdown(max(0, deadline - time.monotonic()))


def observability_module(clock):
    """Register007 as an optional existing009 lifecycle extension, without owning core resources."""
    @asynccontextmanager
    async def lifespan(app):
        """Initialize only technical state after core readiness; always close within technical budget."""
        import asyncio
        telemetry = Telemetry.from_environment(clock=clock)
        app.state.telemetry = telemetry
        try:
            yield
        finally:
            await asyncio.to_thread(telemetry.shutdown)
    return Module("observability", lifespan=lifespan)
