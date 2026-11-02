"""Admission/exclusion under independent PostgreSQL sessions, stable input order and shared001 locks."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from ecs_ec.consumption.models import AcceptedMeasurement, IncorporatedRecord
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def test_equivalence_conflict_overlap_and_stable_order(history_environment, database):
    """First valid original wins; equivalents duplicate and contiguity remains valid within one batch."""
    result = await publish(history_environment, [record(value='1000', unit='Wh'), record(), record(value='0.001', unit='MWh'),
        record(value='2'), record(start='2026-01-01T00:30:00Z', end='2026-01-01T01:30:00Z'),
        record(start='2026-01-01T01:00:00Z', end='2026-01-01T02:00:00Z')])
    assert [r.status for r in result.results] == ['accepted', 'duplicate', 'duplicate', 'rejected', 'rejected', 'accepted']
    assert result.results[4].reason_code == 'overlapping_interval'
    async with UnitOfWork(database.sessions) as uow:
        payload = await uow.session.get(AcceptedMeasurement, result.results[0].measurement_id)
        assert payload.original_unit == 'Wh' and payload.original_value_text == '1000'


async def test_two_new_updates_and_two_same_attempt_recoveries(history_environment, database):
    """Distinct attempts serialize categories, identical attempts return the same accepted outcome."""
    fresh = record(start='2025-01-01T00:00:00Z', end='2025-01-01T01:00:00Z')
    results = await asyncio.gather(publish(history_environment, [record()]), publish(history_environment, [fresh]))
    assert sorted(r.results[0].status for r in results) == ['accepted', 'rejected']
    attempt = uuid4()
    other = record(category_id='CAT-03', source_id=UUID(int=3))
    a, b = await asyncio.gather(publish(history_environment, [other], attempt=attempt), publish(history_environment, [other], attempt=attempt))
    assert a == b and a.results[0].status == 'accepted'
    async with UnitOfWork(database.sessions) as uow:
        assert len((await uow.session.scalars(select(IncorporatedRecord))).all()) == 2


async def test_coordinator_runs_with_one_pool_connection(history_environment, database, clock):
    """Admission must not need a second pooled connection while holding its attempt coordinator."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from ecs_ec.core.database import Database
    from ecs_ec.consumption.reception import Reception
    small = Database(database.engine.url)
    await small.close()
    small.engine = create_async_engine(database.engine.url, pool_size=1, max_overflow=0, pool_timeout=2)
    small.sessions = async_sessionmaker(small.engine, expire_on_commit=False)
    try:
        service = Reception(small, clock, authorized_processes={'process:history_test': {UUID(int=99)}})
        outcomes = await asyncio.wait_for(asyncio.gather(*(publish(service, [record()]) for _ in range(4))), timeout=5)
        assert sum(o.results[0].status == 'accepted' for o in outcomes) == 1
        assert sum(o.results[0].status == 'duplicate' for o in outcomes) == 3
    finally:
        await small.close()


async def test_cancelled_coordinator_releases_attempt_lock(history_environment, database, clock, monkeypatch):
    """Cancellation cannot return a pooled connection with an advisory lock still held."""
    service, attempt = history_environment, uuid4()
    original, entered = service._category, asyncio.Event()
    async def wait_before_category(*args):
        """Pause after immutable input commit; cancellation models a stopped executor."""
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(service, '_category', wait_before_category)
    task = asyncio.create_task(publish(service, [record()], attempt=attempt))
    await asyncio.wait_for(entered.wait(), timeout=3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    monkeypatch.setattr(service, '_category', original)
    assert (await asyncio.wait_for(publish(service, [record()], attempt=attempt), timeout=3)).results[0].status == 'accepted'


@pytest.mark.parametrize('first', ['reception', 'configuration'])
async def test_configuration_and_reception_race_in_both_orders(history_environment, database, clock, first, monkeypatch):
    """001/002 share context locks: accepted future bounds reject replacement, or replacement rejects old source."""
    from ecs_ec.consumption.catalog_storage import lock_configuration, read_revisions
    from ecs_ec.consumption.configuration import ConfigurationError, ConfigurationService
    from ecs_ec.consumption.models import ConfigurationInput, SourceInput
    from ecs_ec.consumption.store import MeasurementStore
    attempt = uuid4()
    original = history_environment._category
    async def stop_before_category(*args):
        """Persist immutable attempt before queuing the actual shared context locks."""
        raise RuntimeError('prepare_attempt')
    monkeypatch.setattr(history_environment, '_category', stop_before_category)
    fresh = record(start='2026-01-02T00:00:00Z', end='2026-01-02T01:00:00Z')
    with pytest.raises(RuntimeError, match='prepare_attempt'):
        await publish(history_environment, [fresh], attempt=attempt)
    monkeypatch.setattr(history_environment, '_category', original)
    # Hold context to launch operations in a deterministic PostgreSQL lock queue.
    async with UnitOfWork(database.sessions) as blocker:
        await lock_configuration(blocker, UUID(int=99))
        async with UnitOfWork(database.sessions) as read:
            previous = (await read_revisions(read, UUID(int=99)))[-1]
        request = ConfigurationInput(expected_revision=previous.revision, effective_from=None, timezone=previous.timezone,
            categories=tuple(SourceInput(**(e.model_dump(exclude={'category_revision'}) |
                ({'source_id': UUID(int=50)} if e.category_id == 'CAT-05' else {}))) for e in previous.categories))
        ready = asyncio.Event()
        async def configure():
            """Run001's real writer with002's bounds provider, allowing its safe conflict to be inspected."""
            async with UnitOfWork(database.sessions) as uow:
                ready.set()
                value = await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=UUID(int=99), request=request,
                    actor_ref='process:history_test')
                await uow.commit()
                return value
        async def receive():
            """Attempt old-source future data;001's validation observes configuration after waiting."""
            ready.set()
            return await publish(history_environment, [fresh], attempt=attempt)
        first_task = asyncio.create_task(receive() if first == 'reception' else configure())
        await ready.wait()
        # Wait for the actual first operation's context lock request, rather than a timing assumption.
        async with UnitOfWork(database.sessions) as monitor:
            for _ in range(100):
                from sqlalchemy import text
                waiting = await monitor.session.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock'"))
                if waiting: break
                await asyncio.sleep(0.01)
            assert waiting
        second_task = asyncio.create_task(configure() if first == 'reception' else receive())
        await blocker.commit()
    a, b = await asyncio.gather(first_task, second_task, return_exceptions=True)
    if first == 'reception':
        assert a.results[0].status == 'accepted'
        assert isinstance(b, ConfigurationError) and b.code == 'accepted_interval_conflict'
    else:
        assert not isinstance(a, Exception)
        assert b.results[0].reason_code == 'unknown_or_uninstalled_source'
