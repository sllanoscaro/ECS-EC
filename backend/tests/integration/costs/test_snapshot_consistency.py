"""004 financial capture shares a real repeatable snapshot with consumers during concurrent bill corrections."""

import pytest
from sqlalchemy import select, text
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import instant
from ecs_ec.costs.models import BillRevision
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice

pytestmark = pytest.mark.integration


async def test_shared_uow_does_not_mix_new_bill(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """A caller's existing read snapshot keepsB1 while a fresh capture seesB2; neither capture creates comparisons."""
    client, env = costs_client, costs_environment
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    headers['Idempotency-Key'] = 'shared-bill'
    response = await client.post('/api/v1/costs/bills', json=invoice(body), headers=headers)
    bill = response.json()
    service = client._transport.app.state.costs
    principal = await service.identity.resolve_session(client.cookies['ecs_ec_session'])
    start, end = instant('2026-01-01T01:00:00Z'), instant('2026-02-01T00:00:00Z')
    async with UnitOfWork(env['database'].sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        await uow.session.scalar(select(BillRevision.id))
        consumption = await env['consumption'].read_general_snapshot(env['building_id'], instant(body['start_at']), instant(body['end_at']), env['clock'].now(), uow)
        assert str(consumption.rows[0].energy_kwh) == '1000'
        env['clock'].advance(1)
        correction = await client.put('/api/v1/costs/bills/'+bill['id'], json=invoice(body,amount='90000'),
            headers=headers | {'Idempotency-Key':'shared-correction','If-Match':response.headers['etag']})
        assert correction.status_code == 200
        recalculated = await client.post('/api/v1/costs/calculations', json=body | {'reason':'synthetic concurrent recalculation'},
            headers=headers | {'Idempotency-Key':'shared-recalculation'})
        assert recalculated.status_code == 201
        captured = await service.read_snapshot(env['building_id'], start, end, env['clock'].now(), principal, unit_of_work=uow)
        assert captured.cycles[0].bill.revision == 1 and captured.cycles[0].calculation.revision == 1
        fresh = await service.read_snapshot(env['building_id'], start, end, env['clock'].now(), principal)
        assert fresh.cycles[0].bill.revision == 2 and fresh.cycles[0].calculation.revision == 2
        assert fresh.cycles[0].comparison is None and fresh.comparison_totals == ()
