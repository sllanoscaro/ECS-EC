"""Partial006 administration integration against real001/002/004; PDF005 remains an explicit unmet gate."""
from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.integration.identity.test_read_integrations import business_state
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import IncorporatedRecord

pytestmark = pytest.mark.integration


async def test_administrative_admission_and_duplicate_source(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Anonymous/Operator cannot reach maintenance; invalid source reuse leaves the committed revision intact."""
    client, env = costs_client, costs_environment
    await prepared(env)
    for method,path in [('get','/consumption/configuration'),('get','/costs/supply'),('get','/costs/profiles'),
                        ('put','/consumption/configuration'),('put','/costs/supply'),('post','/costs/profiles'),('post','/costs/calculations'),('post','/costs/bills')]:
        response=await getattr(client,method)('/api/v1'+path)
        assert response.status_code == 401
    await authenticate(client,account_factory,session_factory,identity_settings,'operador')
    before=await business_state(env['database'])
    for method,path in [('get','/consumption/configuration'),('get','/costs/supply'),('get','/costs/profiles'),
                        ('put','/consumption/configuration'),('put','/costs/supply'),('post','/costs/profiles'),('post','/costs/calculations'),('post','/costs/bills')]:
        response=await getattr(client,method)('/api/v1'+path)
        assert response.status_code == 403
    assert await business_state(env['database']) == before
    headers=await authenticate(client,account_factory,session_factory,identity_settings)
    current=(await client.get('/api/v1/consumption/configuration')).json()
    command=dict(expected_revision=current['revision'], effective_from=None,timezone=current['timezone'],
        categories=[{k:v for k,v in entry.items() if k!='category_revision'} for entry in current['categories']])
    command['categories'][4]['source_id']=command['categories'][2]['source_id']
    response=await client.put('/api/v1/consumption/configuration',json=command,headers=headers)
    assert response.status_code in (409,422)
    assert (await client.get('/api/v1/consumption/configuration')).json() == current
    assert await business_state(env['database']) == before


async def test_mandatory_retention_is_not_an_editable_identity_setting(costs_environment):
    """The actual002 retention provider rejects removal before its calendar deadline, without any006 settings API."""
    from ecs_ec.consumption.retention import Retention
    env=costs_environment
    await prepared(env)
    async with UnitOfWork(env['database'].sessions) as uow:
        record=await uow.session.scalar(select(IncorporatedRecord).where(IncorporatedRecord.category_id=='CAT-01'))
        identifier=record.id
    result=await Retention(env['database'],env['clock'], authorized_processes={'process:identity_test':{UUID(int=99)}}).withdraw_detail(
        building_id=UUID(int=99),record_ids=(identifier,),process='process:identity_test',reason='protected_fixture')
    assert result[0]['reason_code']=='protected'


async def test_invalid_mutation_does_not_extend_activity(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """Explicit dependencies do not turn a rejected malformed body into interactive session activity."""
    from ecs_ec.identity.models import Session
    from ecs_ec.identity.security import digest
    headers=await authenticate(costs_client,account_factory,session_factory,identity_settings)
    bearer=costs_client.cookies['ecs_ec_session']
    async with UnitOfWork(costs_environment['database'].sessions) as uow:
        row=await uow.session.scalar(select(Session).where(Session.token_digest==digest(bearer)))
        previous=(row.last_activity_at,row.idle_expires_at)
    costs_environment['clock'].advance(29*60)
    response=await costs_client.put('/api/v1/consumption/configuration',json={'malformed':True},headers=headers)
    assert response.status_code==422
    async with UnitOfWork(costs_environment['database'].sessions) as uow:
        row=await uow.session.scalar(select(Session).where(Session.token_digest==digest(bearer)))
        assert (row.last_activity_at,row.idle_expires_at)==previous
