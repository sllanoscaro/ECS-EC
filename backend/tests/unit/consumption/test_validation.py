"""Exact normalization boundaries and historical source validity, with no admission/storage double."""

from decimal import Decimal
from uuid import UUID

import pytest

from ecs_ec.consumption.catalog_storage import configuration_segments
from ecs_ec.consumption.models import instant
from ecs_ec.consumption.validation import MeasurementError, MeasurementValidator
from backend.tests.unit.consumption.test_catalog import installation, revision

START, END = instant("2026-01-01T00:00:00Z"), instant("2026-01-01T01:00:00Z")


def record(**changes):
    """Build valid textual evidence; changes intentionally include invalid raw types for rejection tests."""
    return dict(building_id=UUID(int=99), category_id="CAT-05", source_id=UUID(int=5),
        start=START, end=END, value="1", unit="kWh", source_evidence_ref="synthetic:file:1",
        correlation_ref="synthetic:publication:1", **{}) | changes


def normalize(data, revisions=None):
    """Resolve category segments from known history, then invoke production pure normalization."""
    segments = configuration_segments(revisions or (revision(),), "CAT-05", START, END)
    return MeasurementValidator().normalize(data, segments)


def test_independent_fixture_units_and_originals(scenarios):
    """Known three-interval values have exact kWh while source unit/value/evidence remain unchanged."""
    for row in scenarios["records"]:
        config = revision(installation(tuple(range(1, 8)), **{str(i): UUID(scenarios["sources"][f"CAT-{i:02}"]) for i in range(1, 8)}))
        input_row = record(**{k: v for k, v in row.items() if k != "expected_kwh"})
        start, end = instant(row["start"]), instant(row["end"])
        result = MeasurementValidator().normalize(input_row, (config.segment(row["category_id"], start, end),))
        assert result.energy_kwh == Decimal(row["expected_kwh"])
        assert result.original_value_text == row["value"]
        assert result.original_unit == row["unit"]
        assert result.source_evidence_ref == "synthetic:file:1"


def test_quantum_and_maximum_in_every_unit(scenarios):
    """q and M are unit-invariant; output never depends on the ambient precision28 context."""
    for values, expected in ((scenarios["boundaries"]["equivalent_minimum"], scenarios["boundaries"]["q"]),
                             (scenarios["boundaries"]["equivalent_maximum"], scenarios["boundaries"]["M"])):
        for unit, value in values.items():
            assert normalize(record(value=value, unit=unit)).energy_kwh == Decimal(expected)
    for value in scenarios["boundaries"]["outside"]:
        with pytest.raises(MeasurementError, match="energy_out_of_supported_range"): normalize(record(value=value))


@pytest.mark.parametrize("unit,value", [("Wh","1e33"),("kWh","1e30"),("MWh","1e27"),
    ("Wh","1e-13"),("kWh","1e-16"),("MWh","1e-19"),
    ("Wh","1.1e-12"),("kWh","1.1e-15"),("MWh","1.1e-18")])
def test_outside_quantum_and_maximum_are_unit_invariant(unit,value):
    """Outside-equivalent quantities reject with the same explicit reason in all three units."""
    with pytest.raises(MeasurementError, match="energy_out_of_supported_range"):
        normalize(record(unit=unit,value=value))


@pytest.mark.parametrize("unit,value", [("Wh", "1000.00000"), ("kWh", "1.00000000000000000000000000000000000000000000000000000000"), ("MWh", "1e-3")])
def test_equivalent_representations(unit, value):
    """Trailing zeros/exponents do not trigger rounding or change duplicate identity quantities."""
    result = normalize(record(value=value, unit=unit))
    assert result.energy_kwh == Decimal(1)
    assert result.original_value_text == value


@pytest.mark.parametrize("changes", [dict(value=True), dict(value=1.5), dict(value="-1"), dict(value="NaN"),
    dict(value="Infinity"), dict(value="-Infinity"), dict(value={}), dict(unit="W"), dict(category_id="CAT-99"),
    dict(source_id=UUID(int=999)), dict(start="2026-01-01T00:00:00"), dict(start="2026-01-01"),
    dict(start="2026-01-01T00:00:00.0000001Z"), dict(start="0001-01-01T00:00:00+01:00"),
    dict(end="9999-12-31T23:59:59-01:00"), dict(start=END), dict(start=END, end=START)])
def test_invalid_raw_record(changes):
    """Invalid values, sources, units and temporal evidence are rejected before writes."""
    with pytest.raises(MeasurementError): normalize(record(**changes))


@pytest.mark.parametrize("value", ["0", "-0.00000000000000000000000", "0e100000", "0.000000001"])
def test_zero_and_tiny_values(value):
    """Zero is valid and positive subpixel values stay positive without scale coercion."""
    assert normalize(record(value=value)).energy_kwh == Decimal(value)


def test_minuscule_wh_and_temporal_precision():
    """A microWh input stays positive; exact extra timestamp zeros are representable microseconds."""
    result = normalize(record(value="0.000001", unit="Wh", start="2026-01-01T00:00:00.000001000Z"))
    assert result.energy_kwh == Decimal("0.000000001")
    assert result.start.microsecond == 1


def test_global_revision_and_own_source_boundaries():
    """Only changes inside [start,end) to this category reject; global audit changes are permitted."""
    first = revision()
    mid = instant("2026-01-01T00:30:00Z")
    unrelated = revision(installation(**{"3": UUID(int=30)}), first, mid)
    assert normalize(record(), (first, unrelated)).category_revision == 1
    assert normalize(record(), (first, unrelated)).configuration_revision == 1
    own = revision(installation(**{"5": UUID(int=50)}), first, mid)
    with pytest.raises(MeasurementError, match="source_configuration_changed"): normalize(record(), (first, own))
    at_end = revision(installation(**{"5": UUID(int=50)}), first, END)
    assert normalize(record(), (first, at_end)).category_revision == 1
    at_start = revision(installation(**{"5": UUID(int=50)}), first, START)
    result = normalize(record(source_id=UUID(int=50)), (first, at_start))
    assert result.category_revision == 2 and result.configuration_revision == 2


def test_absent_source_or_unconfigured_gap():
    """No installed meter or missing temporal configuration cannot be interpreted as a real reading."""
    with pytest.raises(MeasurementError): normalize(record(), (revision(installation(())),))
    later = revision(at=instant("2026-01-01T00:15:00Z"))
    with pytest.raises(MeasurementError): normalize(record(), (later,))
