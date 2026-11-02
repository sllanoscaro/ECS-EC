"""Known calendar/DST cases, including leap years, folds and nonexistent wall times."""

from datetime import UTC, datetime

import pytest

from ecs_ec.core.retention import anniversary


@pytest.mark.parametrize(("instant", "zone", "expected"), [
    (datetime(2024, 2, 29, 12, tzinfo=UTC), "UTC", datetime(2025, 2, 28, 12, tzinfo=UTC)),
    (datetime(2023, 3, 1, tzinfo=UTC), "UTC", datetime(2024, 3, 1, tzinfo=UTC)),
    # NY 02:30 does not exist on 2025-03-09: move to 03:00, not 03:30.
    (datetime(2024, 3, 9, 7, 30, tzinfo=UTC), "America/New_York", datetime(2025, 3, 9, 7, tzinfo=UTC)),
    # NY 01:30 repeats on 2025-11-02: retain until the second occurrence.
    (datetime(2024, 11, 2, 5, 30, tzinfo=UTC), "America/New_York", datetime(2025, 11, 2, 6, 30, tzinfo=UTC)),
    (datetime(2025, 5, 1, 12, tzinfo=UTC), "America/Santiago", datetime(2026, 5, 1, 12, tzinfo=UTC)),
    # Samoa skipped 2011-12-30 completely; retain through the first valid instant.
    (datetime(2010, 12, 30, 22, tzinfo=UTC), "Pacific/Apia", datetime(2011, 12, 30, 10, tzinfo=UTC)),
])
def test_calendar_anniversary(instant, zone, expected):
    """Compare twelve local calendar months with independently specified UTC expectations."""
    assert anniversary(instant, zone) == expected


def test_reject_naive_instant():
    """A missing timezone must fail instead of assuming the machine timezone."""
    with pytest.raises(ValueError):
        anniversary(datetime(2024, 1, 1), "UTC")
