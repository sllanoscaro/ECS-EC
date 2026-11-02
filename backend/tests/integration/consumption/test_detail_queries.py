"""001 queries against real002 storage; reads never incorporate or extend retention."""

from uuid import UUID

import pytest
from sqlalchemy import select

from ecs_ec.consumption.models import IncorporatedRecord, instant
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


def facade(database, clock):
    """Compose001 queries with actual002 storage and the synthetic singleton context."""
    from ecs_ec.consumption.queries import Consumption
    from ecs_ec.consumption.store import MeasurementStore
    return Consumption(database, clock, UUID(int=99), MeasurementStore())


async def test_status_and_global_catalog(history_environment, database, clock):
    """A new acceptance advances status; catalog retains seven and the global extent across categories."""
    service = facade(database, clock)
    before = await service.source_status('CAT-05')
    assert before['last_new_data_at'] is None and before['category_revision'] == 1
    await publish(history_environment, [record(value='1000', unit='Wh')])
    after = await service.source_status('CAT-05')
    assert after['last_new_data_at'] == clock.now()
    clock.advance(899)
    await publish(history_environment, [record()])
    assert (await service.source_status('CAT-05'))['last_new_data_at'] == after['last_new_data_at']
    catalog = await service.catalog()
    assert len(catalog.categories) == 7
    assert instant(catalog.default_period.start) == instant('2026-01-01T00:00:00Z')
    assert instant(catalog.default_period.end) == instant('2026-01-01T01:00:00Z')


async def test_detail_preserves_originals_and_does_not_write(history_environment, database, clock):
    """The exact response copies provenance, zeros and originals; repeated GET leaves deadlines unchanged."""
    await publish(history_environment, [record(value='1000', unit='Wh'),
        record(value='0', start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')])
    service = facade(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        before = [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]
    result = await service.detail('CAT-05', '2026-01-01T00:00:00-03:00', '2026-01-02T00:00:00-03:00', 'America/Santiago')
    assert result.rows == ()
    result = await service.detail('CAT-05', '2025-12-31T21:00:00-03:00', '2025-12-31T23:00:00-03:00', 'America/Santiago')
    assert [r.energy_kwh for r in result.rows] == ['1', '0']
    assert result.rows[0].origin.original_value == '1000'
    assert result.rows[0].category_revision == 1 and result.state == 'available'
    assert result.period.start.endswith('-03:00')
    async with UnitOfWork(database.sessions) as uow:
        assert [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()] == before


async def test_repeatable_capture_under_concurrent_configuration(history_environment, database, clock, monkeypatch):
    """A concurrent source change cannot mix new source configuration into an already-established detail capture."""
    import asyncio
    from backend.tests.integration.consumption.conftest import ReceptionEnvironment
    await publish(history_environment, [record()])
    service = facade(database, clock)
    original = service.store.read_detail
    entered, resume = asyncio.Event(), asyncio.Event()
    async def pause(*args):
        """Pause after the facade has captured old configuration in its repeatable transaction."""
        entered.set()
        await resume.wait()
        return await original(*args)
    monkeypatch.setattr(service.store, 'read_detail', pause)
    task = asyncio.create_task(service.detail('CAT-05', '2025-12-31T21:00:00-03:00', '2026-01-01T23:00:00-03:00', 'America/Santiago'))
    await entered.wait()
    await ReceptionEnvironment(history_environment, database, clock).configure('CAT-05', effective_from='2026-01-01T01:00:00Z')
    resume.set()
    result = await task
    assert {s.category_revision for s in result.configuration_segments} == {1}
    assert result.rows[0].category_revision == 1
    monkeypatch.setattr(service.store, 'read_detail', original)
    fresh = await service.detail('CAT-05', '2025-12-31T21:00:00-03:00', '2026-01-01T23:00:00-03:00', 'America/Santiago')
    assert {s.category_revision for s in fresh.configuration_segments} == {1, 2}


async def test_full_history_no_truncation(history_environment, database, clock, thirteen_month_records, capsys):
    """Thirteen months in all seven categories remain fully queryable, with observed size/time rather than a new SLO."""
    import json
    import time
    await publish(history_environment, thirteen_month_records)
    service = facade(database, clock)
    catalog = await service.catalog()
    begin, byte_count, count = time.perf_counter(), 0, 0
    for category in catalog.categories:
        result = await service.detail(category.id, catalog.default_period.start, catalog.default_period.end, catalog.timezone)
        assert len(result.rows) == 13
        count += len(result.rows)
        byte_count += len(result.model_dump_json().encode())
    with capsys.disabled():
        print(json.dumps({'scenario': '001-history', 'rows': count, 'bytes': byte_count,
            'seconds': round(time.perf_counter() - begin, 4)}))
