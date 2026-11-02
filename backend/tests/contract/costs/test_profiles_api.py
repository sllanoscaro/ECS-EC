"""004 supply/profile preconditions and full-calendar concurrency contract over actual006/001/002."""

import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.costs_fixtures import profile_input

pytestmark = pytest.mark.integration


def supply_body():
    """Identify the synthetic physical general source already provisioned by001, without inventing real conditions."""
    return dict(general_board_ref='synthetic:board', category_id='CAT-01', general_source_id='00000000-0000-0000-0000-000000000001',
        distributor='synthetic', location='synthetic', connection_conditions='synthetic', document_refs=['synthetic:source'], measurement_point_differences=[])


async def test_supply_and_profile_replay_preconditions(costs_client, account_factory, session_factory, identity_settings):
    """Replay precedes new preconditions; drafts never replace the selected published calendar and stale bases conflict."""
    client = costs_client
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    assert (await client.get('/api/v1/costs/supply')).status_code == 404
    assert (await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers)).status_code == 428
    assert (await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers | {'If-Match':'x','If-None-Match':'*'})).status_code == 422
    headers['If-None-Match'] = '*'
    response = await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers)
    assert response.status_code == 201, response.text
    supply = response.json()
    assert (await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers)).json() == supply
    headers['Idempotency-Key'] = 'another-supply'
    assert (await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers)).status_code == 412
    del headers['If-None-Match']
    headers['If-Match'] = response.headers['etag']
    changed = await client.put('/api/v1/costs/supply', json=supply_body() | {'location': 'new synthetic location'}, headers=headers)
    assert changed.status_code == 200 and changed.json()['revision'] == 2
    headers['Idempotency-Key'] = 'stale-supply'
    assert (await client.put('/api/v1/costs/supply', json=supply_body(), headers=headers)).status_code == 412
    headers.pop('If-Match')
    headers['Idempotency-Key'] = 'profile-published'
    published = await client.post('/api/v1/costs/profiles', json=profile_input(supply['id']), headers=headers)
    assert published.status_code == 201, published.text
    headers['Idempotency-Key'] = 'profile-draft'
    draft = await client.post('/api/v1/costs/profiles', json=profile_input(supply['id'], previous=published.json()['id'], state='draft'), headers=headers)
    assert draft.status_code == 201
    page = (await client.get('/api/v1/costs/profiles')).json()
    assert page['latest_version_id'] == draft.json()['id'] and page['selected_published_version_id'] == published.json()['id']
    headers['Idempotency-Key'] = 'profile-stale'
    assert (await client.post('/api/v1/costs/profiles', json=profile_input(supply['id'], previous=published.json()['id']), headers=headers)).status_code == 409


async def test_full_calendar_publication_preserves_saved_calculation(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """V1 open→V2 full split→V3 retroactive correction never changes the capturedV1 price; draft does not replaceV3."""
    from copy import deepcopy
    from backend.tests.contract.costs.test_calculations_api import prepared
    client = costs_client
    body = await prepared(costs_environment)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    original = (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).json()
    page = (await client.get('/api/v1/costs/profiles')).json()
    full = profile_input(body['supply_id'], previous=page['latest_version_id'])
    second = deepcopy(full['segments'][0]); second['valid_from'] = '2026-07-01T00:00:00Z'; second['charges'][0]['unit_price'] = '110'
    full['segments'][0]['valid_to'] = second['valid_from']; full['segments'].append(second)
    v2 = await client.post('/api/v1/costs/profiles', json=full, headers=headers | {'Idempotency-Key':'calendar-v2'})
    assert v2.status_code == 201
    full['expected_previous_version_id'] = v2.json()['id']; full['segments'][0]['charges'][0]['unit_price'] = '105'
    v3 = await client.post('/api/v1/costs/profiles', json=full, headers=headers | {'Idempotency-Key':'calendar-v3'})
    assert v3.status_code == 201
    full['expected_previous_version_id'] = v3.json()['id']; full['publication_state'] = 'draft'; full['segments'][0]['charges'][0]['unit_price'] = '120'
    draft = await client.post('/api/v1/costs/profiles', json=full, headers=headers | {'Idempotency-Key':'calendar-draft'})
    assert draft.status_code == 201
    corrected = await client.post('/api/v1/costs/calculations', json=body | {'reason':'synthetic retroactive correction'}, headers=headers | {'Idempotency-Key':'calendar-recalculate'})
    assert corrected.status_code == 201 and corrected.json()['complete_total'] == '105000'
    assert corrected.json()['snapshot']['profile_id'] == v3.json()['id']
    assert (await client.get('/api/v1/costs/calculations/'+original['id'])).json() == original
    invalid = deepcopy(full); invalid['expected_previous_version_id'] = draft.json()['id']; invalid['segments'].append(deepcopy(invalid['segments'][0]))
    assert (await client.post('/api/v1/costs/profiles', json=invalid, headers=headers | {'Idempotency-Key':'calendar-invalid'})).status_code == 422
    assert (await client.get('/api/v1/costs/profiles')).json()['latest_version_id'] == draft.json()['id']
