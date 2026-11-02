"""004 calculation HTTP contract with current006 sessions and real001/002 physical evidence."""

from uuid import UUID
import pytest
from backend.tests.costs_fixtures import seed_supply
from backend.tests.unit.consumption.test_validation import record
from backend.tests.contract.consumption.test_reception_contract import publish
from ecs_ec.identity.security import csrf

pytestmark = pytest.mark.integration


async def authenticate(client, account_factory, session_factory, identity_settings, role='administrador_tecnico'):
    """Use a durable ordinary006 session; request bodies never supply principals or permissions."""
    account = await account_factory(role=role)
    bearer, _ = await session_factory(account)
    client.cookies.set('ecs_ec_session', bearer)
    return {'Origin': identity_settings.origin, 'X-CSRF-Token': csrf(identity_settings, 'session', bearer), 'Idempotency-Key': 'synthetic-operation'}


async def prepared(env):
    """Publish a1000kWh physical reference and provision only synthetic004 configuration."""
    supply = await seed_supply(env['database'], env['clock'])
    await publish(env['reception'], [record(category_id='CAT-01', source_id=UUID(int=1), value='1000')])
    env['clock'].advance(7200)
    return dict(supply_id=str(supply.id), start_at='2026-01-01T00:00:00Z', end_at='2026-01-01T01:00:00Z',
        timezone='America/Santiago', boundary_criterion='synthetic:exact')


async def test_calculation_persistence_replay_and_read_only(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """1000×100 persists once, replay precedes new preconditions and reads create no extra revisions."""
    client, env = costs_client, costs_environment
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    result = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert result.status_code == 201, result.text
    data = result.json()
    assert data['complete_total'] == '100000' and data['revision'] == 1
    assert data['snapshot']['supply_revision'] == 1
    assert result.headers['cache-control'] == 'no-store'
    repeated = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert repeated.status_code == 201 and repeated.json() == data
    assert (await client.post('/api/v1/costs/calculations', json=body | {'reason': 'changed'}, headers=headers)).status_code == 409
    assert (await client.get('/api/v1/costs/calculations/' + data['id'])).json() == data
    assert (await client.get('/api/v1/costs/supply')).headers['etag']
    cycles = (await client.get('/api/v1/costs/cycles')).json()
    assert len(cycles['items']) == 1
    assert (await client.post('/api/v1/costs/calculations', json=body)).status_code == 403
    await authenticate(client, account_factory, session_factory, identity_settings, 'operador')
    assert (await client.get('/api/v1/costs/calculations/' + data['id'])).status_code == 200
    assert (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).status_code == 403
