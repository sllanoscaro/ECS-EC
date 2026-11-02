"""Authenticated002 grouped HTTP contract; errors keep006 policy and exact wire values."""
import pytest

from backend.tests.contract.consumption.test_http import authenticate
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration
PATH = '/api/v1/consumption/categories/CAT-05/aggregates'
PARAMS = dict(start='2025-12-31T21:00:00-03:00', end='2025-12-31T23:00:00-03:00', timezone='America/Santiago', granularity='hour')


async def test_grouped_wire_and_session(client, account_factory, session_factory, identity_settings, history_environment, database, clock):
    """No-store covers anonymous, success and validation; nullable empty evidence stays present."""
    assert (await client.get(PATH, params=PARAMS)).status_code == 401
    client._transport.app.state.consumption = facade(database, clock)
    await authenticate(client, account_factory, session_factory, identity_settings)
    await publish(history_environment, [record(value='0')])
    response = await client.get(PATH, params=PARAMS)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    result = response.json()
    assert result['period'] == {k: PARAMS[k] for k in ('start', 'end', 'timezone')}
    block, empty = result['blocks']
    assert block['energy_kwh'] == '0' and block['duration_us'] == '3600000000'
    assert block['coverage_state'] == 'complete' and block['start'].endswith('-03:00')
    for field in ('aggregate_id', 'revision', 'created_at', 'last_new_data_at', 'retain_until', 'energy_kwh'):
        assert field in empty and empty[field] is None
    for replacement in ({'timezone': 'UTC'}, {'granularity': 'minute'}, {'start': '2025-12-31T21:00:00-04:00'}, {'end': PARAMS['start']}):
        error = await client.get(PATH, params=PARAMS | replacement)
        assert error.status_code == 422 and error.headers['cache-control'] == 'no-store'
    assert (await client.get(PATH.replace('CAT-05', 'CAT-08'), params=PARAMS)).status_code == 404


async def test_grouped_provider_error_is_not_absence(client, account_factory, session_factory, identity_settings, history_environment, database, clock, monkeypatch):
    """A failing indispensable provider returns503 with a safe problem and no-store."""
    service = facade(database, clock)
    client._transport.app.state.consumption = service
    await authenticate(client, account_factory, session_factory, identity_settings)
    async def fail(*args, **kwargs):
        """Simulate an internal provider error with secret-looking text that must not be reflected."""
        raise ValueError('private-provider-details')
    monkeypatch.setattr(service, 'query_aggregates', fail)
    response = await client.get(PATH, params=PARAMS)
    assert response.status_code == 503 and response.headers['cache-control'] == 'no-store'
    assert 'private-provider-details' not in response.text


async def test_grouped_current_renewal_and_microsecond_policy(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock):
    """Renewal is403 before selection parsing; valid microseconds are conserved and excess precision rejected."""
    client._transport.app.state.consumption = facade(database, clock)
    account = await account_factory(renewal=True)
    bearer, _ = await session_factory(account)
    client.cookies.set('ecs_ec_session', bearer)
    response = await client.get(PATH, params=PARAMS)
    assert response.status_code == 403 and response.headers['cache-control'] == 'no-store'
    await authenticate(client, account_factory, session_factory, identity_settings)
    response = await client.get(PATH, params=PARAMS | {'start': '2025-12-31T21:00:00.000001-03:00'})
    assert response.status_code == 200 and response.json()['period']['start'].endswith('00.000001-03:00')
    response = await client.get(PATH, params=PARAMS | {'start': '2025-12-31T21:00:00.0000001-03:00'})
    assert response.status_code == 422
