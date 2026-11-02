"""Read exact persisted002 calendar aggregates through001's concrete facade."""
from uuid import UUID

import pytest

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import instant
from ecs_ec.consumption.ports import AggregateSelection

pytestmark = pytest.mark.integration


def selection(category='CAT-05', granularity='hour', start='2026-01-01T00:00:00Z', end='2026-01-01T02:00:00Z'):
    """Internal selections use UTC identities and the explicit synthetic building zone."""
    return AggregateSelection(building_id=UUID(int=99), category_id=category, granularity=granularity,
        start=start, end=end, timezone='America/Santiago')


@pytest.mark.parametrize('late_value,expected', [('0','3'), ('1','4')])
async def test_three_quarters_zero_empty_and_late_commit(history_environment, database, clock, late_value, expected):
    """Known75% becomes100% only after permitted late incorporation; duplicate does not revise."""
    rows = [record(value='1', start=f'2026-01-01T00:{m:02}:00Z', end=f'2026-01-01T00:{m+15:02}:00Z') for m in (0, 15, 30)]
    await publish(history_environment, rows)
    service = facade(database, clock)
    result = await service.query_aggregates(selection(), None)
    first, empty = result.blocks
    assert (first.energy_kwh, first.coverage_percent, first.coverage_state) == ('3', '75', 'incomplete')
    assert empty.energy_kwh is None and empty.covered_duration_us == '0'
    clock.advance(900)
    late = record(value=late_value, start='2026-01-01T00:45:00Z', end='2026-01-01T01:00:00Z')
    await publish(history_environment, [late])
    updated = (await service.query_aggregates(selection(), None)).blocks[0]
    assert updated.energy_kwh == expected and updated.coverage_state == 'complete'
    assert updated.revision > first.revision
    await publish(history_environment, [late])
    assert (await service.query_aggregates(selection(), None)).blocks[0] == updated


@pytest.mark.parametrize('granularity,start,end', [
    ('hour','2026-01-01T00:00:00Z','2026-01-01T01:00:00Z'),
    ('day','2025-12-31T03:00:00Z','2026-01-01T03:00:00Z'),
    ('month','2025-12-01T03:00:00Z','2026-01-01T03:00:00Z'),
    ('year','2025-01-01T03:00:00Z','2026-01-01T03:00:00Z')])
async def test_seven_categories_four_levels(history_environment, database, clock, granularity, start, end):
    """Seven physical series sum their own originals once at every calendar level."""
    await publish(history_environment, [record(category_id=f'CAT-{i:02}', source_id=UUID(int=i), value=str(i)) for i in range(1,8)])
    service = facade(database, clock)
    for i in range(1,8):
        result = await service.query_aggregates(selection(f'CAT-{i:02}', granularity, start, end), None)
        assert len(result.blocks) == 1
        assert result.blocks[0].energy_kwh == str(i)


async def test_crossing_and_partial_filter(history_environment, database, clock):
    """A crossing survives detail/day, but cannot contribute to either hour; edges stay unclipped."""
    await publish(history_environment, [record(start='2026-01-01T00:30:00Z', end='2026-01-01T01:30:00Z', value='4')])
    service = facade(database, clock)
    result = await service.query_aggregates(selection(), None)
    assert all(b.energy_kwh is None for b in result.blocks)
    assert any(w.code == 'measurement_crosses_block' for w in result.warnings)
    day = await service.query_aggregates(selection(granularity='day', start='2025-12-31T03:00:00Z', end='2026-01-01T03:00:00Z'), None)
    assert day.blocks[0].energy_kwh == '4'
    excluded = await service.query_aggregates(selection(start='2026-01-01T00:15:00Z', end='2026-01-01T00:45:00Z'), None)
    assert excluded.blocks == () and len(excluded.excluded_blocks) == 1
    assert excluded.excluded_blocks[0].reason_code == 'filter_both'


async def test_future_and_cutoff_boundaries(history_environment, database, clock):
    """Coverage is independent of not_started/ongoing/finished and one captured clock is used."""
    service = facade(database, clock)
    chosen = selection(start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')
    for advance, state in ((0, 'not_started'), (3600, 'ongoing'), (3600, 'finished')):
        clock.advance(advance)
        result = await service.query_aggregates(chosen, None)
        assert result.period.start == chosen.start
        assert result.blocks[0].temporal_state == state
        assert result.blocks[0].energy_kwh is None


async def test_calculated_total_uses_own_incorporated_series(consumption_reception_environment, database, clock):
    """Calculated20+30=50 is not summed with its physical partials a second time."""
    await consumption_reception_environment.publish([
        record(value='12'), record(category_id='CAT-03', source_id=UUID(int=3), value='8'),
        record(value='18', start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z'),
        record(category_id='CAT-03', source_id=UUID(int=3), value='12', start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')])
    result = await facade(database, clock).query_aggregates(selection('CAT-01', 'day', '2025-12-31T03:00:00Z', '2026-01-01T03:00:00Z'), None)
    assert result.blocks[0].energy_kwh == '50'
    assert result.blocks[0].source_mode == 'mixed'
    assert result.blocks[0].provenance_segments[-1].source_mode == 'calculated'
    assert any(w.code == 'partial_calculation_basis' for w in result.warnings)


async def test_repeated_hours_and_leap_calendar(history_environment, database, clock):
    """Real projected buckets preserve both offsets and the independent29-day February duration."""
    from ecs_ec.consumption.configuration import ConfigurationService
    from ecs_ec.consumption.store import MeasurementStore
    from ecs_ec.core.unit_of_work import UnitOfWork
    from backend.tests.unit.consumption.test_catalog import installation
    async with UnitOfWork(database.sessions) as uow:
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=UUID(int=99),
            request=installation(tuple(range(1,8))).model_copy(update={'expected_revision': 1, 'effective_from': None, 'timezone': 'America/New_York'}),
            actor_ref='process:history_test')
        await uow.commit()
    await publish(history_environment, [record(start='2026-11-01T05:00:00Z', end='2026-11-01T06:00:00Z', value='1'),
        record(start='2026-11-01T06:00:00Z', end='2026-11-01T07:00:00Z', value='2')])
    chosen = selection(start='2026-11-01T04:00:00Z', end='2026-11-02T05:00:00Z').model_copy(update={'timezone': 'America/New_York'})
    result = await facade(database, clock).query_aggregates(chosen, None)
    assert len(result.blocks) == 25
    assert [b.energy_kwh for b in result.blocks[1:3]] == ['1', '2']
    leap = selection(granularity='month', start='2028-02-01T05:00:00Z', end='2028-03-01T05:00:00Z').model_copy(update={'timezone': 'America/New_York'})
    assert (await facade(database, clock).query_aggregates(leap, None)).blocks[0].duration_us == '2505600000000'


async def test_aggregate_can_exceed_individual_maximum_exactly(history_environment, database, clock):
    """Two admitted interval energies sum to10^30 exactly; aggregate limits do not inherit individual caps."""
    await publish(history_environment, [record(value='999999999999999999999999999999.999999999999999',
        start='2026-01-01T00:00:00Z',end='2026-01-01T00:30:00Z'),
        record(value='0.000000000000001',start='2026-01-01T00:30:00Z',end='2026-01-01T01:00:00Z')])
    block = (await facade(database, clock).query_aggregates(selection(), None)).blocks[0]
    assert block.energy_kwh == '1000000000000000000000000000000'
    assert block.coverage_state == 'complete' and block.contribution_count == 2
