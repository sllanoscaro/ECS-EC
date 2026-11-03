"""003 diagnoses corrupt native evidence while preserving independent valid files, first-valid readings and late adjacent pairs."""
import json
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.staging import Staging
from ecs_ec.acquisition.models import NativeReading,AdaptationResult,PublicationEvaluation
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import native_bytes,service,sealed

pytestmark=pytest.mark.integration


async def test_unreadable_file_does_not_discard_other_valid_file(acquisition_environment):
    """One sealed batch can contain an unreadable native file and a separately accepted4kWh interval."""
    env=acquisition_environment
    stage=Staging(env['database'],env['clock'],env['settings'],env['binding'])
    await stage.start()
    for index,data in ((1,native_bytes()),(2,b'{broken')):
        handle=await stage.open(f'20260101003000000_{index}.json')
        await stage.write(handle,0,data);await stage.close(handle)
    stage.clean_eof=True
    result=await service(env).process_sealed(await stage.finish())
    assert result['results'][0]['status']=='accepted'
    async with UnitOfWork(env['database'].sessions) as uow:
        rows=(await uow.session.scalars(select(AdaptationResult))).all()
        assert any(r.scope=='file' and r.reason=='file_unreadable' for r in rows)
        assert any(r.status=='candidate' for r in rows)


async def test_invalid_observation_does_not_reserve_canonical_identity(acquisition_environment):
    """A later correction fills only adjacent pairs; no earlier gap was silently bridged into8kWh."""
    env=acquisition_environment
    data=json.loads(native_bytes())
    records=data['message']['content']['data']['timeseries'][0]['records']
    records[1]['v']='invalid-value';records.append({'v':108,'t':1800000})
    publication=await sealed(env,json.dumps(data).encode())
    assert await service(env).process_sealed(publication) is None
    async with UnitOfWork(env['database'].sessions) as uow:
        row=(await uow.session.scalars(select(PublicationEvaluation))).one()
        assert row.attempt_id is None
    records[1]['v']=104
    result=await service(env).process_sealed(await sealed(env,json.dumps(data).encode()))
    assert len(result['results'])==2 and all(r['status']=='accepted' for r in result['results'])
    async with UnitOfWork(env['database'].sessions) as uow:
        invalid=(await uow.session.scalars(select(NativeReading).where(NativeReading.state=='invalid'))).all()
        assert len(invalid)==1 and invalid[0].canonical_key is None


async def test_confirmed_too_early_requires_new_resend(acquisition_environment):
    """Recovery preserves a completed timing rejection; only another explicit sealed session creates a fresh attempt."""
    env=acquisition_environment;acquisition=service(env)
    await acquisition.process_sealed(await sealed(env))
    data=json.loads(native_bytes())
    series=data['message']['content']['data']['timeseries'][0]
    series['records']=[{'v':104,'t':900000},{'v':108,'t':1800000}]
    second=await sealed(env,json.dumps(data).encode())
    rejected=await acquisition.process_sealed(second)
    assert any(r['reason_code']=='too_early' for r in rejected['results'])
    env['clock'].advance(900)
    assert await acquisition.process_sealed(second)==rejected
    assert await sealed(env,json.dumps(data).encode())==second
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluation=(await uow.session.scalars(select(PublicationEvaluation).where(PublicationEvaluation.publication_id==second,PublicationEvaluation.state=='pending'))).one()
        identifier=evaluation.id
    accepted=await acquisition.process_sealed(second,identifier)
    assert accepted['attempt_id']!=rejected['attempt_id']
    assert any(r['status']=='accepted' for r in accepted['results'])
