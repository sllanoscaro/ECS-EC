"""At least twelve actual monthly cycles remain selectable with signed fixed-cutoff continuation."""

from datetime import datetime, UTC
import pytest
from backend.tests.costs_fixtures import seed_supply
from backend.tests.contract.costs.test_calculations_api import authenticate

pytestmark = pytest.mark.integration


async def test_twelve_months_cursor_and_read_only_retention(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Create actual004 partial cycles, page across12 months and reject a cursor with changed filters."""
    env, client = costs_environment, costs_client
    supply = await seed_supply(env['database'], env['clock'])
    env['clock'].advance((datetime(2027, 1, 2, tzinfo=UTC)-env['clock'].now()).total_seconds())
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    for month in range(1, 13):
        start = datetime(2026, month, 1, tzinfo=UTC)
        end = datetime(2026 + (month == 12), month % 12 + 1, 1, tzinfo=UTC)
        body = dict(supply_id=str(supply.id), start_at=start.isoformat(), end_at=end.isoformat(), timezone='America/Santiago', boundary_criterion='synthetic:months')
        response = await client.post('/api/v1/costs/calculations', json=body, headers=headers | {'Idempotency-Key': f'month-{month}'})
        assert response.status_code == 201, response.text
        assert response.json()['complete_total'] is None
    first = (await client.get('/api/v1/costs/history?limit=5')).json()
    cutoff, items, cursor = first['cutoff_at'], first['items'], first['next_cursor']
    assert len(items) == 5 and cursor
    bad = await client.get('/api/v1/costs/history', params={'limit':5, 'cursor':cursor, 'from':'2026-02-01T00:00:00Z'})
    assert bad.status_code == 422
    while cursor:
        page = (await client.get('/api/v1/costs/history', params={'limit':5,'cursor':cursor})).json()
        assert page['cutoff_at'] == cutoff
        items += page['items']; cursor = page['next_cursor']
    assert len({item['id'] for item in items}) == 12
    assert [item['calculation']['revision'] for item in items] == [1]*12
    again = (await client.get('/api/v1/costs/history?limit=100')).json()
    assert [item['calculation']['retain_until'] for item in again['items']] == [item['calculation']['retain_until'] for item in items]
