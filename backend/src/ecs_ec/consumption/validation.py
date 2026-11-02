"""Pure physical-reading normalization; source history and exact energy are validated before002 admission."""

from typing import Any
from uuid import UUID

from pydantic import Field, ValidationError

from ecs_ec.consumption.energy import decimal_value, to_kwh
from ecs_ec.consumption.models import CategoryId, DomainModel, Period, ValidatedMeasurement


class MeasurementError(ValueError):
    """Per-record safe reason, with no payload, source body or database details."""

    def __init__(self, code):
        """Expose a fixed normalization reason to002 without attempting admission or persistence."""
        self.code = code
        super().__init__(code)


class RawMeasurement(Period):
    """Typed envelope around untrusted scalar energy/unit values; unknown fields are rejected."""

    building_id: UUID
    category_id: CategoryId
    source_id: UUID
    value: Any
    unit: Any
    source_evidence_ref: str = Field(min_length=1, max_length=200)
    correlation_ref: str = Field(min_length=1, max_length=200)


def covering_segments(segments, start, end):
    """Clip a full ordered configuration partition to [start,end); reject gaps/overlap/unconfigured spans."""
    period = Period(start=start, end=end)
    result, cursor = [], period.start
    for segment in sorted(segments, key=lambda s: s.start):
        lower, upper = max(segment.start, period.start), min(segment.end, period.end)
        if lower >= upper: continue
        if lower != cursor: raise ValueError("configuration_missing_or_overlapping")
        result.append(segment.model_copy(update={"start": lower, "end": upper}))
        cursor = upper
    if cursor != period.end: raise ValueError("configuration_missing_or_overlapping")
    return tuple(result)


class MeasurementValidator:
    """Convert physical energy and verify a stable category source across every historical segment."""

    def normalize(self, record, segments) -> ValidatedMeasurement:
        """Return exact normalized evidence or MeasurementError; do not assign IDs, write or accept."""
        try:
            raw = RawMeasurement.model_validate(record)
        except ValidationError as error:
            code = "unknown_category" if any(e["loc"] == ("category_id",) for e in error.errors()) else "invalid_measurement"
            raise MeasurementError(code) from None
        try:
            selected = covering_segments(segments, raw.start, raw.end)
        except ValueError:
            raise MeasurementError("source_configuration_missing") from None
        first = selected[0]
        signatures = {(s.category_revision, s.source_mode, s.source_id) for s in selected}
        if len(signatures) != 1: raise MeasurementError("source_configuration_changed")
        if first.source_mode != "measured" or first.source_id != raw.source_id:
            raise MeasurementError("unknown_or_uninstalled_source")
        try:
            if not isinstance(raw.unit, str): raise ValueError("unsupported_unit")
            energy = to_kwh(raw.value, raw.unit)
        except ValueError as error:
            raise MeasurementError(str(error)) from None
        return ValidatedMeasurement(building_id=raw.building_id, category_id=raw.category_id, source_id=raw.source_id,
            start=raw.start, end=raw.end, original_value=decimal_value(raw.value), original_unit=raw.unit,
            original_value_text=str(raw.value), energy_kwh=energy, configuration_revision=first.configuration_revision,
            category_revision=first.category_revision, source_evidence_ref=raw.source_evidence_ref, correlation_ref=raw.correlation_ref)
