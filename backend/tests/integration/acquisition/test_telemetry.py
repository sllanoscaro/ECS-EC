"""Actual007 emissions remain optional and cannot affect committed003/002 outcomes."""
import json
import pytest
from ecs_ec.observability.lifecycle import Telemetry,Policy
from backend.tests.integration.acquisition.test_recovery import service,sealed

pytestmark=pytest.mark.integration


async def test_real_emitter_and_unavailable_sink(acquisition_environment,tmp_path,monkeypatch):
    """A safe ordinary terminal is emitted; a failing real adapter leaves accepted consumption unchanged."""
    env=acquisition_environment;acquisition=service(env)
    telemetry=Telemetry(Policy(spool=tmp_path/'spool'),clock=env['clock'],autostart=False)
    acquisition.telemetry=telemetry
    try:
        publication=await sealed(env)
        outcome=await acquisition.process_sealed(publication)
        assert outcome['results'][0]['status']=='accepted'
        payloads=[];telemetry.logs._writer=payloads.append
        while telemetry.logs.drain_one():pass
        events=[json.loads(item) for item in payloads]
        terminals=[e for e in events if e['event']=='operation.completed' and e['operation']=='acquisition.process']
        assert len(terminals)==1 and terminals[0]['outcome']=='success'
        assert 'modbus:' not in json.dumps(events) and 'SIMULATED-PAS600' not in json.dumps(events)
        def broken(*args,**kwargs):
            """Fail the actual technical adapter only; raw error text must never escape the producer."""
            raise RuntimeError('PRIVATE_TELEMETRY_MARKER')
        monkeypatch.setattr(telemetry,'begin',broken)
        assert await acquisition.process_sealed(publication)==outcome
    finally:telemetry.shutdown()


async def test_real_listener_emits_one_safe_terminal(sftp_environment,tmp_path):
    """A real SFTP probe has one ordinary expected-rejection terminal and cannot fabricate a reception002 success."""
    import asyncssh
    from ecs_ec.acquisition.sftp_server import start_listener
    env=sftp_environment;env['listener'].close();await env['listener'].wait_closed()
    telemetry=Telemetry(Policy(spool=tmp_path/'receiver-spool'),clock=env['clock'],autostart=False)
    settings=env['settings'].model_copy(update={'host_key_file':env['private'].parent/'host','auth_file':env['private'].parent/'auth'})
    listener=await start_listener(env['database'],env['clock'],settings,telemetry)
    host=asyncssh.read_private_key(settings.host_key_file)
    known=tmp_path/'receiver-known';known.write_bytes(f'[127.0.0.1]:{listener.get_port()} '.encode()+host.export_public_key())
    try:
        async with asyncssh.connect('127.0.0.1',listener.get_port(),username='pas600',client_keys=[str(env['private'])],known_hosts=str(known)) as connection:
            sftp=await connection.start_sftp_client()
            async with sftp.open('.ecs-ec-probe','xb') as stream:await stream.write('probe')
            await sftp.remove('.ecs-ec-probe');sftp.exit();await sftp.wait_closed()
        listener.close();await listener.wait_closed()
        payloads=[];telemetry.logs._writer=payloads.append
        while telemetry.logs.drain_one():pass
        events=[json.loads(item) for item in payloads]
        terminals=[e for e in events if e['event']=='operation.completed' and e['operation']=='acquisition.receive']
        assert len(terminals)==1 and terminals[0]['outcome']=='expected_rejection'
        assert not any(e['event']=='reception.completed' for e in events)
    finally:
        listener.close();await listener.wait_closed();telemetry.shutdown()
