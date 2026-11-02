"""900 elapsed UTC seconds apply to new category updates, never source interval length."""

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from ecs_ec.consumption.models import CategoryReceptionState, ConsumptionAggregate
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def test_all_seven_categories_899_900_and_independent_batches(history_environment, database, clock):
    """Seven categories share reception time but independent limits; historical batches count once."""
    rows = [record(category_id=f'CAT-{i:02}', source_id=UUID(int=i)) for i in range(1, 8)]
    first = await publish(history_environment, rows)
    assert all(r.status == 'accepted' for r in first.results)
    assert len(first.updates) == 7
    fresh = [r | dict(start='2025-01-01T00:00:00Z', end='2025-01-01T01:00:00Z') for r in rows]
    clock.advance(899)
    early = await publish(history_environment, fresh)
    assert all(r.reason_code == 'too_early' for r in early.results)
    clock.advance(1)
    allowed = await publish(history_environment, fresh + [fresh[0] | dict(start='2024-01-01T00:00:00Z', end='2024-01-01T01:00:00Z')])
    assert all(r.status == 'accepted' for r in allowed.results)
    async with UnitOfWork(database.sessions) as uow:
        states = (await uow.session.scalars(select(CategoryReceptionState))).all()
        assert len(states) == 7
        assert all(s.last_new_data_at == clock.now() and s.next_admissible_at == clock.now() + timedelta(seconds=900) for s in states)
        assert len((await uow.session.scalars(select(ConsumptionAggregate))).all()) >= 7 * 4


async def test_duplicates_invalid_clock_reversal_and_other_category(history_environment, clock):
    """No-op input preserves eligibility; source timestamps cannot bypass reversed platform time."""
    first = await publish(history_environment, [record()])
    next_at = first.updates[0].next_admissible_at
    clock.advance(899)
    mixed = await publish(history_environment, [record(), record(value='2'), record(value='NaN'),
        record(start='2025-01-01T00:00:00Z', end='2025-01-01T01:00:00Z'),
        record(category_id='CAT-03', source_id=UUID(int=3))])
    assert [r.status for r in mixed.results] == ['duplicate', 'rejected', 'rejected', 'rejected', 'accepted']
    assert mixed.results[1].reason_code == 'conflicting_duplicate'
    assert mixed.results[3].next_admissible_at == next_at
    clock.instant -= timedelta(seconds=1000)  # Simulate wall-clock regression while monotonic stays increasing.
    reversed_result = await publish(history_environment, [record(start='2024-01-01T00:00:00Z', end='2024-01-01T01:00:00Z')])
    assert reversed_result.results[0].reason_code == 'clock_regressed'
    clock.advance(1001)
    assert (await publish(history_environment, [record(start='2025-01-01T00:00:00Z', end='2025-01-01T01:00:00Z')])).results[0].status == 'accepted'
