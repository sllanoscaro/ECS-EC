"""Standalone CLI contract: immutable run evidence, stop during real cadence wait, and safe diagnostics."""
import asyncio,json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
from pas600_simulator.report import generate_run
from pas600_simulator.scenario import SimulationScenario

CLI=str(Path(sys.executable).with_name('pas600-sim'))


def test_unknown_arguments_never_echo_credentials():
    """An accidental inline secret argument produces only a fixed argument error, not a credential transcript."""
    result=subprocess.run([CLI,'test-connection','--transport','/tmp/unused-config','--password','PRIVATE_MARKER'],capture_output=True,text=True)
    assert result.returncode==2 and 'PRIVATE_MARKER' not in result.stderr


def test_sigterm_preserves_bytes_and_wait_state(tmp_path,monkeypatch):
    """Stop while waiting for a previous attempt's900seconds, preserve all originals and return130 without networking."""
    from pas600_simulator.transport import TransportSettings,destination_lock
    import asyncssh
    scenario=SimulationScenario(end='2026-01-01T00:15:00Z')
    root=tmp_path/'run';manifest=generate_run(scenario,root)
    before={p.relative_to(root):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    known=tmp_path/'known';known.write_bytes(b'[127.0.0.1]:2222 '+asyncssh.generate_private_key('ssh-ed25519').export_public_key())
    values=dict(destination_alias='stopped',host='127.0.0.1',port=2222,directory='/',username='pas600',known_hosts_file=str(known),auth={'password_env':'PAS600_TEST_PASSWORD'})
    settings=TransportSettings.model_validate(values)
    monkeypatch.setenv('PAS600_SIM_STATE_DIRECTORY',str(tmp_path/'cadence'))
    async def previous_attempt():
        """Record one real completed-attempt marker so a restarted process must wait again."""
        async with destination_lock(settings,scenario.publisher.publisher_serial,asyncio.Event()) as cadence:cadence.finished()
    asyncio.run(previous_attempt())
    transport=tmp_path/'transport.json';transport.write_text(json.dumps(values))
    process=subprocess.Popen([CLI,'publish','--run',str(root),'--transport',str(transport)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    import fcntl
    locked=False
    try:
        for _ in range(300):
            with next((tmp_path/'cadence').glob('*.lock')).open('a+b') as lock:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:locked=True
            if locked:break
            time.sleep(.01)
        assert locked
        process.send_signal(signal.SIGTERM)
        output,errors=process.communicate(timeout=10)
        assert process.returncode==130,(output,errors)
        assert json.loads((root/'control/run.json').read_text())['state']=='stopped'
        assert {p.relative_to(root):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}==before
    finally:
        if process.poll() is None:process.kill();process.wait()


def test_tampered_native_is_evidence_error_before_connect(tmp_path):
    """A changed original fails with code5 before any host or credentials are contacted."""
    scenario=SimulationScenario(end='2026-01-01T00:15:00Z')
    root=tmp_path/'run';manifest=generate_run(scenario,root)
    native=next((root/'data').rglob('*.csv'));native.write_bytes(b'changed')
    transport=tmp_path/'transport.json';transport.write_text(json.dumps(dict(destination_alias='tampered',host='127.0.0.1',port=2222,directory='/',username='pas600',known_hosts_file=str(tmp_path/'unknown'),auth={'password_env':'UNSET_PRIVATE_MARKER'})))
    result=subprocess.run([CLI,'publish','--run',str(root),'--transport',str(transport)],capture_output=True,text=True)
    assert result.returncode==5 and 'UNSET_PRIVATE_MARKER' not in result.stderr
