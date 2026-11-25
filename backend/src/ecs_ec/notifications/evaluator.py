"""Urgent selection consumes the real001/002 admissible window and compares exact finite Decimal values."""

from decimal import Decimal, InvalidOperation


def compare_window(condition, window):
    """Missing/incomplete evidence never becomes zero or a normalizing evaluation."""
    if window.status != "available":
        return "no_evaluable"
    if (
        condition["window"]["kind"] == "intervalo"
        and int(window.duration_us)
        != condition["window"]["measurement_interval_seconds"] * 1000000
    ):
        return "no_evaluable"
    if window.duration_us != window.covered_duration_us:
        return "no_evaluable"
    try:
        if not isinstance(window.energy_kwh, str) or not isinstance(
            condition["threshold_kwh"], str
        ):
            return "no_evaluable"
        value, threshold = (
            Decimal(window.energy_kwh),
            Decimal(condition["threshold_kwh"]),
        )
        if (
            not value.is_finite()
            or not threshold.is_finite()
            or min(value, threshold) < 0
        ):
            return "no_evaluable"
    except InvalidOperation, ValueError, TypeError:
        return "no_evaluable"
    passed = {
        "gt": lambda: value > threshold,
        "gte": lambda: value >= threshold,
        "lt": lambda: value < threshold,
        "lte": lambda: value <= threshold,
    }[condition["comparison"]]()
    return "cumple" if passed else "no_cumple"
