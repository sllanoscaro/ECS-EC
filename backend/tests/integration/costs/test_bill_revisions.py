"""Real004 invoice identity/correction races cannot duplicate a document or overwrite an old revision."""

import asyncio
import pytest
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice

pytestmark = pytest.mark.integration


async def test_concurrent_document_identity_and_stale_correction(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Identical concurrent registrations return one logical/revision ID; stale corrections have one winner."""
    body = await prepared(costs_environment)
    headers = await authenticate(costs_client, account_factory, session_factory, identity_settings)
    async def create(key):
        """Submit one explicit operation with its own idempotency identity."""
        return await costs_client.post('/api/v1/costs/bills', json=invoice(body), headers=headers | {'Idempotency-Key': key})
    a, b = await asyncio.gather(create('bill-a'), create('bill-b'))
    assert sorted([a.status_code,b.status_code]) == [200,201]
    assert a.json()['bill_revision_id'] == b.json()['bill_revision_id']
    tag, identifier = a.headers['etag'], a.json()['id']
    async def correct(key, amount):
        """Race independently keyed corrections against the exact same reviewed revision tag."""
        return await costs_client.put('/api/v1/costs/bills/'+identifier, json=invoice(body, amount=amount),
            headers=headers | {'Idempotency-Key': key, 'If-Match': tag})
    changed = await asyncio.gather(correct('fix-a','90000'), correct('fix-b','80000'))
    assert sorted(value.status_code for value in changed) == [200,412]
    original = await costs_client.get('/api/v1/costs/bills/'+identifier, params={'revision':1})
    assert original.json()['total_payable'] == '100000'
    assert len((await costs_client.get('/api/v1/costs/bills')).json()['items']) == 2
