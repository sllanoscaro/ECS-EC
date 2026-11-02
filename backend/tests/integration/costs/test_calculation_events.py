"""004 producer failures are atomic with009 events and do not require008 or a mail transport."""

import pytest
from sqlalchemy import func, select
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_failed_result_event_and_replay(costs_client, costs_environment, account_factory, session_factory, identity_settings, monkeypatch):
    """A technical engine failure produces one stable failed revision/event in a new valid transaction."""
    from ecs_ec.costs import engine
    env, client = costs_environment, costs_client
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    def crash(*args):
        """Inject a producer failure with a synthetic secret that must not enter a public result or event."""
        raise RuntimeError('synthetic-secret-004')
    monkeypatch.setattr(engine, 'evaluate', crash)
    response = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()['execution_state'] == 'fallido' and response.json()['complete_total'] is None
    assert 'synthetic-secret' not in response.text
    assert (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).json() == response.json()
    async with UnitOfWork(env['database'].sessions) as uow:
        events = (await uow.session.scalars(select(FunctionalEvent).where(FunctionalEvent.source_module == 'costs'))).all()
        assert len(events) == 1 and events[0].event_type == 'cost.failed' and not events[0].accepted_new_data
        assert events[0].source_entity_id.hex == response.json()['id'].replace('-', '')
        assert 'synthetic-secret' not in str(events[0].safe_payload)


async def test_failure_record_and_event_roll_back_together(costs_client, costs_environment, account_factory, session_factory, identity_settings, monkeypatch):
    """If the failure event cannot be stored, neither its failed result nor its snapshot is reported durable."""
    from ecs_ec.costs import engine
    from ecs_ec.audit.events import EventWriter
    from ecs_ec.costs.models import Calculation, InputSnapshot
    body = await prepared(costs_environment)
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    def crash(*args):
        """Simulate an unexpected engine failure after input capture."""
        raise RuntimeError('synthetic_engine_failure')
    original = EventWriter.append
    async def event_failure(self, uow, event):
        """Fail after the result/audit were flushed, proving a valid transaction must still roll everything back."""
        if event.event_type == 'cost.failed':
            raise RuntimeError('synthetic_event_failure')
        return await original(self, uow, event)
    monkeypatch.setattr(engine, 'evaluate', crash)
    monkeypatch.setattr(EventWriter, 'append', event_failure)
    response = await costs_client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert response.status_code == 503
    async with UnitOfWork(costs_environment['database'].sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Calculation)) == 0
        assert await uow.session.scalar(select(func.count()).select_from(InputSnapshot)) == 0
        assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(FunctionalEvent.source_module == 'costs')) == 0
