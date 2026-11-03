"""003 staging and binding isolation reject traversal, offsets, quotas and tampering without promoting partial bytes."""
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from ecs_ec.acquisition.staging import Staging
from ecs_ec.acquisition.models import NativePublication,PublicationEvaluation
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import sealed,service,native_bytes

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('name',['../file.json','/etc/passwd','a/../../20260101003000000_1.json','x\\20260101003000000_1.json','x\n_20260101003000000_1.json'])
async def test_invalid_paths_never_seal(acquisition_environment,name):
    """Every untrusted traversal/control path fails before filesystem allocation and irrevocably aborts the batch."""
    env=acquisition_environment
    stage=Staging(env['database'],env['clock'],env['settings'],env['binding'])
    await stage.start()
    with pytest.raises(ValueError):await stage.open(name)
    stage.clean_eof=True
    assert await stage.finish() is None


@pytest.mark.parametrize('condition',['offset','quota','open_handle','sequence'])
async def test_partial_bytes_never_promote(acquisition_environment,condition):
    """Wrong offsets, quotas, cleanup CLOSE and observable index gaps cannot be sealed even after EOF."""
    env=acquisition_environment
    options=env['settings'].model_copy(update={'max_json_bytes':4}) if condition=='quota' else env['settings']
    stage=Staging(env['database'],env['clock'],options,env['binding'])
    await stage.start()
    handle=await stage.open('20260101003000000_2.json' if condition=='sequence' else '20260101003000000_1.json')
    if condition in ('offset','quota'):
        with pytest.raises(ValueError):await stage.write(handle,1 if condition=='offset' else 0,b'12345')
        stage.cleanup=True;await stage.close(handle)
    elif condition=='open_handle':
        await stage.write(handle,0,b'{}')
        stage.cleanup=True;stage.failed=True;await stage.close(handle)
    else:
        await stage.write(handle,0,b'{}');await stage.close(handle)
    stage.clean_eof=True
    assert await stage.finish() is None


async def test_frozen_input_database_constraint_and_missing_bytes(acquisition_environment):
    """Prepared002 input is immutable in PostgreSQL, and a missing sealed payload is an error rather than an empty result."""
    env=acquisition_environment
    publication=await sealed(env)
    acquisition=service(env)
    evaluation,binding,_=await acquisition.prepare(publication)
    async with UnitOfWork(env['database'].sessions) as uow:
        row=await uow.session.get(PublicationEvaluation,evaluation.id)
        row.input_digest='0'*64
        with pytest.raises(DBAPIError):await uow.commit()
    # Same frozen input can still recover without reparsing, so test missing bytes on a new sealed evaluation.
    publication2=await sealed(env,native_bytes(105))
    for path in env['settings'].storage.glob('*/*'):
        if path.read_bytes()==native_bytes(105):path.unlink()
    with pytest.raises(ValueError,match='sealed_bytes_missing'):await acquisition.process_sealed(publication2)


@pytest.mark.parametrize('limit',['session_bytes','file_count','active_sessions','publisher'])
async def test_publisher_and_session_resource_limits(acquisition_environment,limit):
    """Enforce cumulative byte/file quotas and separate active-session/publisher-write exclusion before allocation."""
    env=acquisition_environment
    settings=env['settings'].model_copy(update={'max_session_bytes':3,'max_files':1})
    first=Staging(env['database'],env['clock'],settings,env['binding']);await first.start()
    second=None
    try:
        if limit=='active_sessions':
            second=Staging(env['database'],env['clock'],settings,env['binding']);await second.start()
            third=Staging(env['database'],env['clock'],settings,env['binding'])
            with pytest.raises(ValueError,match='resource_limit'):await third.start()
        else:
            handle=await first.open('20260101003000000_1.json');await first.write(handle,0,b'{}')
            if limit=='session_bytes':
                with pytest.raises(ValueError,match='resource_limit'):await first.write(handle,2,b'xx')
            elif limit=='file_count':
                await first.close(handle)
                with pytest.raises(ValueError,match='resource_limit'):await first.open('20260101003000000_2.json')
            else:
                second=Staging(env['database'],env['clock'],settings,env['binding']);await second.start()
                with pytest.raises(ValueError,match='publisher_busy'):await second.open('20260101003000000_1.json')
    finally:
        for stage in (first,second):
            if stage:
                stage.cleanup=True;stage.failed=True
                for handle in list(stage.handles.values()):await stage.close(handle)
                assert await stage.finish() is None


@pytest.mark.parametrize('boundary',['fsync','metadata_commit'])
async def test_failed_close_never_seals_durable_prefix(acquisition_environment,monkeypatch,boundary):
    """A failure before fsync or after it but before metadata commit leaves recoverable aborted bytes, never a publication."""
    import ecs_ec.acquisition.staging as staging
    env=acquisition_environment
    stage=Staging(env['database'],env['clock'],env['settings'],env['binding']);await stage.start()
    handle=await stage.open('20260101003000000_1.json');await stage.write(handle,0,native_bytes())
    target=staging.os if boundary=='fsync' else UnitOfWork
    name='fsync' if boundary=='fsync' else 'commit'
    original=getattr(target,name)
    def fail_fsync(*args):
        """Inject a storage failure before successful protocol CLOSE can be acknowledged."""
        raise OSError('synthetic_storage_failure')
    async def fail_commit(*args):
        """Inject a metadata failure after actual fsync but before its durable database transition."""
        raise OSError('synthetic_metadata_failure')
    monkeypatch.setattr(target,name,fail_fsync if boundary=='fsync' else fail_commit)
    with pytest.raises(OSError):await stage.close(handle)
    monkeypatch.setattr(target,name,original)
    stage.cleanup=True
    for opened in list(stage.handles.values()):await stage.close(opened)
    stage.clean_eof=True
    assert await stage.finish() is None
    assert any(path.read_bytes()==native_bytes() for path in env['settings'].storage.glob('*/*'))
