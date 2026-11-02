"""Actual002 original withdrawal cannot destroy004's protected reproducible financial evidence."""

import pytest
from uuid import UUID
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import instant
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate

pytestmark = pytest.mark.integration


async def test_reproduction_after_real_original_withdrawal(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Withdraw at the original's real calendar minimum, while the later004 snapshot is still protected."""
    from ecs_ec.consumption.retention import Retention
    from ecs_ec.costs.reproduction import reproduce
    env, client = costs_environment, costs_client
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    saved = (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).json()
    record_id = UUID(saved['snapshot']['measurements'][0]['record_id'])
    target = instant('2027-01-01T01:00:00Z')
    env['clock'].advance((target-env['clock'].now()).total_seconds())
    retention = Retention(env['database'], env['clock'], authorized_processes={'process:costs_test': {env['building_id']}})
    result = await retention.withdraw_detail(building_id=env['building_id'], record_ids=[record_id], process='process:costs_test', reason='synthetic_expiry')
    assert result[0]['status'] == 'withdrawn'
    assert reproduce(saved['snapshot'], saved['input_hash'], saved['engine_version'])['complete_total'] == '100000'


async def test_reproduction_rejects_tampering_or_unknown_engine(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Preserved inputs are verified before evaluation, rather than accepting mutable financial evidence."""
    import copy
    from ecs_ec.costs.reproduction import reproduce
    from ecs_ec.costs.repository import CostsProblem
    body = await prepared(costs_environment)
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    saved = (await costs_client.post('/api/v1/costs/calculations', json=body, headers=headers)).json()
    forged = copy.deepcopy(saved['snapshot'])
    forged['measurements'][0]['energy_kwh'] = '1001'
    with pytest.raises(CostsProblem, match='snapshot_hash_mismatch'):
        reproduce(forged, saved['input_hash'], saved['engine_version'])
    with pytest.raises(CostsProblem, match='engine_version_unavailable'):
        reproduce(saved['snapshot'], saved['input_hash'], 'future-engine')
