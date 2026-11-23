"""Energy estimates over real001/002/004/006 data and isolated PostgreSQL."""
from uuid import UUID
import pytest
from sqlalchemy import select

from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.costs.models import Calculation
from ecs_ec.consumption.models import IncorporatedRecord

pytestmark = pytest.mark.integration


async def test_distribution_is_authorized_exact_and_read_only(costs_client, costs_environment,
        account_factory, session_factory, identity_settings):
    client, env = costs_client, costs_environment
    body = await prepared(env)
    await publish(env['reception'], [record(category_id=f'CAT-{i:02}', source_id=UUID(int=i), value=value)
        for i, value in enumerate(('400', '100', '160', '220', '70', '50'), 2)])
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    response = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert response.status_code == 201, response.text
    calculation = response.json()
    path = f'/api/v1/costs/calculations/{calculation["id"]}/distribution'
    await authenticate(client, account_factory, session_factory, identity_settings, 'operador')
    async with UnitOfWork(env['database'].sessions) as uow:
        records_before = [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]
        calculations_before = [r.id for r in (await uow.session.scalars(select(Calculation))).all()]
    response = await client.get(path)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['state'] == 'available' and data['energy_amount'] == '100000'
    assert [row['estimated_amount'] for row in data['categories']] == ['40000', '10000', '16000', '22000', '7000', '5000']
    assert data['unassigned_amount'] == '0'
    assert (await client.get('/api/v1/costs/calculations/' + calculation['id'])).json() == calculation
    async with UnitOfWork(env['database'].sessions) as uow:
        assert [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()] == records_before
        assert [r.id for r in (await uow.session.scalars(select(Calculation))).all()] == calculations_before
    assert (await client.get('/api/v1/costs/calculations/' + str(UUID(int=999)) + '/distribution')).status_code == 404
    client.cookies.clear()
    assert (await client.get(path)).status_code == 401
