"""Selected003 restoration verifies existing009 tools plus native bytes; no production or shared database is modified."""
import asyncio,json,os,re,shutil,subprocess
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy import select
from ecs_ec.core.database import Database
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.acquisition.models import NativePublication,ReceivedFile,SftpSessionAttempt,PublicationEvaluation,NativeReading,IntervalCandidate
from ecs_ec.acquisition.staging import Staging
from backend.tests.integration.acquisition.test_recovery import sealed,service

pytestmark=[pytest.mark.integration,pytest.mark.restore]


async def test_database_and_native_volume_restore(acquisition_environment,tmp_path,test_url):
    """Restore manifest/bytes/results into an empty separate database; a missing sealed file cannot replace a prior valid export."""
    env=acquisition_environment
    container=os.environ.get('PAS600_RESTORE_CONTAINER','')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',container):raise pytest.UsageError('Explicit PAS600_RESTORE_CONTAINER is required')
    url=make_url(test_url);target='ecs003_'+uuid4().hex[:12]+'_restore'
    assert (url.database or '').endswith('_test') and target!=url.database
    publication=await sealed(env)
    outcome=await service(env).process_sealed(publication)
    interrupted=Staging(env['database'],env['clock'],env['settings'],env['binding']);await interrupted.start()
    handle=await interrupted.open('20260101003000000_1.json');await interrupted.write(handle,0,b'{pending');await interrupted.close(handle)
    interrupted.failed=True;assert await interrupted.finish() is None
    from backend.tests.integration.acquisition.test_recovery import native_bytes
    await sealed(env,native_bytes(108))  # Sealed, queued evidence stays pending across restore.
    async with UnitOfWork(env['database'].sessions) as uow:
        original_states={model.__tablename__:sorted((str(row.id),row.retain_until.isoformat(),getattr(row,'state',None)) for row in (await uow.session.scalars(select(model))).all())
            for model in (SftpSessionAttempt,ReceivedFile,PublicationEvaluation,NativeReading,IntervalCandidate)}
    archive=tmp_path/'database.dump'
    processes={**os.environ,'PG_CONTAINER':container,'PGDATABASE':url.database,'PGUSER':url.username,
        'PGPASSWORD':url.password,'PGHOST':'127.0.0.1','PGPORT':'5432'}
    async def command(args,environment=processes):
        """Run existing administration tools with credentials only in the environment, capturing fixed diagnostics."""
        process=await asyncio.create_subprocess_exec(*args,env=environment,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        output,error=await process.communicate()
        assert process.returncode==0,(process.returncode,error.decode())
        return output
    await command(['deploy/backup.sh',str(archive)])
    await command(['docker','exec',container,'createdb','-U',url.username,target])
    restored=None
    try:
        await command(['deploy/restore.sh',str(archive)],processes|{'PGDATABASE':target,'SOURCE_DATABASE':url.database})
        storage=tmp_path/'restored_bytes';shutil.copytree(env['settings'].storage,storage)
        target_url=url.set(database=target).render_as_string(hide_password=False)
        restored=Database(target_url)
        async with UnitOfWork(restored.sessions) as uow:
            row=await uow.session.get(NativePublication,publication)
            reference=row.publication_ref
            evaluation=(await uow.session.scalars(select(PublicationEvaluation).where(PublicationEvaluation.publication_id==publication))).one()
            file=(await uow.session.scalars(select(ReceivedFile).where(ReceivedFile.session_id==evaluation.session_id))).one()
            storage_key=file.storage_key
            for model in (SftpSessionAttempt,ReceivedFile,PublicationEvaluation,NativeReading,IntervalCandidate):
                assert sorted((str(row.id),row.retain_until.isoformat(),getattr(row,'state',None)) for row in (await uow.session.scalars(select(model))).all())==original_states[model.__tablename__]
        options={**os.environ,'ENVIRONMENT':'test','DATABASE_URL':target_url,'PAS600_STORAGE':str(storage),
            'PAS600_MAINTENANCE_PROCESSES':'process:test','PAS600_MAINTENANCE_PROCESS':'process:test'}
        output=tmp_path/'export.json'
        args=['.venv/bin/python','-m','ecs_ec.acquisition.cli','export-results','--publication-ref',reference,
            '--start','2025-12-31T21:00:00-03:00','--end','2025-12-31T21:15:00-03:00',
            '--timezone','America/Santiago','--categories','CAT-03','--view','detail','--output',str(output)]
        await command(args,options)
        snapshot=json.loads(output.read_text())
        assert snapshot['evaluations'][0]['outcome']==outcome
        assert snapshot['consumption_snapshot']['detail_results'][0]['rows'][0]['energy_kwh']=='4'
        previous=output.read_bytes()
        (storage/storage_key).unlink()
        process=await asyncio.create_subprocess_exec(*args,env=options,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        assert process.returncode==5 and output.read_bytes()==previous
        Path('/tmp/ecs003-restore-result.json').write_text(json.dumps(dict(restored=True,missing_bytes_detected=True,prior_export_preserved=True,aborted_and_pending_preserved=True,retention_preserved=True)))
    finally:
        if restored:await restored.close()
        await command(['docker','exec',container,'dropdb','-U',url.username,target])
