"""Durable requests without candidates protect originals needed for post-crashCAT-01 evaluation."""
from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import IncorporatedRecord, TotalEvaluationRequest
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_pending_request_without_candidate_blocks_withdrawal(consumption_reception_environment, database, clock, monkeypatch):
    """A crash before candidate creation leaves a durable request which maintenance must respect."""
    from ecs_ec.consumption.pending_totals import PendingTotals
    from ecs_ec.consumption.retention import Retention
    async def stop(*args, **kwargs):
        """Simulate process loss after the category transaction; recovery owns the persisted request."""
        raise RuntimeError('synthetic_crash')
    monkeypatch.setattr(PendingTotals, 'run_due', stop)
    try:
        await consumption_reception_environment.publish([record()])
    except RuntimeError:
        pass
    async with UnitOfWork(database.sessions) as uow:
        row = await uow.session.scalar(select(IncorporatedRecord))
        identifier, deadline = row.id, row.retain_until
        assert (await uow.session.scalar(select(TotalEvaluationRequest))).status == 'pending'
    clock.advance((deadline - clock.now()).total_seconds())
    retention = Retention(database, clock, authorized_processes={'process:retention_test': {UUID(int=99)}})
    result = await retention.withdraw_detail(building_id=UUID(int=99), record_ids=(identifier,),
        process='process:retention_test', reason='expired_detail', preview=True)
    assert result[0]['reason_code'] == 'protected_dependency'
    monkeypatch.undo()
    await consumption_reception_environment.publish([record(category_id='CAT-03', source_id=UUID(int=3), value='1')])
    async with UnitOfWork(database.sessions) as uow:
        total = await uow.session.scalar(select(IncorporatedRecord).where(IncorporatedRecord.category_id == 'CAT-01'))
        assert total is not None and total.energy_kwh == 2
        assert (await uow.session.get(IncorporatedRecord, identifier)).retain_until >= total.retain_until


async def test_calculated_total_extends_originals_to_its_minimum(consumption_reception_environment, database, clock):
    """Delayed incorporation ofCAT-01 protects earlier originals until the dependent's own anniversary."""
    from ecs_ec.consumption.retention import Retention
    from backend.tests.integration.consumption.test_detail_queries import facade
    await consumption_reception_environment.publish([record(value='12')])
    async with UnitOfWork(database.sessions) as uow:
        original = await uow.session.scalar(select(IncorporatedRecord))
        identifier, original_deadline = original.id, original.retain_until
    clock.advance(900)
    await consumption_reception_environment.publish([record(category_id='CAT-03', source_id=UUID(int=3), value='8')])
    async with UnitOfWork(database.sessions) as uow:
        original = await uow.session.get(IncorporatedRecord, identifier)
        total = await uow.session.scalar(select(IncorporatedRecord).where(IncorporatedRecord.category_id == 'CAT-01'))
        assert original.retain_until >= total.retain_until > original_deadline
    clock.advance((original_deadline - clock.now()).total_seconds())
    outcome = await Retention(database, clock, authorized_processes={'process:test': {UUID(int=99)}}).withdraw_detail(
        building_id=UUID(int=99), record_ids=(identifier,), process='process:test', reason='expired_detail')
    assert outcome[0]['reason_code'] == 'protected'
    result = await facade(database, clock).detail('CAT-01', '2025-12-31T21:00:00-03:00', '2025-12-31T22:00:00-03:00', 'America/Santiago')
    assert result.rows[0].energy_kwh == '20'
