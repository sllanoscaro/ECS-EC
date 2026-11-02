"""Consumption-owned functional summaries use durable category results and explicit history bounds."""
from uuid import UUID

import pytest

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import instant
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_summary_observed_results_and_pre_registration_gap(history_environment, database, clock):
    """One completed category counts once; earlier history is a known gap and reads do not publish."""
    await publish(history_environment, [record()])
    from ecs_ec.consumption.queries import FunctionalSummary
    service = FunctionalSummary(facade(database, clock))
    clock.advance(1)
    async with UnitOfWork(database.sessions) as uow:
        result = await service.read(('reception.completed',),
            instant('2025-12-31T23:00:00Z'), clock.now(), cutoff_at=clock.now(),
            permissions={'consumption.read'}, unit_of_work=uow)
    assert result[0]['count'] == 1
    assert result[0]['integrity'] == 'incompleta'
    assert result[0]['known_gaps']
    assert len(result[0]['source_refs']) == 1


async def test_summary_zero_is_complete_only_with_registration(history_environment, database, clock):
    """Known empty history after registration differs from an unsupported content or unauthorized read."""
    from ecs_ec.consumption.queries import FunctionalSummary
    service = FunctionalSummary(facade(database, clock))
    start = clock.now()
    clock.advance(60)
    async with UnitOfWork(database.sessions) as uow:
        result = await service.read(('reception.completed', 'foreign.content'), start,
            clock.now(), cutoff_at=clock.now(), permissions={'consumption.read'}, unit_of_work=uow)
        assert result[0]['count'] == 0 and result[0]['integrity'] == 'completa'
        assert result[1]['count'] is None and result[1]['integrity'] == 'desconocida'
        with pytest.raises(PermissionError):
            await service.read(('reception.completed',), start, clock.now(),
                cutoff_at=clock.now(), permissions=set(), unit_of_work=uow)
