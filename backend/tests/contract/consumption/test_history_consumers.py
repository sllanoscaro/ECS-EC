"""Producer-only consumer contracts; real002 evidence never substitutes calculatedCAT-01 for supply."""
from uuid import UUID
import pytest
from sqlalchemy import func, select, text
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import ConsumptionAggregate, instant
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_latest_complete_projection_cursor_and_no_writes(history_environment, database, clock):
    """Another zone projects original intervals; invalid selection cursors fail and GET creates no buckets."""
    await publish(history_environment, [record(value='2')])
    clock.advance(7200)
    service = facade(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        before = await uow.session.scalar(select(func.count()).select_from(ConsumptionAggregate))
        args = dict(building_id=UUID(int=99), category_id='CAT-05', resolution='hour', timezone='UTC',
            activation_at=instant('2025-01-01T00:00:00Z'), cutoff_at=clock.now(), cursor=None, unit_of_work=uow)
        result = await service.latest_admissible_window(**args)
        assert result.status == 'available' and result.energy_kwh == '2'
        assert result.period.end == instant('2026-01-01T01:00:00Z')
        repeated = await service.latest_admissible_window(**(args | {'cursor': result.cursor}))
        assert repeated.evidence_revision == result.evidence_revision
        with pytest.raises(ValueError, match='invalid_cursor'):
            await service.latest_admissible_window(**(args | {'category_id': 'CAT-03', 'cursor': result.cursor}))
        assert await uow.session.scalar(select(func.count()).select_from(ConsumptionAggregate)) == before


async def test_general_and_demand_resolution(history_environment, database, clock):
    """Hourly physical energy is useful for general snapshot but proves no15-minute demand resolution."""
    await publish(history_environment, [record(category_id='CAT-01', source_id=UUID(int=1), value='100')])
    service = facade(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        args = (UUID(int=99), instant('2026-01-01T00:00:00Z'), instant('2026-01-01T01:00:00Z'), clock.now(), uow)
        general = await service.read_general_snapshot(*args)
        assert general.reason_code is None and general.rows[0].energy_kwh == 100
        demand = await service.read_demand_history(*args)
        assert demand.reason_code == 'insufficient_resolution'


async def test_calculated_general_is_explicit_limitation(consumption_reception_environment, database, clock):
    """The supplier boundary never treats a computed total as a physical meter."""
    await consumption_reception_environment.publish([record(value='12'), record(category_id='CAT-03', source_id=UUID(int=3), value='8')])
    service = facade(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        result = await service.read_general_snapshot(UUID(int=99), instant('2026-01-01T00:00:00Z'),
            instant('2026-01-01T01:00:00Z'), clock.now(), uow)
        assert result.reason_code == 'calculated_general' and result.rows == ()
        report = await service.read_report_snapshot(UUID(int=99), instant('2026-01-01T00:00:00Z'),
            instant('2026-01-01T01:00:00Z'), 'hour', clock.now(), None, unit_of_work=uow)
        assert len(report['categories']) == 7
        assert report['categories'][0]['aggregates'].blocks[0].energy_kwh == '20'


async def test_window_revision_moves_only_after_late_completion(history_environment, database, clock):
    """A newer incomplete hour does not displace a complete window; a committed late quarter makes it eligible."""
    await publish(history_environment, [record(value='2'),
        record(value='1',start='2026-01-01T01:00:00Z',end='2026-01-01T01:45:00Z')])
    clock.advance(7200)
    service = facade(database, clock)
    async def read(cursor=None):
        """Each external consumer evaluation opens a fresh coherent read capture."""
        async with UnitOfWork(database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            return await service.latest_admissible_window(building_id=UUID(int=99), category_id='CAT-05',
                resolution='hour', timezone='UTC', activation_at=instant('2025-01-01T00:00:00Z'),
                cutoff_at=clock.now(), cursor=cursor, unit_of_work=uow)
    first = await read()
    assert first.period.end == instant('2026-01-01T01:00:00Z')
    await publish(history_environment, [record(value='3',start='2026-01-01T01:45:00Z',end='2026-01-01T02:00:00Z')])
    newer = await read(first.cursor)
    assert newer.period.end == instant('2026-01-01T02:00:00Z') and newer.energy_kwh == '4'
    assert newer.evidence_revision != first.evidence_revision
    assert (await read(newer.cursor)).evidence_revision == newer.evidence_revision
