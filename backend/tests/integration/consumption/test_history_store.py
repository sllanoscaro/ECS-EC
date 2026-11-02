"""002 providers share captures, exact values and permanent history without read-side writes."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select, text

from ecs_ec.consumption.aggregates import quanta_energy
from ecs_ec.consumption.catalog_storage import lock_configuration
from ecs_ec.consumption.models import ConsumptionAggregate, IncorporatedRecord, instant
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import BUILDING, publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def test_initial_empty_states_and_bounds(history_environment, database, clock):
    """Seven empty states have true nulls and no fabricated acceptance/history/extent."""
    store = MeasurementStore()
    async with UnitOfWork(database.sessions) as uow:
        await lock_configuration(uow, BUILDING)
        bounds = await store.read_reconfiguration_bounds(BUILDING, ('CAT-01', 'CAT-05'), uow)
        assert not bounds.has_accepted_history and bounds.latest_interval_end_by_category == {'CAT-01': None, 'CAT-05': None}
        extent = await store.read_extent(BUILDING, clock.now(), uow)
        assert extent.start is None and extent.end is None
        for i in range(1, 8):
            state = await store.read_update_state(BUILDING, f'CAT-{i:02}', clock.now(), uow)
            assert state.last_new_data_at is state.next_admissible_at is state.latest_interval_end is None


async def test_global_extent_crossings_and_capture_without_writes(history_environment, database, clock):
    """Two categories share global extent; contained detail and crossings are separate and reads do not extend deadlines."""
    await publish(history_environment, [record(), record(category_id='CAT-03', source_id=UUID(int=3),
        start='2024-02-29T00:00:00Z', end='2024-02-29T01:00:00Z')])
    store = MeasurementStore()
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        extent = await store.read_extent(BUILDING, clock.now(), uow)
        assert extent.start == instant('2024-02-29T00:00:00Z') and extent.end == instant('2026-01-01T01:00:00Z')
        detail = await store.read_detail(BUILDING, 'CAT-05', instant('2026-01-01T00:30:00Z'), extent.end, clock.now(), uow)
        assert not detail.rows and len(detail.crossing_record_ids) == 1
        assert not uow.session.new and not uow.session.dirty
    async with UnitOfWork(database.sessions) as uow:
        await lock_configuration(uow, BUILDING)
        bounds = await store.read_reconfiguration_bounds(BUILDING, ('CAT-01', 'CAT-05'), uow)
        assert bounds.has_accepted_history and bounds.latest_interval_end_by_category['CAT-01'] is None
        assert bounds.latest_interval_end_by_category['CAT-05'] == extent.end


async def test_exact_extremes_and_synchronous_four_level_aggregates(history_environment, database, clock):
    """Physical max/q/zero survive numeric persistence and sum without the ambient Decimal precision."""
    maximum = '999999999999999999999999999999.999999999999999'
    await publish(history_environment, [record(value=maximum, start='2025-01-02T03:00:00Z', end='2025-01-02T03:15:00Z'),
        record(value='0.000000000000001', start='2025-01-02T03:15:00Z', end='2025-01-02T03:30:00Z'),
        record(value='0', start='2025-01-02T03:30:00Z', end='2025-01-02T03:45:00Z')])
    async with UnitOfWork(database.sessions) as uow:
        aggregates = (await uow.session.scalars(select(ConsumptionAggregate))).all()
        assert {a.granularity for a in aggregates} == {'hour', 'day', 'month', 'year'}
        for aggregate in aggregates:
            assert int(aggregate.energy_quanta) == 10**45
            assert quanta_energy(int(aggregate.energy_quanta)) == Decimal('1000000000000000000000000000000')
            assert aggregate.covered_duration_us == 2700000000
            assert aggregate.contribution_count == 3
            assert aggregate.retain_until == clock.now().replace(year=2027)
        retained = (await uow.session.scalars(select(IncorporatedRecord).order_by(IncorporatedRecord.start))).all()
        assert retained[0].energy_kwh == Decimal(maximum) and retained[1].energy_kwh == Decimal('0.000000000000001')


async def test_crossing_hour_does_not_discard_wider_levels(history_environment, database):
    """A measurement crossing a local hour can contribute once to day/month/year without proration."""
    await publish(history_environment, [record(start='2025-01-02T03:30:00Z', end='2025-01-02T04:30:00Z', value='2')])
    async with UnitOfWork(database.sessions) as uow:
        rows = (await uow.session.scalars(select(ConsumptionAggregate))).all()
        assert {a.granularity for a in rows} == {'day', 'month', 'year'}
        assert all(a.covered_duration_us == 3600000000 and int(a.energy_quanta) == 2 * 10**15 for a in rows)


async def test_real_fixture_spans_thirteen_months_seven_categories(history_environment, database, clock, thirteen_month_records):
    """Load91 original readings exclusively through Reception; no complete coverage is inferred from sparse months."""
    result = await publish(history_environment, thirteen_month_records)
    assert len(result.results) == 91 and all(r.status == 'accepted' for r in result.results)
    async with UnitOfWork(database.sessions) as uow:
        extent = await MeasurementStore().read_extent(BUILDING, clock.now(), uow)
        assert extent.start == instant('2024-01-01T03:00:00Z') and extent.end == instant('2025-01-01T04:00:00Z')
        for i in range(1, 8):
            detail = await MeasurementStore().read_detail(BUILDING, f'CAT-{i:02}', extent.start, extent.end, clock.now(), uow)
            assert len(detail.rows) == 13 and all(r.energy_kwh == i for r in detail.rows)
            assert all(r.first_incorporated_at == clock.now() for r in detail.rows)


async def test_retention_is_initialized_from_acceptance_and_only_new_data_extends_aggregates(history_environment, database, clock):
    """Initial minima reuse009's leap anniversary; re-sends preserve dates and late novelties extend aggregates."""
    clock.instant = instant('2028-02-29T12:00:00Z')
    first = record(start='2025-01-02T03:00:00Z', end='2025-01-02T03:15:00Z')
    await publish(history_environment, [first])
    async with UnitOfWork(database.sessions) as uow:
        original = (await uow.session.scalars(select(IncorporatedRecord))).one()
        identifier, deadline = original.id, original.retain_until
        assert deadline == instant('2029-02-28T12:00:00Z')
    clock.advance(900)
    await publish(history_environment, [first])
    async with UnitOfWork(database.sessions) as uow:
        assert all(a.retain_until == deadline and a.revision == 1 for a in (await uow.session.scalars(select(ConsumptionAggregate))).all())
    clock.advance(86400)
    await publish(history_environment, [record(start='2025-01-02T03:15:00Z', end='2025-01-02T03:30:00Z')])
    async with UnitOfWork(database.sessions) as uow:
        assert (await uow.session.get(IncorporatedRecord, identifier)).retain_until == deadline
        assert all(a.retain_until > deadline and a.revision == 2 for a in (await uow.session.scalars(select(ConsumptionAggregate))).all())


async def test_incompatible_calendar_identity_requires_reconciliation(history_environment, database, clock):
    """A synthetic stored older calendar boundary cannot silently become a new overlapping bucket."""
    await publish(history_environment, [record(start='2025-01-02T03:00:00Z', end='2025-01-02T03:15:00Z')])
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(text("UPDATE consumption_aggregate SET start=start-interval '30 minutes',tzdata_version='synthetic-old' WHERE granularity='hour'"))
        await uow.commit()
    clock.advance(900)
    with pytest.raises(ValueError, match='tzdata_reconciliation_required'):
        await publish(history_environment, [record(start='2025-01-02T03:30:00Z', end='2025-01-02T03:45:00Z')])
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(IncorporatedRecord)) == 1
        assert all(a.revision == 1 for a in (await uow.session.scalars(select(ConsumptionAggregate))).all())
