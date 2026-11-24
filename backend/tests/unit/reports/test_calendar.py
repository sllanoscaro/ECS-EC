"""005 calendar selections follow actual building-zone boundaries and reject future/alien fields."""

from datetime import UTC, datetime
import pytest
from pydantic import ValidationError
from ecs_ec.reports.schemas import Selection
from ecs_ec.reports.calendar import window


def test_day_dst_and_leap_month():
    """A New York repeated-hour day is25h; leap February spans29 complete local days."""
    start, end = window(
        Selection(scale="diario", date="2026-11-01"),
        "America/New_York",
        datetime(2026, 11, 2, tzinfo=UTC),
    )
    assert (end - start).total_seconds() == 25 * 3600
    start, end = window(
        Selection(scale="mensual", year=2024, month=2),
        "Etc/UTC",
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert (end - start).days == 29


@pytest.mark.parametrize(
    "body",
    [
        {"scale": "diario", "date": "2026-02-30"},
        {"scale": "anual", "year": 2026, "month": 1},
        {"scale": "mensual", "year": 2026},
        {"scale": "mensual", "year": 2026, "month": 13},
    ],
)
def test_invalid_selection(body):
    """Impossible dates and nonapplicable fields reject rather than being silently normalized."""
    with pytest.raises(ValidationError):
        Selection(**body)


def test_future_and_current_period():
    """Current-year selection retains its full window; a completely future year is inadmissible."""
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert window(Selection(scale="anual", year=2026), "Etc/UTC", now)[1] == datetime(
        2027, 1, 1, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="future_period"):
        window(Selection(scale="anual", year=2027), "Etc/UTC", now)
