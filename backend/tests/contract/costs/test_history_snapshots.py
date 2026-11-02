"""004 producer snapshot selects immutable financial revisions before resolving their exact comparison pair."""

import pytest
from ecs_ec.consumption.models import instant
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice

pytestmark = pytest.mark.integration


async def test_snapshot_never_backtracks_comparison(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """CorrectingB1→B2 leavesC1/B2 pending, while the old cutoff continues to selectC1/B1/K1."""
    env, client = costs_environment, costs_client
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    calc = (await client.post('/api/v1/costs/calculations', json=body, headers=headers)).json()
    headers['Idempotency-Key'] = 'snapshot-bill'
    bill_response = await client.post('/api/v1/costs/bills', json=invoice(body), headers=headers)
    bill = bill_response.json()
    headers['Idempotency-Key'] = 'snapshot-comparison'
    old = (await client.post('/api/v1/costs/comparisons', json=dict(calculation_id=calc['id'], bill_revision_id=bill['bill_revision_id']), headers=headers)).json()
    service = client._transport.app.state.costs
    principal = await service.identity.resolve_session(client.cookies['ecs_ec_session'])
    start, end, cutoff = instant('2026-01-01T01:00:00Z'), instant('2026-02-01T00:00:00Z'), env['clock'].now()
    first = await service.read_snapshot(env['building_id'], start, end, cutoff, principal)
    assert first.cycles[0].comparison.id.hex == old['id'].replace('-', '')
    env['clock'].advance(1)
    headers |= {'Idempotency-Key':'snapshot-correction', 'If-Match':bill_response.headers['etag']}
    correction = await client.put('/api/v1/costs/bills/'+bill['id'], json=invoice(body, amount='90000'), headers=headers)
    assert correction.status_code == 200
    second = await service.read_snapshot(env['building_id'], start, end, env['clock'].now(), principal)
    assert second.cycles[0].comparison_status == 'missing_for_selected_revisions'
    assert second.cycles[0].delta_amount is None and not second.comparison_totals
    repeated = await service.read_snapshot(env['building_id'], start, end, cutoff, principal)
    assert repeated.cycles[0].bill.bill_revision_id == first.cycles[0].bill.bill_revision_id
    assert repeated.cycles[0].comparison.id == first.cycles[0].comparison.id
    assert (await client.get('/api/v1/costs/history')).status_code == 200

    headers['Idempotency-Key'] = 'snapshot-new-exact-comparison'
    newer = await client.post('/api/v1/costs/comparisons', json=dict(calculation_id=calc['id'], bill_revision_id=correction.json()['bill_revision_id']), headers=headers)
    assert newer.status_code == 201
    third = await service.read_snapshot(env['building_id'], start, end, env['clock'].now(), principal)
    assert third.cycles[0].comparison_status == 'available' and third.comparison_totals[0].delta_amount == '10000'
    env['clock'].advance(1)
    headers['Idempotency-Key'] = 'snapshot-recalculated'
    recalculated = await client.post('/api/v1/costs/calculations', json=body | {'reason':'synthetic new capture'}, headers=headers)
    assert recalculated.status_code == 201
    pending = await service.read_snapshot(env['building_id'], start, end, env['clock'].now(), principal)
    assert pending.cycles[0].comparison_status == 'missing_for_selected_revisions' and not pending.comparison_totals
    assert pending.cycles[0].delta_amount is None
    unchanged = await service.read_snapshot(env['building_id'], start, end, cutoff, principal)
    assert unchanged.cycles[0].comparison.id == first.cycles[0].comparison.id
