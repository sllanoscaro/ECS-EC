"""Isolated DTO/port shape checks; no claim of a reception/storage002 implementation."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from ecs_ec.consumption.models import ReceptionResult, ReconfigurationBounds
from ecs_ec.consumption.ports import MeasurementStore, Reception


def test_explicit_ports():
    """Require all coordinated reads and reception without importing a provider."""
    assert all(callable(getattr(MeasurementStore, name)) for name in
        ("read_detail", "read_extent", "read_update_state", "read_reconfiguration_bounds"))
    assert callable(Reception.accept)
    assert callable(Reception.read_attempt)


def test_bounds_require_every_key_and_preserve_retired_history():
    """Null is a real absence; missing keys/provider state cannot mean empty history."""
    bound = ReconfigurationBounds(has_accepted_history=True,
        latest_interval_end_by_category={"CAT-01": datetime(2026, 1, 2, tzinfo=UTC), "CAT-03": None})
    bound.require_categories(("CAT-01", "CAT-03"))
    assert bound.has_accepted_history
    with pytest.raises(ValueError): bound.require_categories(("CAT-01", "CAT-05"))
    with pytest.raises(ValidationError): ReconfigurationBounds(has_accepted_history=False,
        latest_interval_end_by_category={"CAT-01": datetime(2026, 1, 2, tzinfo=UTC)})


def test_reception_result_references():
    """Accepted/duplicate references are mandatory; rejection cannot assert acceptance."""
    for status in ("accepted", "duplicate"):
        result = ReceptionResult(position=0, status=status, category_id="CAT-03", measurement_id=UUID(int=1),
            measurement_revision=1, category_revision=1, correlation_ref="synthetic")
        assert result.measurement_id == UUID(int=1)
        with pytest.raises(ValidationError): ReceptionResult(position=0, status=status, correlation_ref="synthetic")
    result = ReceptionResult(position=1, status="rejected", reason_code="conflict", correlation_ref="synthetic")
    assert result.measurement_id is None
