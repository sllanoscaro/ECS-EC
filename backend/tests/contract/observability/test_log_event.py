"""Validate emission against the normative closed schema, independently of runtime validation."""

import copy
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.loads(Path("specs/007-observabilidad-externa/contracts/log-event.schema.json").read_text())


@pytest.fixture
def event():
    """Provide an independent known valid envelope from the unit fixtures."""
    from uuid import uuid4
    return dict(schema_version=1, event_id=str(uuid4()), boot_id=str(uuid4()), sequence=1,
                timestamp="2026-11-02T00:00:00Z", environment="test", service_version="0.1.0",
                policy_revision="test-v1", event="operation.completed", operation="consumption.query_detail",
                stage="complete", source_module="consumption", severity="INFO", outcome="success",
                code="ok", context_status="unavailable", operation_ref=None, attempt_ref=None,
                execution_ref=None, publication_ref=None, parent_operation_ref=None, trace_id=None,
                span_id=None, duration_ms=100, counts=None, health=None)


def test_canonical_schema_and_roundtrip(event):
    """Packaged schema must equal the normative contract; safe bytes validate independently."""
    from ecs_ec.observability.events import serialize, SCHEMA as packaged
    assert packaged == SCHEMA
    encoded = serialize(event)
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(json.loads(encoded))
    assert len(encoded) <= 16384


@pytest.mark.parametrize("patch", [
    {"extra": "SECRET"}, {"schema_version": 2}, {"sequence": 0}, {"sequence": True},
    {"timestamp": "2026-11-02T00:00:00+00:00"}, {"timestamp": "nonsenseZ"},
    {"environment": "production"}, {"event_id": "bad"}, {"event": "client.event"},
    {"operation": "unknown"}, {"stage": "unknown"}, {"source_module": "unknown"},
    {"severity": "CRITICAL"}, {"outcome": "in_progress"}, {"duration_ms": -1},
    {"duration_ms": float("nan")}, {"duration_ms": float("inf")}, {"trace_id": "0" * 32},
    {"span_id": "1" * 16}, {"trace_id": "1" * 32}, {"operation_ref": "bad"},
    {"context_status": "available"}, {"counts": {"records_seen": -1}},
    {"counts": {"records_seen": 1.5}}, {"counts": {"body": "SECRET"}},
    {"service_version": ""}, {"policy_revision": "a" * 129},
    {"outcome": "unexpected_error", "severity": "INFO", "code": "calculation_failed"},
    {"outcome": "unexpected_error", "severity": "ERROR", "code": "ok"},
    {"event": "telemetry.heartbeat", "health": None},
])
def test_invalid_envelopes_fail_safely(event, patch):
    """Unknown fields, malformed identities, nonfinite values and inconsistent results reject safely."""
    from ecs_ec.observability.events import serialize, RejectedEvent
    event.update(patch)
    with pytest.raises(RejectedEvent, match="^schema_rejected$"):
        serialize(event)


def test_unregistered_code_is_never_exported(event):
    """An unknown code becomes the catalog fallback without retaining its source text."""
    from ecs_ec.observability.events import serialize
    event["code"] = "SECRET@example.test"
    data = serialize(event)
    assert b"SECRET" not in data
    assert json.loads(data)["code"] == "unclassified"


def test_health_requires_independent_evidence(event):
    """Available requires non-null success for that signal, not evidence from the other one."""
    from ecs_ec.observability.events import serialize, RejectedEvent
    event.update(event="telemetry.heartbeat", operation="telemetry", outcome="not_applicable")
    health = dict(logs_dropped_total=0, spans_dropped_total=0, schema_rejected_total=0,
                  log_queue_depth=0, span_queue_depth=0, log_collector_status="unknown",
                  last_log_collector_success=None, trace_export_status="unknown",
                  last_trace_export_success=None, trace_export_failures_total=0, trace_exported_spans_total=0)
    event["health"] = health
    serialize(event)
    for key in tuple(health):
        candidate = copy.deepcopy(event)
        del candidate["health"][key]
        with pytest.raises(RejectedEvent):
            serialize(candidate)
    for signal in ("log_collector", "trace_export"):
        candidate = copy.deepcopy(event)
        candidate["health"][signal + "_status"] = "available"
        with pytest.raises(RejectedEvent):
            serialize(candidate)
