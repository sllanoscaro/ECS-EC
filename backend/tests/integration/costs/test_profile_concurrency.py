"""Real PostgreSQL full-calendar concurrency: one winner and immutable selected publications."""

import asyncio
import pytest
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.costs.profiles import append_profile
from ecs_ec.costs.repository import CostsProblem, selected_profile
from backend.tests.costs_fixtures import seed_supply, profile_input

pytestmark = pytest.mark.integration


async def test_two_publications_share_a_real_supply_lock(costs_environment):
    """Independent transactions based on the same saved revision cannot both publish another revision."""
    env = costs_environment
    supply = await seed_supply(env['database'], env['clock'])
    async with UnitOfWork(env['database'].sessions) as uow:
        previous = await selected_profile(uow, supply.id, env['clock'].now(), published=False)
        previous_id = previous.id
    async def publish(price):
        """Invoke the actual004 calendar writer in an independent PostgreSQL transaction."""
        async with UnitOfWork(env['database'].sessions) as uow:
            value = await append_profile(uow, supply, profile_input(supply.id, previous=str(previous_id), price=price), 'process:fixture', env['clock'])
            await uow.commit()
            return value.id
    results = await asyncio.gather(publish('110'), publish('120'), return_exceptions=True)
    assert sum(isinstance(value, CostsProblem) for value in results) == 1
    async with UnitOfWork(env['database'].sessions) as uow:
        latest = await selected_profile(uow, supply.id, env['clock'].now())
        assert latest.revision == 2 and latest.previous_version_id == previous_id
        from ecs_ec.costs.models import ProfileVersion
        original = await uow.session.get(ProfileVersion, previous_id)
        assert original.data['segments'][0]['charges'][0]['unit_price'] == '100'


async def test_concurrent_supply_creation_and_edit_have_one_winner(costs_client, account_factory, session_factory, identity_settings):
    """The common building lock protects the absent singleton and strong revision edits across independent requests."""
    from backend.tests.contract.costs.test_calculations_api import authenticate
    from backend.tests.contract.costs.test_profiles_api import supply_body
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    async def create(key):
        """Create an initially absent supply through the real006/004 route with explicit precondition."""
        return await costs_client.put('/api/v1/costs/supply', json=supply_body(), headers=headers | {'Idempotency-Key':key, 'If-None-Match':'*'})
    results = await asyncio.gather(create('supply-race-a'), create('supply-race-b'))
    assert sorted(r.status_code for r in results) == [201,412]
    winner = next(r for r in results if r.status_code == 201)
    async def edit(key, location):
        """Race two reviewed edits; only one may advance the original singleton revision."""
        return await costs_client.put('/api/v1/costs/supply', json=supply_body() | {'location':location}, headers=headers | {'Idempotency-Key':key, 'If-Match':winner.headers['etag']})
    results = await asyncio.gather(edit('supply-edit-a','a'), edit('supply-edit-b','b'))
    assert sorted(r.status_code for r in results) == [200,412]
    assert (await costs_client.get('/api/v1/costs/supply')).json()['revision'] == 2
