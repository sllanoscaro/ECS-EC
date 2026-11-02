"""004 authorization is current006 state and its financial producer never calls optional consumers."""

import sys
import pytest
from sqlalchemy import select, func
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.costs.models import Calculation
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate

pytestmark = pytest.mark.integration


async def test_revoked_session_cannot_replay_or_read(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """A previously authorized idempotency key never grants access after the ordinary006 logout revokes its session."""
    client = costs_client
    body = await prepared(costs_environment)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    saved = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert saved.status_code == 201
    bearer = client.cookies['ecs_ec_session']
    assert (await client.post('/api/v1/auth/logout', headers=headers)).status_code == 204
    client.cookies.set('ecs_ec_session', bearer)
    assert (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).status_code == 401
    assert (await client.get('/api/v1/costs/calculations/'+saved.json()['id'])).status_code == 401
    async with UnitOfWork(costs_environment['database'].sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Calculation)) == 1


async def test_no_optional_consumer_required(costs_client, costs_environment, account_factory, session_factory, identity_settings, monkeypatch):
    """Unavailable SMTP/notification/telemetry modules cannot prevent the real financial transaction."""
    for module in ['ecs_ec.notifications', 'smtplib', 'opentelemetry']:
        monkeypatch.setitem(sys.modules, module, None)
    body = await prepared(costs_environment)
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    response = await costs_client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert response.status_code == 201 and response.json()['complete_total'] == '100000'
    assert 'synthetic-local-test' not in response.text and 'ecs_ec_session' not in response.text
    await authenticate(costs_client, account_factory, session_factory, identity_settings, 'operador')
    assert (await costs_client.get('/api/v1/costs/supply')).status_code == 403
    assert (await costs_client.post('/api/v1/costs/bills', json={}, headers=headers)).status_code == 403
