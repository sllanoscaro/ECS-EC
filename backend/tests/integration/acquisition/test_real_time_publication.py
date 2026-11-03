"""Selected long acceptance measures actual SSH attempts900seconds apart, with real002 consumption."""
import asyncio
from datetime import UTC,datetime
import hashlib,json,os
from pathlib import Path
import pytest
import asyncssh
from argon2 import PasswordHasher
from sqlalchemy import select
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.acquisition.models import PublicationEvaluation
from ecs_ec.acquisition.sftp_server import start_listener
from backend.tests.integration.acquisition.test_recovery import service

pytestmark=[pytest.mark.integration,pytest.mark.real_time]


@pytest.mark.parametrize('mode',['cycles','retry'])
async def test_real_gap_and_consumption(acquisition_environment,tmp_path,monkeypatch,mode):
    """Publish two actual generated native cycles; full900second monotonic wait cannot be shortened by test settings."""
    env=dict(acquisition_environment)
    env['clock']=SystemClock()
    key=asyncssh.generate_private_key('ssh-ed25519')
    host=tmp_path/'host';key.write_private_key(host);host.chmod(0o600)
    password='Synthetic transport password003'
    auth=tmp_path/'auth';auth.write_text(json.dumps({'pas600':{'password_hash':PasswordHasher().hash(password)}}));auth.chmod(0o600)
    settings=env['settings'].model_copy(update={'host_key_file':host,'auth_file':auth})
    listener=await start_listener(env['database'],env['clock'],settings)
    known=tmp_path/'known';known.write_bytes(f'[127.0.0.1]:{listener.get_port()} '.encode()+key.export_public_key())
    transport=tmp_path/'transport.json';transport.write_text(json.dumps(dict(destination_alias='real-time003',host='127.0.0.1',port=listener.get_port(),
        directory='/',username='pas600',known_hosts_file=str(known),auth={'password_env':'PAS600_TEST_PASSWORD'},publication_gap_seconds=900,max_attempts=3)))
    scenario=json.loads(Path('tools/pas600_simulator/examples/seven-meters.json').read_text())
    scenario.update(start='2026-01-01T00:00:00Z',end='2026-01-01T00:30:00Z',samples_per_publication=1,format='json')
    for category,channel in zip(scenario['categories'],env['binding'].channels):
        category['meter'].update(device_local_id=channel.device_local_id,reduced_id=channel.reduced_id,
            device_name=channel.device_name,csv_topic_id=channel.csv_topic_id,json_value_item_id=channel.json_value_item_id)
    scenario['publisher'].update(publisher_serial=env['binding'].publisher_serial,publisher_remote_id=env['binding'].publisher_remote_id)
    scenario_path=tmp_path/'scenario.json';scenario_path.write_text(json.dumps(scenario))
    run=tmp_path/'run'
    subprocess_env={**os.environ,'PAS600_TEST_PASSWORD':password,'PAS600_SIM_STATE_DIRECTORY':str(tmp_path/'cadence')}
    async def command(*args):
        """Run the standalone installed CLI with protected external credentials, no backend imports or public fixture routes."""
        process=await asyncio.create_subprocess_exec('tools/pas600_simulator/.venv/bin/pas600-sim',*args,
            env=subprocess_env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        output,errors=await process.communicate()
        assert process.returncode==0,(process.returncode,errors.decode())
        return output
    if mode=='retry':
        from ecs_ec.acquisition.sftp_server import VirtualFiles
        original_write=VirtualFiles.write
        failed=[False]
        async def interrupted_write(server,*args):
            """Interrupt one real SSH connection after durable bytes and a measurable slow transfer prefix."""
            await original_write(server,*args)
            if not failed[0]:
                failed[0]=True
                await asyncio.sleep(.25)
                server._chan.get_connection().abort()
        monkeypatch.setattr(VirtualFiles,'write',interrupted_write)
        scenario['samples_per_publication']=2
        scenario_path.write_text(json.dumps(scenario))
    acquisition=service(env)
    errors=[];stop=asyncio.Event()
    async def worker():
        """Exercise the actual in-process003 recoverer while real transport waits between cycles."""
        while not stop.is_set():
            try:await acquisition.recover()
            except Exception as error:errors.append(type(error).__name__)
            try:await asyncio.wait_for(stop.wait(),.1)
            except TimeoutError:pass
    task=asyncio.create_task(worker())
    try:
        await command('generate','--scenario',str(scenario_path),'--output',str(run),'--format','json')
        await command('publish','--run',str(run),'--transport',str(transport))
        for _ in range(100):
            await acquisition.recover()
            async with UnitOfWork(env['database'].sessions) as uow:
                rows=(await uow.session.scalars(select(PublicationEvaluation).order_by(PublicationEvaluation.recorded_at))).all()
                outcomes=[r.outcome for r in rows]
            if len(outcomes)==(2 if mode=='cycles' else 1) and all(outcomes):break
            await asyncio.sleep(.1)
        attempts=[json.loads(line) for line in (run/'control/transfers.jsonl').read_text().splitlines()]
        assert len(attempts)==2 and attempts[-1]['session_end']=='clean'
        if mode=='retry':assert attempts[0]['publication_status']=='uncertain' and attempts[0]['duration_seconds']>=.25
        gap=(datetime.fromisoformat(attempts[1]['started_at'])-datetime.fromisoformat(attempts[0]['ended_at'])).total_seconds()
        assert gap>=900 and not errors
        assert len(outcomes)==(2 if mode=='cycles' else 1) and all(o['state']=='completed' for o in outcomes)
        assert all(any(r['status']=='accepted' for r in o['results']) for o in outcomes)
        evidence=dict(gap_seconds=gap,attempts=attempts,outcomes=outcomes)
        Path('/tmp/ecs003-real-time-'+mode+'-result.json').write_text(json.dumps(evidence))
        print(json.dumps({'real_gap_seconds':gap,'evaluations':len(outcomes)}))
    finally:
        stop.set();await task
        listener.close();await listener.wait_closed()
