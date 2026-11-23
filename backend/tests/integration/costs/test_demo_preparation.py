"""Local-demo orchestration uses real owned services and preserves consumption on rerun."""
import importlib.util
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.settings import Settings
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.costs.models import Calculation, BillRevision, Comparison

pytestmark=pytest.mark.integration

async def test_demo_seed_is_idempotent_and_keeps_missing_demand_explicit(costs_environment,costs_client,identity_settings,account_factory,session_factory,monkeypatch,tmp_path):
    directory=Path(__file__).parents[4]/'deploy/demo'
    monkeypatch.syspath_prepend(str(directory))
    spec=importlib.util.spec_from_file_location('costs_demo_preparation',directory/'prepare_costs.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'MARKER',tmp_path/'marker.json')
    module.MARKER.write_text('{"configuration_revision":1,"effective_from":"2025-01-01T00:00:00Z"}')
    monkeypatch.setenv('IDENTITY_CSRF_KEY',identity_settings.csrf_key.get_secret_value())
    monkeypatch.setenv('IDENTITY_LOGIN_BUCKET_KEY',identity_settings.login_bucket_key.get_secret_value())
    monkeypatch.setenv('IDENTITY_BUILDING_ID',str(UUID(int=99)))
    monkeypatch.setenv('IDENTITY_ENVIRONMENT','test')
    monkeypatch.setenv('IDENTITY_PUBLIC_URL','http://localhost:8000')
    monkeypatch.setenv('IDENTITY_DEVELOPMENT_HTTP','true')
    env=costs_environment
    from ecs_ec.consumption.catalog_storage import read_revisions
    from ecs_ec.consumption.configuration import ConfigurationService
    from ecs_ec.consumption.models import ConfigurationInput
    from ecs_ec.consumption.store import MeasurementStore
    sources={c['category_id']:UUID(c['source_id']) for c in module.channels()}
    async with UnitOfWork(env['database'].sessions) as uow:
        previous=(await read_revisions(uow,UUID(int=99)))[-1]
        entries=[c.model_dump(exclude={'category_revision'}) for c in previous.categories]
        for entry in entries:entry.update(source_id=sources[entry['category_id']],source_label='Demo test')
        await ConfigurationService(env['clock'],MeasurementStore()).apply(uow,building_id=UUID(int=99),
            request=ConfigurationInput(expected_revision=previous.revision,effective_from=None,timezone='America/Santiago',categories=entries),actor_ref='process:history_test')
        await uow.commit()
    await publish(env['reception'],[record(category_id=f'CAT-{i:02}',source_id=sources[f'CAT-{i:02}'],value=value)
        for i,value in enumerate(('1000','400','100','160','220','70','50'),1)])
    env['clock'].advance(7200)
    settings=Settings(_env_file=None,environment='local',demo_calendar=True,building_timezone='America/Santiago')
    async with UnitOfWork(env['database'].sessions) as uow:
        before=[(r.id,r.kind,r.energy_kwh) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]
    preview=await module.prepare_financial_demo(env['database'],env['clock'],settings,UUID(int=99))
    repeated=await module.prepare_financial_demo(env['database'],env['clock'],settings,UUID(int=99))
    assert preview['cycle']['comparison_status']=='available'
    assert preview['distribution']['state']=='available'
    assert repeated['cycle']['calculation']['id']==preview['cycle']['calculation']['id']
    from backend.tests.contract.costs.test_calculations_api import authenticate
    await authenticate(costs_client,account_factory,session_factory,identity_settings,'operador')
    response=await costs_client.get('/api/v1/costs/cycles')
    assert response.status_code==200,response.text
    assert response.json()['items'][0]['comparison_status']=='available'
    response=await costs_client.get('/api/v1/costs/calculations/'+preview['cycle']['calculation']['id']+'/distribution')
    assert response.status_code==200,response.text
    assert response.json()['state']=='available'
    assert response.json()['energy_amount']=='100000'
    async with UnitOfWork(env['database'].sessions) as uow:
        calculations=(await uow.session.scalars(select(Calculation))).all()
        assert len(calculations)==1 and calculations[0].complete_total is None
        assert calculations[0].sufficiency=='parcial'
        assert len((await uow.session.scalars(select(BillRevision))).all())==1
        assert len((await uow.session.scalars(select(Comparison))).all())==1
        assert [(r.id,r.kind,r.energy_kwh) for r in (await uow.session.scalars(select(IncorporatedRecord))).all()]==before
