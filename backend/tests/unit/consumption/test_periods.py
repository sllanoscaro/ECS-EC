"""Query periods use explicit IANA offsets and preserve representable microseconds."""

import pytest

from ecs_ec.consumption.periods import local_day, resolve_period
from ecs_ec.consumption.models import instant


def test_repeated_hour_and_microseconds():
    """Two offsets of a repeated Santiago hour identify distinct real instants."""
    value = resolve_period('2026-04-04T23:30:00.000001-03:00', '2026-04-04T23:30:00.000002-04:00',
        'America/Santiago', 'America/Santiago')
    assert (value.end - value.start).total_seconds() == 3600.000001


@pytest.mark.parametrize('start,end,zone', [
    ('2026-09-06T00:30:00-04:00', '2026-09-06T02:00:00-03:00', 'America/Santiago'),
    ('2026-01-01T00:00:00-04:00', '2026-01-02T00:00:00-03:00', 'America/Santiago'),
    ('2026-01-01T00:00:00', '2026-01-02T00:00:00-03:00', 'America/Santiago'),
    ('2026-01-01T00:00:00-03:00', '2026-01-01T00:00:00-03:00', 'America/Santiago'),
    ('2026-01-01T00:00:00.0000001-03:00', '2026-01-02T00:00:00-03:00', 'America/Santiago'),
    ('2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z', 'UTC'),
])
def test_invalid_period(start, end, zone):
    """Absent/wrong offsets, empty ranges, foreign zones and unrepresentable precision all fail closed."""
    with pytest.raises(ValueError):
        resolve_period(start, end, zone, 'America/Santiago')


def test_empty_history_uses_local_day():
    """A UTC instant belongs to the prior local date when Santiago is behind UTC."""
    period = local_day(instant('2026-01-01T01:00:00Z'), 'America/Santiago')
    assert period.start == instant('2025-12-31T03:00:00Z')
    assert period.end == instant('2026-01-01T03:00:00Z')
