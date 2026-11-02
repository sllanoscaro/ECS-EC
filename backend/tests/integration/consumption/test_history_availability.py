"""Real DB/session reads remain separate from unavailable technical transports and have no business side effects."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from backend.tests.contract.consumption.test_aggregate_http import PATH, PARAMS
from backend.tests.contract.consumption.test_http import authenticate
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.models import ConsumptionAggregate, IncorporatedRecord
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_grouped_failure_recovers_without_modifying_evidence(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, monkeypatch):
    """A DB operation error is503, never no_data; reconnecting/querying leaves revisions/deadlines unchanged."""
    await publish(history_environment, [record()])
    service = facade(database, clock)
    client._transport.app.state.consumption = service
    await authenticate(client, account_factory, session_factory, identity_settings)
    async with UnitOfWork(database.sessions) as uow:
        before = [(r.id, r.revision, r.retain_until) for r in (await uow.session.scalars(select(ConsumptionAggregate))).all()]
    async def fail(*args, **kwargs):
        """Fail at the mandatory storage read boundary, as a real lost DB connection would."""
        raise OperationalError('synthetic', {}, Exception('private database error'))
    with monkeypatch.context() as patch:
        patch.setattr(service.store, 'read_detail', fail)
        response = await client.get(PATH, params=PARAMS)
        assert response.status_code == 503 and response.headers['cache-control'] == 'no-store'
        assert 'private database error' not in response.text
    await database.engine.dispose()
    response = await client.get(PATH, params=PARAMS)
    assert response.status_code == 200 and response.json()['blocks'][0]['energy_kwh'] == '1'
    async with UnitOfWork(database.sessions) as uow:
        assert [(r.id, r.revision, r.retain_until) for r in (await uow.session.scalars(select(ConsumptionAggregate))).all()] == before
        assert len((await uow.session.scalars(select(IncorporatedRecord))).all()) == 1
