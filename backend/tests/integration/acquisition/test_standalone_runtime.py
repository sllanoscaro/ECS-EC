"""Installed --no-dev simulator probes and publishes over verified real SFTP without backend runtime imports."""
import asyncio,json,os
from pathlib import Path
import pytest
from sqlalchemy import select,func
from ecs_ec.acquisition.models import NativePublication,PublicationEvaluation
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_compare_pipeline import pipeline

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('mode',['password','key'])
async def test_runtime_probe_publish_and_duplicates(sftp_environment,tmp_path,mode):
    """Both externally provisioned auth modes work in an isolated runtime-only environment; probe never adds measurements."""
    env=sftp_environment
    run,acquisition,reference=await pipeline(env,tmp_path)
    configuration=dict(destination_alias='runtime-'+mode,host='127.0.0.1',port=env['port'],directory='/',username='pas600',
        known_hosts_file=str(env['known']),auth={'password_env':'PAS600_RUNTIME_PASSWORD'} if mode=='password' else {'private_key_file':str(env['private'])})
    transport=tmp_path/'transport.json';transport.write_text(json.dumps(configuration))
    environment={**os.environ,'UV_PROJECT_ENVIRONMENT':str(tmp_path/'runtime-env'),'PAS600_SIM_STATE_DIRECTORY':str(tmp_path/'cadence'),'PAS600_RUNTIME_PASSWORD':'Synthetic password003'}
    async def command(*args):
        """Run uv against the independent lock; private credentials remain env-only and child errors stay captured."""
        process=await asyncio.create_subprocess_exec('uv','run','--project','tools/pas600_simulator','--locked','--no-dev',*args,
            env=environment,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        output,error=await process.communicate()
        assert process.returncode==0,(process.returncode,error.decode())
        return output
    await command('python','-c',"import importlib.util; assert importlib.util.find_spec('pytest') is None; assert importlib.util.find_spec('ecs_ec') is None")
    await command('pas600-sim','validate','--scenario','tools/pas600_simulator/examples/seven-meters.json')
    await command('pas600-sim','generate','--scenario','tools/pas600_simulator/examples/seven-meters.json','--format','json','--output',str(tmp_path/'runtime-generated'))
    await command('pas600-sim','test-connection','--transport',str(transport))
    async with UnitOfWork(env['database'].sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(NativePublication))==1
    await command('pas600-sim','publish','--run',str(run),'--transport',str(transport))
    await acquisition.recover()
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluations=(await uow.session.scalars(select(PublicationEvaluation))).all()
        assert len(evaluations)==2
        assert sorted(e.outcome['results'][0]['status'] for e in evaluations)==['accepted','duplicate']
