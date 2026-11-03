"""Containment and diagnostic crossings use real002 records and never prorate."""

import pytest
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('category', ['CAT-05', 'CAT-01'])
async def test_crossing_rows_and_diagnostics(consumption_reception_environment, database, clock, category):
    """An interval crossing both boundaries counts once; the same holds for an incomplete candidate."""
    env = consumption_reception_environment
    await env.publish([record()])
    service = facade(database, clock)
    result = await service.detail(category, '2025-12-31T21:15:00-03:00', '2025-12-31T21:45:00-03:00', 'America/Santiago')
    assert result.rows == () and result.diagnostics == () and result.state == 'no_data'
    assert next(w for w in result.warnings if w.code == 'crossing_intervals_excluded').count == 1


@pytest.mark.parametrize('begin,end,expected,crossings', [
    ('2026-01-01T00:00:00Z', '2026-01-01T01:00:00Z', 1, 0),
    ('2025-12-31T23:00:00Z', '2026-01-01T00:00:00Z', 0, 0),
    ('2026-01-01T01:00:00Z', '2026-01-01T02:00:00Z', 0, 0),
    ('2026-01-01T00:30:00Z', '2026-01-01T02:00:00Z', 0, 1),
    ('2025-12-31T23:00:00Z', '2026-01-01T00:30:00Z', 0, 1),
])
async def test_exact_containment_and_read_only(history_environment, database, clock, begin, end, expected, crossings):
    """Before/after/boundary selections neither prorate the source nor renew its retention."""
    from sqlalchemy import select
    from ecs_ec.consumption.models import IncorporatedRecord
    from ecs_ec.core.unit_of_work import UnitOfWork
    from backend.tests.contract.consumption.test_reception_contract import publish
    await publish(history_environment, [record()])
    async with UnitOfWork(database.sessions) as uow:
        before = [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]
    from zoneinfo import ZoneInfo
    from ecs_ec.consumption.models import instant
    begin = instant(begin).astimezone(ZoneInfo('America/Santiago')).isoformat()
    end = instant(end).astimezone(ZoneInfo('America/Santiago')).isoformat()
    result = await facade(database, clock).detail('CAT-05', begin, end, 'America/Santiago')
    assert len(result.rows) == expected
    assert sum(w.count for w in result.warnings if w.code == 'crossing_intervals_excluded') == crossings
    async with UnitOfWork(database.sessions) as uow:
        assert [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()] == before


async def test_repeated_hour_keeps_both_offsets(history_environment, database, clock):
    """The two Santiago23:00 hours represent distinct UTC intervals independent of host timezone."""
    from backend.tests.contract.consumption.test_reception_contract import publish
    await publish(history_environment, [
        record(start='2025-04-05T23:00:00-03:00', end='2025-04-05T23:00:00-04:00', value='12'),
        record(start='2025-04-05T23:00:00-04:00', end='2025-04-06T00:00:00-04:00', value='8')])
    result = await facade(database, clock).detail('CAT-05', '2025-04-05T23:00:00-03:00',
        '2025-04-06T00:00:00-04:00', 'America/Santiago')
    assert [r.energy_kwh for r in result.rows] == ['12', '8']
    assert result.rows[0].start.endswith('-03:00') and result.rows[1].start.endswith('-04:00')
