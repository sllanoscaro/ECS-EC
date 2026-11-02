"""Exact002 grouped states are independent dimensions; displayed percentage cannot establish completeness."""
from types import SimpleNamespace
from uuid import UUID

from ecs_ec.consumption.aggregates import project_block
from ecs_ec.consumption.calendar import containing_block
from ecs_ec.consumption.models import instant


def test_one_microsecond_missing_and_large_exact_sum():
    """A rounded100 percent with one missing microsecond remains incomplete, including huge exact energy."""
    block = containing_block(instant('2026-01-01T00:00:00Z'), 'hour', 'UTC')
    row = SimpleNamespace(id=UUID(int=1), revision=1, energy_quanta=10**70 + 1,
        covered_duration_us=3599999999, contribution_count=1,
        created_at=block.start, last_new_data_at=block.start, retain_until=instant('2027-01-01T00:00:00Z'))
    result = project_block(block, row, (), block.end)
    assert result.coverage_state == 'incomplete' and result.coverage_percent == '100'
    assert result.energy_kwh == '10000000000000000000000000000000000000000000000000000000.000000000000001'
    assert result.temporal_state == 'finished'


def test_future_start_end_are_exact_and_empty_is_null():
    """Empty projection never fabricates identity, energy or storage dates and retains the requested block."""
    from datetime import timedelta
    block = containing_block(instant('2026-01-01T00:00:00Z'), 'hour', 'UTC')
    for cutoff, state in ((block.start - timedelta(microseconds=1), 'not_started'), (block.start, 'ongoing'), (block.end, 'finished')):
        result = project_block(block, None, (), cutoff)
        assert result.temporal_state == state and result.coverage_state == 'no_data'
        assert result.energy_kwh is None and result.duration_us == '3600000000'
        assert result.aggregate_id is None and result.retain_until is None
