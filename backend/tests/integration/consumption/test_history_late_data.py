"""Late originals after a permitted withdrawal extend aggregates once; old normalized identities stay permanent."""
from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.integration.consumption.test_aggregates import selection
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.consumption.retention import Retention
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_late_after_withdrawal_retains_old_contribution(history_environment, database, clock):
    """An old duplicate/conflict/overlap cannot sum again; a permitted new contiguous reading does."""
    original = record(value='1')
    await publish(history_environment, [original])
    async with UnitOfWork(database.sessions) as uow:
        row = await uow.session.scalar(select(IncorporatedRecord))
        identifier, deadline = row.id, row.retain_until
    clock.advance((deadline - clock.now()).total_seconds())
    await Retention(database, clock, authorized_processes={'process:test': {UUID(int=99)}}).withdraw_detail(
        building_id=UUID(int=99), record_ids=(identifier,), process='process:test', reason='expired_detail')
    result = await publish(history_environment, [original, record(value='9'),
        record(value='2', start='2026-01-01T00:30:00Z', end='2026-01-01T01:30:00Z'),
        record(value='3', start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')])
    assert [r.status for r in result.results] == ['duplicate','rejected','rejected','accepted']
    chosen = selection(granularity='day',start='2025-12-31T03:00:00Z',end='2026-01-01T03:00:00Z')
    block = (await facade(database, clock).query_aggregates(chosen, None)).blocks[0]
    assert block.energy_kwh == '4' and block.covered_duration_us == '7200000000'
    assert block.revision == 2 and block.retain_until > clock.now()
