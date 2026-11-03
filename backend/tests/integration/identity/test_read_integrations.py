"""006 verifies read grants against real001/002/004 providers and their immutable business state."""
import pytest
from sqlalchemy import text
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice

pytestmark = pytest.mark.integration


async def business_state(database):
    """Capture every owned business row in stable order; only trusted schema table names enter SQL."""
    async with UnitOfWork(database.sessions) as uow:
        names = await uow.session.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE 'consumption_%' OR tablename LIKE 'costs_%') ORDER BY tablename"))
        result = {}
        for name in names:
            assert name.replace('_','').isalnum()
            result[name] = (await uow.session.execute(text(f'SELECT to_jsonb(t) FROM "{name}" t ORDER BY to_jsonb(t)::text'))).scalars().all()
        return result


@pytest.mark.parametrize('role', ['operador', 'administrador_tecnico'])
async def test_real_read_matrix_preserves_business_state(costs_client, costs_environment, account_factory, session_factory, identity_settings, role):
    """Both profiles read seven categories, exact detail/aggregates and persisted financial references without mutation."""
    client, env = costs_client, costs_environment
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    calculation = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert calculation.status_code == 201
    headers['Idempotency-Key'] = 'identity-real-bill'
    bill = await client.post('/api/v1/costs/bills', json=invoice(body), headers=headers)
    assert bill.status_code == 201
    await authenticate(client, account_factory, session_factory, identity_settings, role)
    before = await business_state(env['database'])
    catalog = await client.get('/api/v1/consumption/catalog')
    assert catalog.status_code == 200 and len(catalog.json()['categories']) == 7
    period = dict(start='2025-12-31T21:00:00-03:00', end='2025-12-31T22:00:00-03:00', timezone='America/Santiago')
    for index in range(1,8):
        detail = await client.get(f'/api/v1/consumption/categories/CAT-{index:02}/detail', params=period)
        grouped = await client.get(f'/api/v1/consumption/categories/CAT-{index:02}/aggregates', params=period | {'granularity':'hour'})
        assert detail.status_code == grouped.status_code == 200
        assert detail.headers['cache-control'] == grouped.headers['cache-control'] == 'no-store'
        if index == 1:
            assert detail.json()['rows'][0]['energy_kwh'] == '1000'
    for path in ('/costs/cycles','/costs/bills','/costs/history','/costs/calculations/'+calculation.json()['id']):
        response = await client.get('/api/v1'+path)
        assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
        if path == '/costs/bills':
            assert response.json()['items'][0]['id'] == bill.json()['id']
    assert await business_state(env['database']) == before


async def test_real_query_activity_boundaries(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Real consumption queries extend minute29 to59; background/introspection never revive expired sessions or exceed8h."""
    from datetime import timedelta
    env,client=costs_environment,costs_client
    await prepared(env)
    await authenticate(client,account_factory,session_factory,identity_settings,'operador')
    started=env['clock'].now()
    env['clock'].advance(29*60)
    assert (await client.get('/api/v1/consumption/catalog',headers={'X-Session-Activity':'interactive'})).status_code==200
    data=(await client.get('/api/v1/auth/session',headers={'X-Session-Activity':'interactive'})).json()
    from ecs_ec.consumption.models import instant
    assert instant(data['idle_expires_at'])==started+timedelta(minutes=59)
    env['clock'].advance(30*60)
    assert (await client.get('/api/v1/consumption/catalog',headers={'X-Session-Activity':'interactive'})).status_code==401
    await authenticate(client,account_factory,session_factory,identity_settings,'operador')
    env['clock'].advance(29*60)
    assert (await client.get('/api/v1/consumption/catalog')).status_code==200
    assert (await client.get('/api/v1/auth/session',headers={'X-Session-Activity':'interactive'})).status_code==200
    env['clock'].advance(60)
    assert (await client.get('/api/v1/consumption/catalog')).status_code==401
    await authenticate(client,account_factory,session_factory,identity_settings,'operador')
    started=env['clock'].now()
    for _ in range(16):
        env['clock'].advance(29*60)
        assert (await client.get('/api/v1/consumption/catalog',headers={'X-Session-Activity':'interactive'})).status_code==200
    env['clock'].advance(16*60)
    assert env['clock'].now()==started+timedelta(hours=8)
    assert (await client.get('/api/v1/consumption/catalog',headers={'X-Session-Activity':'interactive'})).status_code==401
