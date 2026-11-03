"""Synthetic technical fixtures; never claim real business coverage from these events."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from ecs_ec.core.clock import FrozenClock


@pytest.fixture
def telemetry_clock():
    """Yield independent UTC/monotonic time, changed only by the requesting test."""
    return FrozenClock(datetime(2026, 11, 2, tzinfo=UTC))


@pytest.fixture
def safe_event():
    """Return a known complete schema-v1 event with opaque references and no business data."""
    return dict(schema_version=1, event_id=str(uuid4()), boot_id=str(uuid4()), sequence=1,
                timestamp="2026-11-02T00:00:00Z", environment="test", service_version="0.1.0",
                policy_revision="test-v1", event="operation.completed", operation="consumption.query_detail",
                stage="complete", source_module="consumption", severity="INFO", outcome="success",
                code="ok", context_status="available", operation_ref=str(uuid4()), attempt_ref=None,
                execution_ref=None, publication_ref=None, parent_operation_ref=None, trace_id=None,
                span_id=None, duration_ms=100, counts=None, health=None)
