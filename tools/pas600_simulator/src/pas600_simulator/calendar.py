"""Exact UTC calendar and rational quantum validation; never truncate a period."""
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def interval_count(start: datetime, end: datetime, timezone: str, minutes: int) -> int:
    """Return complete UTC intervals; raise ValueError for naive/inconsistent bounds."""
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("unknown IANA timezone") from exc
    if isinstance(minutes, bool) or minutes <= 0:
        raise ValueError('sampling_minutes must be positive')
    for value in (start, end):
        if value.utcoffset() is None or value.utcoffset() != value.astimezone(zone).utcoffset():
            raise ValueError('explicit offset must agree with timezone')
    delta = end.astimezone(UTC) - start.astimezone(UTC)
    microseconds = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    step = minutes * 60 * 1000000
    if microseconds <= 0 or microseconds % step:
        raise ValueError('period must contain a positive whole number of samples')
    return microseconds // step


def quantum_bounds(low: Decimal, high: Decimal, quantum: Decimal) -> tuple[int, int]:
    """Return inclusive integer quantum indices using exact rational arithmetic."""
    if not all(v.is_finite() for v in (low, high, quantum)) or low < 0 or high < low or quantum <= 0:
        raise ValueError('invalid finite range or quantum')
    lower, upper = Fraction(low) / Fraction(quantum), Fraction(high) / Fraction(quantum)
    first = -(-lower.numerator // lower.denominator)
    last = upper.numerator // upper.denominator
    if first > last:
        raise ValueError('range has no representable value')
    return first, last


def representable(value: Decimal, quantum: Decimal) -> bool:
    """Test a finite value on a positive quantum grid without decimal rounding."""
    return value.is_finite() and quantum.is_finite() and quantum > 0 and (Fraction(value) / Fraction(quantum)).denominator == 1
