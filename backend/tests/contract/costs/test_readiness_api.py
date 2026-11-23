"""Empty-state diagnostics preserve authorization and never create financial data."""
import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate

pytestmark=pytest.mark.integration

async def test_operator_gets_only_prerequisite_flags_without_admin_prices(costs_client,account_factory,session_factory,identity_settings):
    path='/api/v1/costs/readiness'
    assert (await costs_client.get(path)).status_code==401
    await authenticate(costs_client,account_factory,session_factory,identity_settings,'operador')
    response=await costs_client.get(path)
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    assert response.json()=={'physical_general':True,'supply_configured':False,'profile_published':False}
    assert (await costs_client.get('/api/v1/costs/cycles')).json()['items']==[]
