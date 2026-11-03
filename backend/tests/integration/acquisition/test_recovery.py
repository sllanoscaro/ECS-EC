"""Real003 frozen input survives lost002 responses and concurrent recovery without duplicate incorporation."""
import json
from uuid import UUID
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.staging import Staging
from ecs_ec.acquisition.service import Acquisition
from ecs_ec.acquisition.models import PublicationEvaluation,NativePublication
from ecs_ec.consumption.reception import Reception
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark=pytest.mark.integration


def native_bytes(value=104):
    """Independent known100/104 reference, bound to synthetic source3 without any simulator import."""
    return json.dumps({'$schema':'ESX/EDM/Protocol/Specific/CloudMessaging/DeviceToCloud/Data/CewsMessage',
        'message':{'remoteId':'urn:dev:cer:1111111111111111111111111111111111111111','contentType':'data','cewsVersion':'3.0.0',
        'timestamp':'2026-01-01T00:30:00Z','content':{'data':{'timeseries':[{'valueItemId':'modbus:1_mb_EaImport3',
            'timestamp':'2026-01-01T00:00:00Z','records':[{'v':100,'t':0},{'v':value,'t':900000}]}]}}}}).encode()


async def sealed(env,data=None):
    """Stage explicit bytes with real fsync/close/EOF and return their publication identity."""
    stage=Staging(env['database'],env['clock'],env['settings'],env['binding'])
    await stage.start()
    handle=await stage.open('20260101003000000_1.json')
    await stage.write(handle,0,native_bytes() if data is None else data)
    await stage.close(handle)
    stage.clean_eof=True
    return await stage.finish()


def service(env):
    """Compose real002 with a trusted binding-specific process; no reception fake substitutes for acceptance."""
    process='process:acquisition:'+str(env['binding'].id)
    return Acquisition(env['database'],env['clock'],env['settings'],Reception(env['database'],env['clock'],authorized_processes={process:{env['binding'].building_id}}))


async def test_lost_response_recovers_frozen_attempt(acquisition_environment,monkeypatch):
    """Commit002 then lose its response: restart reads completed original, preserving ID/input and acceptance time."""
    env=acquisition_environment
    publication=await sealed(env)
    acquisition=service(env)
    original=acquisition.reception.accept
    async def lost(*args,**kwargs):
        """Lose only the transport response after the actual002 provider has committed."""
        await original(*args,**kwargs)
        raise RuntimeError('synthetic_lost_response')
    monkeypatch.setattr(acquisition.reception,'accept',lost)
    with pytest.raises(RuntimeError):await acquisition.process_sealed(publication)
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluation=(await uow.session.scalars(select(PublicationEvaluation))).one()
        attempt,records=evaluation.attempt_id,evaluation.input_records
    recovered=await service(env).process_sealed(publication)
    assert recovered['state']=='completed' and recovered['attempt_id']==str(attempt)
    assert recovered['results'][0]['status']=='accepted'
    assert recovered['results'][0]['measurement_id']
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluation=(await uow.session.scalars(select(PublicationEvaluation))).one()
        assert evaluation.input_records==records and evaluation.state=='completed'
    assert await service(env).process_sealed(publication)==recovered


async def test_same_native_retransmission_new_attempt(acquisition_environment):
    """Same exact manifest shares publication identity but an explicit new session creates a new002 evaluation."""
    import asyncio
    env=acquisition_environment
    publication=await sealed(env)
    first=await service(env).process_sealed(publication)
    assert first['results'][0]['status']=='accepted'
    assert await sealed(env)==publication
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluations=(await uow.session.scalars(select(PublicationEvaluation).where(PublicationEvaluation.state=='pending'))).all()
        identifier=evaluations[0].id
    results=await asyncio.gather(service(env).process_sealed(publication,identifier),service(env).process_sealed(publication,identifier))
    assert results[0]==results[1]
    assert results[0]['attempt_id']!=first['attempt_id'] and results[0]['results'][0]['status']=='duplicate'


async def test_payload_conflict_conflicting_reading_and_revision(acquisition_environment):
    """002 rejects changing a frozen ID; first valid003 reading survives conflict and a new descriptor has separate identity."""
    from ecs_ec.acquisition.config import install_binding
    from ecs_ec.acquisition.models import NativeReading,IntervalCandidate
    env=acquisition_environment;acquisition=service(env)
    publication=await sealed(env);first=await acquisition.process_sealed(publication)
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluation=(await uow.session.scalars(select(PublicationEvaluation))).one()
        changed=[dict(r,value='5') for r in evaluation.input_records]
        attempt=evaluation.attempt_id
    with pytest.raises(ValueError,match='attempt_payload_conflict'):
        await acquisition.reception.accept(attempt,env['binding'].building_id,'changed','process:acquisition:'+str(env['binding'].id),changed,'acquisition:changed')
    assert await acquisition.process_sealed(publication)==first
    await acquisition.process_sealed(await sealed(env,native_bytes(105)))
    async with UnitOfWork(env['database'].sessions) as uow:
        assert len((await uow.session.scalars(select(NativeReading).where(NativeReading.state=='conflict'))).all())==1
        assert [r.energy for r in (await uow.session.scalars(select(IntervalCandidate))).all()]==[4]
    data=env['binding'].model_dump(mode='json');data['revision']=2
    revision=await install_binding(env['database'],env['clock'],env['settings'],'process:test',data)
    revised=dict(env,binding=revision)
    await service(revised).process_sealed(await sealed(revised))
    async with UnitOfWork(env['database'].sessions) as uow:
        assert {r.binding_revision for r in (await uow.session.scalars(select(IntervalCandidate))).all()}=={1,2}


async def test_dependent_retention_protects_prior_file(acquisition_environment):
    """Later duplicate evidence extends all original endpoint dependencies, while direct deletion is FK-protected."""
    from sqlalchemy import delete
    from sqlalchemy.exc import DBAPIError
    from ecs_ec.acquisition.models import ReceivedFile,NativeReading,IntervalCandidate,SftpSessionAttempt
    env=acquisition_environment;acquisition=service(env)
    publication=await sealed(env);await acquisition.process_sealed(publication)
    env['clock'].advance(86400*400)
    await sealed(env);await acquisition.recover()
    async with UnitOfWork(env['database'].sessions) as uow:
        candidate=(await uow.session.scalars(select(IntervalCandidate))).one()
        reading=await uow.session.get(NativeReading,candidate.first_reading_id)
        file=await uow.session.get(ReceivedFile,reading.file_id)
        session=await uow.session.get(SftpSessionAttempt,file.session_id)
        assert file.retain_until>=candidate.retain_until and session.retain_until>=candidate.retain_until
        with pytest.raises(DBAPIError):
            await uow.session.execute(delete(ReceivedFile).where(ReceivedFile.id==file.id));await uow.commit()
