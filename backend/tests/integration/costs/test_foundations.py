"""004 prerequisites and money/profile invariants on actual PostgreSQL/identity/consumption providers."""

from uuid import UUID

import pytest
from sqlalchemy import text

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_actual_physical_and_calculated_boundaries(costs_environment, consumption_reception_environment):
    """CalculatedCAT-01 is a limitation; the financial producer cannot replace the physical general meter."""
    env = costs_environment
    await consumption_reception_environment.publish([record(value='12'), record(category_id='CAT-03', source_id=UUID(int=3), value='8')])
    from ecs_ec.consumption.models import instant
    async with UnitOfWork(env['database'].sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        result = await env['consumption'].read_general_snapshot(UUID(int=99), instant('2026-01-01T00:00:00Z'),
            instant('2026-01-01T01:00:00Z'), env['clock'].now(), uow)
        assert result.rows == () and result.reason_code == 'calculated_general'


def test_decimal_and_rounding_boundaries():
    """No binary float, NaN or infinity is accepted; an arbitrary quantum is a multiple, not just a scale."""
    from ecs_ec.costs.money import number, rounded
    for value in (float('nan'), 1.2, True, 'NaN', 'Infinity'):
        with pytest.raises(ValueError): number(value)
    from ecs_ec.costs.schemas import RoundingPolicy
    policy = RoundingPolicy(precision=50, quantum='5', mode='ROUND_HALF_UP', stage='component')
    assert rounded(number('12.5'), policy) == number('15')


async def test_real_identity_permissions(identity, account_factory, session_factory, identity_settings):
    """Actual006 principals can read; only the active administrator can create financial revisions."""
    from ecs_ec.identity.errors import IdentityProblem
    for role in ('operador', 'administrador_tecnico'):
        account = await account_factory(role=role)
        _, principal = await session_factory(account)
        identity.authorize(principal, 'costs.read', identity_settings.building_id)
        if role == 'operador':
            with pytest.raises(IdentityProblem):
                identity.authorize(principal, 'costs.calculations.create', identity_settings.building_id)
        else:
            identity.authorize(principal, 'costs.calculations.create', identity_settings.building_id)


async def test_profile_storage_and_idempotency(costs_environment):
    """PostgreSQL preserves calendar revisions, excludes drafts from selection and atomically stores replay results."""
    from uuid import uuid4
    from ecs_ec.costs.models import Supply
    from ecs_ec.costs.profiles import append_profile
    from ecs_ec.costs.repository import selected_profile, replay, remember, CostsProblem
    from ecs_ec.core.retention import anniversary
    from backend.tests.costs_fixtures import profile_input
    env, supply_id = costs_environment, uuid4()
    clock, database = env['clock'], env['database']
    async with UnitOfWork(database.sessions) as uow:
        supply = Supply(id=supply_id, building_id=UUID(int=99), revision=1, data={}, created_at=clock.now(),
            updated_at=clock.now(), actor_ref='process:fixture', retain_until=anniversary(clock.now(), 'America/Santiago'))
        uow.session.add(supply)
        await uow.session.flush()
        published = await append_profile(uow, supply, profile_input(supply_id), 'process:fixture', clock)
        draft = await append_profile(uow, supply, profile_input(supply_id, previous=str(published.id), state='draft'), 'process:fixture', clock)
        assert (await selected_profile(uow, supply_id, clock.now())).id == published.id
        assert (await selected_profile(uow, supply_id, clock.now(), published=False)).id == draft.id
        assert await replay(uow, 'process:fixture', 'test', 'key', {'a': 1}) is None
        await remember(uow, 'process:fixture', 'test', 'key', {'a': 1}, {'id': str(published.id)}, 201, clock, 'America/Santiago')
        await uow.commit()
    async with UnitOfWork(database.sessions) as uow:
        assert (await replay(uow, 'process:fixture', 'test', 'key', {'a': 1})).resource_id == published.id
        with pytest.raises(CostsProblem, match='idempotency_conflict'):
            await replay(uow, 'process:fixture', 'test', 'key', {'a': 2})
