"""Real004 manual bill, immutable correction and explicit pair comparison API contract."""

import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared

pytestmark = pytest.mark.integration


def invoice(body, *, amount='100000'):
    """Document one aligned energy concept and preserve nullable unreported quantities."""
    return dict(supply_id=body['supply_id'], external_identifier='Synthetic invoice004', issued_at='2026-01-02T00:00:00Z',
        start_at=body['start_at'], end_at=body['end_at'], timezone=body['timezone'], boundary_criterion='synthetic:exact', boundary_limited=False,
        declared_start=None, declared_end=None, document_reference='synthetic:invoice', currency='CLP', energy_read='1000',
        demand_read=None, demand_billed=None, declared_tax=None, total_payable=amount,
        lines=[dict(code='energy', description='Synthetic energy', quantity='1000', unit='kWh', amount=amount,
            tax_basis='neto', tax_amount=None, cycle_relation='current_cycle', document_reference='synthetic:energy-line')])


async def test_bill_correction_and_explicit_comparison(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Correcting a bill preserves its old comparison and leaves the new selected pair pending until explicitly compared."""
    body = await prepared(costs_environment)
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    calculation = (await costs_client.post('/api/v1/costs/calculations', json=body, headers=headers)).json()
    headers['Idempotency-Key'] = 'bill-first'
    bill_response = await costs_client.post('/api/v1/costs/bills', json=invoice(body), headers=headers)
    assert bill_response.status_code == 201, bill_response.text
    bill = bill_response.json()
    assert bill['demand_read'] is None and bill['lines'][0]['amount'] == '100000'
    pair = dict(calculation_id=calculation['id'], bill_revision_id=bill['bill_revision_id'])
    headers['Idempotency-Key'] = 'comparison-first'
    comparison_response = await costs_client.post('/api/v1/costs/comparisons', json=pair, headers=headers)
    assert comparison_response.status_code == 201, comparison_response.text
    comparison = comparison_response.json()
    assert comparison['delta_amount'] == '0'
    assert (await costs_client.get('/api/v1/costs/comparisons/' + comparison['id'])).json() == comparison
    headers['Idempotency-Key'] = 'bill-correction'
    correction = invoice(body, amount='90000')
    assert (await costs_client.put('/api/v1/costs/bills/' + bill['id'], json=correction, headers=headers)).status_code == 428
    headers['If-Match'] = bill_response.headers['etag']
    changed = await costs_client.put('/api/v1/costs/bills/' + bill['id'], json=correction, headers=headers)
    assert changed.status_code == 200, changed.text
    assert changed.json()['revision'] == 2 and changed.json()['bill_revision_id'] != bill['bill_revision_id']
    cycle = (await costs_client.get('/api/v1/costs/cycles')).json()['items'][0]
    assert cycle['comparison_status'] == 'missing_for_selected_revisions' and cycle['delta_amount'] is None
    assert (await costs_client.get('/api/v1/costs/bills/' + bill['id'], params={'revision': 1})).json() == bill
    headers['Idempotency-Key'] = 'stale-correction'
    assert (await costs_client.put('/api/v1/costs/bills/' + bill['id'], json=correction, headers=headers)).status_code == 412
