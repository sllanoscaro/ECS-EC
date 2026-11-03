"""Real standalone process signals during SFTP do not start another cycle or lose immutable transfer evidence."""
import asyncio,json,os,signal
from pathlib import Path
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.models import PublicationEvaluation
from ecs_ec.acquisition.sftp_server import VirtualFiles
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import service

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('boundary,stop_signal',[('write',signal.SIGTERM),('close',signal.SIGINT)])
async def test_signal_finishes_current_only(sftp_environment,tmp_path,monkeypatch,boundary,stop_signal):
    """A signal while WRITE or after server CLOSE cooperatively finishes that bounded attempt and returns130."""
    env=sftp_environment
    scenario=json.loads(Path('tools/pas600_simulator/examples/seven-meters.json').read_text())
    scenario.update(start='2026-01-01T00:00:00Z',end='2026-01-01T00:30:00Z',samples_per_publication=1,format='json')
    scenario['publisher'].update(publisher_serial=env['binding'].publisher_serial,publisher_remote_id=env['binding'].publisher_remote_id)
    for category,channel in zip(scenario['categories'],env['binding'].channels):
        category['meter'].update(device_local_id=channel.device_local_id,reduced_id=channel.reduced_id,device_name=channel.device_name,
            csv_topic_id=channel.csv_topic_id,json_value_item_id=channel.json_value_item_id)
    configuration=tmp_path/'scenario.json';configuration.write_text(json.dumps(scenario));run=tmp_path/'run'
    generate=await asyncio.create_subprocess_exec('tools/pas600_simulator/.venv/bin/pas600-sim','generate','--scenario',str(configuration),'--output',str(run),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    await generate.communicate();assert generate.returncode==0
    originals={p.relative_to(run):p.read_bytes() for p in (run/'data').rglob('*.json')}
    transport=tmp_path/'transport.json';transport.write_text(json.dumps(dict(destination_alias='stop-'+boundary,host='127.0.0.1',port=env['port'],
        username='pas600',known_hosts_file=str(env['known']),auth={'private_key_file':str(env['private'])})))
    method=getattr(VirtualFiles,boundary);sent=False;child=None
    async def interrupted(server,*args):
        """Deliver a real POSIX signal at the selected server boundary while retaining normal SFTP completion."""
        nonlocal sent
        result=await method(server,*args)
        if not sent:
            sent=True;child.send_signal(stop_signal);await asyncio.sleep(.1)
        return result
    monkeypatch.setattr(VirtualFiles,boundary,interrupted)
    child=await asyncio.create_subprocess_exec('tools/pas600_simulator/.venv/bin/pas600-sim','publish','--run',str(run),'--transport',str(transport),
        env={**os.environ,'PAS600_SIM_STATE_DIRECTORY':str(tmp_path/'cadence')},stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try:
        output,error=await asyncio.wait_for(child.communicate(),15)
        assert sent and child.returncode==130,(output,error)
        attempts=json.loads((run/'control/transfers.pending.json').read_text())['attempts']
        assert len(attempts)==1 and attempts[0]['session_end']=='clean'
        assert json.loads((run/'control/run.json').read_text())['state']=='stopped'
        assert {p.relative_to(run):p.read_bytes() for p in (run/'data').rglob('*.json')}==originals
        await service(env).recover()
        async with UnitOfWork(env['database'].sessions) as uow:
            evaluations=(await uow.session.scalars(select(PublicationEvaluation))).all()
            assert len(evaluations)==1 and evaluations[0].state=='completed'
    finally:
        if child.returncode is None:child.kill();await child.communicate()
