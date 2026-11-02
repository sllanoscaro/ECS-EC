"""Calendar minima are from acceptance, remain queryable at deadline, and never depend on GET frequency."""
from datetime import timedelta
from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import IncorporatedRecord, instant
from ecs_ec.consumption.retention import retention_deadline
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('accepted,expected', [
    ('2028-02-29T12:00:00Z','2029-02-28T12:00:00Z'),
    ('2026-09-05T04:30:00Z','2027-09-05T04:00:00Z'),
    ('2026-04-04T02:30:00Z','2027-04-04T03:30:00Z')])
async def test_original_deadline_and_read_at_anniversary(history_environment, database, clock, accepted, expected):
    """Late historical measurements use acceptance; leap day, missing/repeated hour follow the009 helper."""
    clock.advance((instant(accepted) - clock.now()).total_seconds())
    await publish(history_environment, [record()])
    async with UnitOfWork(database.sessions) as uow:
        row = await uow.session.scalar(select(IncorporatedRecord))
        assert row.retain_until == instant(expected)
        identifier, deadline = row.id, row.retain_until
    for target in (deadline - timedelta(microseconds=1), deadline, deadline + timedelta(seconds=1)):
        clock.advance((target - clock.now()).total_seconds())
        result = await facade(database, clock).detail('CAT-05','2025-12-31T21:00:00-03:00','2025-12-31T22:00:00-03:00','America/Santiago')
        assert len(result.rows) == 1
    async with UnitOfWork(database.sessions) as uow:
        assert (await uow.session.get(IncorporatedRecord, identifier)).retain_until == deadline
    assert retention_deadline(instant(accepted), 'America/Santiago', deadline + timedelta(days=1)) == deadline + timedelta(days=1)


async def test_thirteen_months_seven_categories_at_minimum(history_environment, database, clock, thirteen_month_records):
    """Ninety-one late originals and their monthly/yearly aggregates remain readable before and at the minimum."""
    from ecs_ec.consumption.periods import timestamp
    from ecs_ec.consumption.ports import AggregateSelection
    # Midday UTC stays within its local calendar month across both seasonal offsets.
    rows = [r | {'start': r['start'].replace('T03:', 'T12:'), 'end': r['end'].replace('T04:', 'T13:')} for r in thirteen_month_records]
    await publish(history_environment, rows)
    service = facade(database, clock)
    start, end = instant('2024-01-01T03:00:00Z'), instant('2025-02-01T03:00:00Z')
    async with UnitOfWork(database.sessions) as uow:
        deadline = (await uow.session.scalar(select(IncorporatedRecord).limit(1))).retain_until
    for target in (deadline - timedelta(microseconds=1), deadline):
        clock.advance((target - clock.now()).total_seconds())
        for i in range(1,8):
            category = f'CAT-{i:02}'
            detail = await service.detail(category, timestamp(start, 'America/Santiago'), timestamp(end, 'America/Santiago'), 'America/Santiago')
            assert len(detail.rows) == 13 and all(r.energy_kwh == str(i) for r in detail.rows)
            grouped = await service.query_aggregates(AggregateSelection(building_id=UUID(int=99), category_id=category,
                start=start, end=end, timezone='America/Santiago', granularity='month'), None)
            assert len(grouped.blocks) == 13 and all(b.energy_kwh == str(i) for b in grouped.blocks)
            assert all(b.coverage_state == 'incomplete' for b in grouped.blocks)
