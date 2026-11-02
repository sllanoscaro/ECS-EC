"""Real session admission and001 wire contracts over an isolated PostgreSQL context."""

import json
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator

from ecs_ec.identity.security import csrf

pytestmark = pytest.mark.integration


async def authenticate(client, account_factory, session_factory, identity_settings, *, role='operador'):
    """Install an ordinary opaque test session backed by the real006 rows."""
    account = await account_factory(role=role)
    bearer, _ = await session_factory(account)
    client.cookies.set('ecs_ec_session', bearer)
    return {'Origin': identity_settings.origin, 'X-CSRF-Token': csrf(identity_settings, 'session', bearer)}


async def test_authorization_before_invalid_body(client, account_factory, session_factory, identity_settings):
    """Anonymous/Operator callers cannot inspect administrative data or exploit body validation order."""
    for path in ('/consumption/catalog', '/consumption/configuration'):
        response = await client.get('/api/v1' + path)
        assert response.status_code == 401 and response.headers['cache-control'] == 'no-store'
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    assert (await client.get('/api/v1/consumption/configuration')).status_code == 403
    assert (await client.put('/api/v1/consumption/configuration', content='invalid', headers=headers)).status_code == 403


async def test_catalog_detail_configuration_contract(client, account_factory, session_factory, identity_settings,
        history_environment, database, clock):
    """Every public response matches001's frozen OpenAPI and maintains actual session/CSRF policy."""
    from backend.tests.integration.consumption.test_detail_queries import facade
    # The production binding uses the configured identity singleton. This fixture has its own UUID99 context.
    client._transport.app.state.consumption = facade(database, clock)
    headers = await authenticate(client, account_factory, session_factory, identity_settings, role='administrador_tecnico')
    installed = client._transport.app.openapi()
    assert installed['paths']['/api/v1/consumption/configuration']['put']['security'] == [{'SessionCookie': [], 'CsrfToken': []}]
    assert '503' in installed['paths']['/api/v1/consumption/catalog']['get']['responses']
    document = json.loads(Path('specs/001-visualizar-consumo-categorias/contracts/openapi.json').read_text())
    for path, schema in (('/consumption/catalog', 'Catalog'), ('/consumption/configuration', 'Configuration'),
        ('/consumption/categories/CAT-05/detail?start=2025-12-31T21:00:00-03:00&end=2025-12-31T22:00:00-03:00&timezone=America/Santiago', 'DetailResult')):
        response = await client.get('/api/v1' + path)
        assert response.status_code == 200, response.text
        Draft202012Validator({'$ref': f'#/components/schemas/{schema}', 'components': document['components']}).validate(response.json())
        assert response.headers['cache-control'] == 'no-store'
    current = (await client.get('/api/v1/consumption/configuration')).json()
    command = dict(expected_revision=current['revision'], effective_from=None, timezone=current['timezone'],
        categories=[{k: v for k, v in c.items() if k != 'category_revision'} for c in current['categories']])
    assert (await client.put('/api/v1/consumption/configuration', json=command)).status_code == 403
    assert (await client.put('/api/v1/consumption/configuration', json=command, headers=headers)).status_code == 200
    assert (await client.put('/api/v1/consumption/configuration', json=command | {'expected_revision': 0}, headers=headers)).status_code == 409
    command['categories'][0]['category_revision'] = 99
    assert (await client.put('/api/v1/consumption/configuration', json=command, headers=headers)).status_code == 422
    for path in ('/consumption/categories/CAT-08/detail?start=x',
                 '/consumption/categories/CAT-05/detail?start=x&end=y&timezone=America/Santiago'):
        response = await client.get('/api/v1' + path)
        assert response.status_code in (404, 422) and response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('condition', ['renewal', 'inactive', 'revoked'])
async def test_current_identity_is_required(client, account_factory, session_factory, condition):
    """Current renewal/state/revocation wins over any previously valid browser cookie."""
    account = await account_factory(renewal=condition == 'renewal', status='inactive' if condition == 'inactive' else 'active')
    bearer, principal = await session_factory(account)
    if condition == 'revoked':
        from ecs_ec.identity.sessions import logout
        await logout(client._transport.app.state.identity, principal)
    client.cookies.set('ecs_ec_session', bearer)
    response = await client.get('/api/v1/consumption/catalog')
    assert response.status_code == (403 if condition == 'renewal' else 401)
    assert response.headers['cache-control'] == 'no-store'


async def test_calculated_wire_schema(client, account_factory, session_factory,
        identity_settings, consumption_reception_environment, database, clock):
    """Actual measured and calculated rows match the same published schema, including originals and contributions."""
    from backend.tests.integration.consumption.test_detail_queries import facade
    from backend.tests.unit.consumption.test_validation import record
    await consumption_reception_environment.publish([record(value='12'), record(category_id='CAT-03', source_id=UUID(int=3), value='8')])
    client._transport.app.state.consumption = facade(database, clock)
    await authenticate(client, account_factory, session_factory, identity_settings)
    document = json.loads(Path('specs/001-visualizar-consumo-categorias/contracts/openapi.json').read_text())
    validator = Draft202012Validator({'$ref': '#/components/schemas/DetailResult', 'components': document['components']})
    for category in ('CAT-05', 'CAT-01'):
        response = await client.get(f'/api/v1/consumption/categories/{category}/detail', params={
            'start': '2025-12-31T21:00:00-03:00', 'end': '2025-12-31T22:00:00-03:00', 'timezone': 'America/Santiago'})
        assert response.status_code == 200
        validator.validate(response.json())
        assert response.json()['rows'][0]['energy_kwh'] == ('12' if category == 'CAT-05' else '20')
