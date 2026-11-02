"""Independent exact arithmetic/calendar expectations for002; no PostgreSQL doubles."""

from datetime import UTC, datetime
from decimal import Decimal, localcontext

import pytest

from ecs_ec.consumption.calendar import blocks, containing_block, duration_us
from ecs_ec.consumption.aggregates import energy_quanta, quanta_energy
from ecs_ec.consumption.models import instant
from ecs_ec.core.retention import anniversary


def test_quantum_and_unbounded_integer_sum():
    """Ambient precision cannot truncate q, six maxima or sums wider than50 digits."""
    with localcontext() as context:
        context.prec = 8
        assert energy_quanta(Decimal('0.000000000000001')) == 1
        value = Decimal('999999999999999999999999999999.999999999999999')
        coefficient = energy_quanta(value)
        assert coefficient == 10**45 - 1
        assert str(quanta_energy(coefficient * 10**12)) == '999999999999999999999999999999999999999999.999000000000000'
    for invalid in ('0.0000000000000001', '-1', 'NaN', 'Infinity'):
        with pytest.raises(ValueError): energy_quanta(Decimal(invalid))


def test_repeated_and_missing_hours():
    """New York autumn has25 real hours, spring23; repeated labels retain distinct offsets."""
    for day, count in (('2026-11-01', 25), ('2026-03-08', 23)):
        block = containing_block(instant(day + 'T12:00:00Z'), 'day', 'America/New_York')
        hours = blocks(block.start, block.end, 'hour', block.timezone)
        assert len(hours) == count
        assert sum(duration_us(b.start, b.end) for b in hours) == count * 3600 * 10**6
        assert hours[0].start == block.start and hours[-1].end == block.end
        assert all(a.end == b.start for a, b in zip(hours, hours[1:]))
    autumn = containing_block(instant('2026-11-01T12:00:00Z'), 'day', 'America/New_York')
    hours = blocks(autumn.start, autumn.end, 'hour', autumn.timezone)
    assert hours[1].start_offset != hours[2].start_offset


def test_noninteger_transition_leap_month_and_skipped_midnight():
    """Lord Howe preserves30-minute transition; Santiago midnight resolves to first valid instant."""
    day = containing_block(instant('2026-10-04T12:00:00Z'), 'day', 'Australia/Lord_Howe')
    hours = blocks(day.start, day.end, 'hour', day.timezone)
    assert sum(duration_us(b.start, b.end) for b in hours) == 84600 * 10**6
    assert any(duration_us(b.start, b.end) == 1800 * 10**6 for b in hours)
    month = containing_block(instant('2028-02-12T12:00:00Z'), 'month', 'UTC')
    assert duration_us(month.start, month.end) == 29 * 86400 * 10**6
    year = containing_block(month.start, 'year', 'UTC')
    assert duration_us(year.start, year.end) == 366 * 86400 * 10**6
    day = containing_block(instant('2026-09-06T12:00:00Z'), 'day', 'America/Santiago')
    assert day.start == instant('2026-09-06T04:00:00Z')
    assert duration_us(day.start, day.end) == 23 * 3600 * 10**6


def test_containment_microseconds_and_retention():
    """No partial block, float duration or365-day substitute is allowed."""
    start, end = instant('2026-01-01T00:00:00.000001Z'), instant('2026-01-01T02:00:00Z')
    result = blocks(start, end, 'hour', 'UTC')
    assert len(result) == 1 and result[0].start == instant('2026-01-01T01:00:00Z')
    assert duration_us(start, end) == 7199999999
    assert anniversary(datetime(2028, 2, 29, 12, tzinfo=UTC), 'UTC') == datetime(2029, 2, 28, 12, tzinfo=UTC)
