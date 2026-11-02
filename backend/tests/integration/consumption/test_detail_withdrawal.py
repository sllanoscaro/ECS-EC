"""Real maintenance withdrawal preserves ledger, exact aggregates and permanent001 configuration bounds."""
from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.integration.consumption.test_aggregates import selection
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import AcceptedMeasurement, IncorporatedRecord, instant
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_protected_then_expired_withdrawal_and_resend(history_environment, database, clock):
    """Withdrawing a permitted original does not reduce a protected day or reactivate a duplicate payload."""
    from ecs_ec.consumption.retention import Retention
    await publish(history_environment, [record(value='1')])
    async with UnitOfWork(database.sessions) as uow:
        original = await uow.session.scalar(select(IncorporatedRecord))
        identifier, deadline = original.id, original.retain_until
    retention = Retention(database, clock, authorized_processes={'process:retention_test': {UUID(int=99)}})
    args = dict(building_id=UUID(int=99), record_ids=(identifier,), process='process:retention_test', reason='expired_detail')
    assert (await retention.withdraw_detail(**args, preview=True))[0]['reason_code'] == 'protected'
    with pytest.raises(PermissionError):
        await retention.withdraw_detail(**(args | {'process': 'untrusted'}))
    clock.advance((instant('2026-12-31T00:00:00Z') - clock.now()).total_seconds())
    await publish(history_environment, [record(value='2', start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')])
    chosen = selection(granularity='day', start='2025-12-31T03:00:00Z', end='2026-01-01T03:00:00Z')
    service = facade(database, clock)
    before = (await service.query_aggregates(chosen, None)).blocks[0]
    clock.advance((deadline - clock.now()).total_seconds())
    outcome = await retention.withdraw_detail(**args)
    assert outcome[0]['status'] == 'withdrawn'
    after = (await service.query_aggregates(chosen, None)).blocks[0]
    assert (after.energy_kwh, after.covered_duration_us, after.revision, after.retain_until) == (before.energy_kwh, before.covered_duration_us, before.revision, before.retain_until)
    duplicate = await publish(history_environment, [record(value='1')])
    assert duplicate.results[0].status == 'duplicate'
    conflict = await publish(history_environment, [record(value='9')])
    assert conflict.results[0].reason_code == 'conflicting_duplicate'
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.get(AcceptedMeasurement, identifier) is None
        assert (await uow.session.get(IncorporatedRecord, identifier)).detail_state == 'withdrawn'
    detail = await service.detail('CAT-05', '2025-12-31T21:00:00-03:00', '2025-12-31T23:00:00-03:00', 'America/Santiago')
    assert len(detail.rows) == 1
    assert any(w.code == 'detail_withdrawn' for w in detail.warnings)

    from ecs_ec.consumption.store import lock_history, MeasurementStore
    async with UnitOfWork(database.sessions) as uow:
        await lock_history(uow, UUID(int=99))
        bounds = await MeasurementStore().read_reconfiguration_bounds(UUID(int=99), ('CAT-05',), uow)
        assert bounds.has_accepted_history
        assert bounds.latest_interval_end_by_category == {'CAT-05': instant('2026-01-01T02:00:00Z')}
