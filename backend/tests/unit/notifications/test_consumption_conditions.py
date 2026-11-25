"""Urgent consumption comparisons use exact Decimal and only complete admissible owner windows."""

from types import SimpleNamespace

import pytest
from ecs_ec.notifications.evaluator import compare_window


@pytest.mark.parametrize(
    ("comparison", "value", "expected"),
    [
        ("gt", "100", "no_cumple"),
        ("gt", "101", "cumple"),
        ("gt", "99", "no_cumple"),
        ("gte", "100", "cumple"),
        ("lt", "99", "cumple"),
        ("lt", "100", "no_cumple"),
        ("lte", "100", "cumple"),
        ("lte", "101", "no_cumple"),
        ("gt", "0", "no_cumple"),
        ("gte", "0", "cumple"),
    ],
)
def test_exact_four_comparisons_and_zero(comparison, value, expected):
    """Boundary100/101/99 and threshold0 never pass through a binary floating point conversion."""
    condition = dict(
        window=dict(kind="hora"),
        comparison=comparison,
        threshold_kwh="0" if value == "0" else "100",
    )
    window = SimpleNamespace(
        status="available",
        energy_kwh=value,
        duration_us="3600000000",
        covered_duration_us="3600000000",
    )
    assert compare_window(condition, window) == expected


@pytest.mark.parametrize("kind", ["intervalo", "hora", "dia", "mes", "anio"])
def test_missing_or_partial_window_is_not_evaluable(kind):
    """Unavailable evidence cannot be converted into a zero that closes a persistent episode."""
    condition = dict(
        window=dict(kind=kind, measurement_interval_seconds=900),
        comparison="gt",
        threshold_kwh="0",
    )
    assert (
        compare_window(
            condition, SimpleNamespace(status="not_evaluable", energy_kwh=None)
        )
        == "no_evaluable"
    )


def test_interval_requires_the_configured_resolution():
    """An otherwise complete owner interval cannot silently replace the configured measurement duration."""
    condition = dict(
        window=dict(kind="intervalo", measurement_interval_seconds=900),
        comparison="gt",
        threshold_kwh="1",
    )
    window = SimpleNamespace(
        status="available",
        energy_kwh="2",
        duration_us="1800000000",
        covered_duration_us="1800000000",
    )
    assert compare_window(condition, window) == "no_evaluable"
