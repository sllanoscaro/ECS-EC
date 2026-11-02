"""Installed002 providers use009 composition/lifecycle; no HTTP reception or query side effects."""

import asyncio

import pytest
from pydantic import SecretStr

from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app

pytestmark = pytest.mark.integration


async def test_registered_recovery_is_cancelled_on_shutdown(test_url, tmp_path, clock):
    """The existing application owns exactly one recovery task and releases its DB connections at shutdown."""
    (tmp_path / 'index.html').write_text('<h1>Synthetic static export</h1>')
    app = create_app(Settings(database_url=SecretStr(test_url), web_directory=tmp_path, environment='test'), clock=clock)
    async with app.router.lifespan_context(app):
        assert app.state.consumption_store is not None
        assert app.state.consumption_reception.authorized_processes == {}
        jobs = [task for task in asyncio.all_tasks() if task.get_name() == 'consumption-pending-totals']
        assert len(jobs) == 1
        await asyncio.sleep(0)
    assert jobs[0].done()
    assert app.state.database.engine.pool.checkedout() == 0


async def test_startup_recovers_durable_request_without_candidate(history_environment, database, clock, test_url, tmp_path, monkeypatch):
    """Actual application lifespans recover after a lost producer; a second startup cannot duplicate the total."""
    from sqlalchemy import func, select
    from ecs_ec.consumption.models import IncorporatedRecord
    from ecs_ec.core.unit_of_work import UnitOfWork
    from backend.tests.contract.consumption.test_reception_contract import publish
    from backend.tests.integration.consumption.test_pending_totals import calculated_config, partials
    await calculated_config(database, clock)
    async def crash(*args):
        """Stop after physical commits and before creating anyCAT-01 candidate."""
        raise RuntimeError('producer_stopped')
    monkeypatch.setattr(history_environment, '_evaluate', crash)
    with pytest.raises(RuntimeError, match='producer_stopped'): await publish(history_environment, partials())
    (tmp_path / 'index.html').write_text('<h1>Synthetic static export</h1>')
    for _ in range(2):
        app = create_app(Settings(database_url=SecretStr(test_url), web_directory=tmp_path, environment='test'), clock=clock)
        async with app.router.lifespan_context(app):
            for _ in range(200):
                async with UnitOfWork(app.state.database.sessions) as uow:
                    count = await uow.session.scalar(select(func.count()).select_from(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))
                if count: break
                await asyncio.sleep(0.01)
            assert count == 1
