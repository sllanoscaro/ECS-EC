"""Authenticated daily dashboard over real PostgreSQL001/002 data, not browser fixtures."""
import pytest
from sqlalchemy import select
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_http import authenticate
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def test_dashboard_authorization_exact_projection_and_no_business_writes(client, account_factory,
        session_factory, identity_settings, history_environment, database, clock):
    """Partial categories cannot fabricateCAT-01; public response retains privacy/cache and read-only semantics."""
    service = facade(database, clock)
    client._transport.app.state.consumption = service
    assert (await client.get('/api/v1/consumption/dashboard')).status_code == 401
    await publish(history_environment, [record(value='4')])
    clock.advance(5400)
    await authenticate(client, account_factory, session_factory, identity_settings)
    async with UnitOfWork(database.sessions) as uow:
        before = [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]
    response = await client.get('/api/v1/consumption/dashboard', headers={'X-Session-Activity': 'background'})
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    categories = {c['id']: c for c in data['categories']}
    assert categories['CAT-05']['energy_kwh'] == '4'
    assert categories['CAT-01']['energy_kwh'] is None
    assert len(data['series']) == 90  #22:30 local on the previous date, not a future full day.
    assert all(point['energy_kwh'] is None for point in data['series'])
    # Manual refreshes inside the same quarter must not change coverage or its denominator.
    clock.advance(60)
    refreshed = (await client.get('/api/v1/consumption/dashboard', headers={'X-Session-Activity': 'background'})).json()
    assert refreshed['cutoff_at'] != data['cutoff_at']
    assert refreshed['coverage_end_at'] == data['coverage_end_at']
    assert refreshed['categories'] == data['categories']
    async with UnitOfWork(database.sessions) as uow:
        assert [(r.id, r.retain_until) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()] == before
