"""Transport policy tests use known manifest hashes and virtual waits, never shortened acceptance cadence."""
import asyncio
from pathlib import Path
import pytest


def test_transport_rejects_inline_password_and_short_gap(tmp_path):
    """Deployment configuration cannot leak inline passwords or bypass the900second minimum."""
    from pas600_simulator.transport import TransportSettings
    base=dict(destination_alias='local',host='localhost',port=2222,directory='/',username='source',known_hosts_file=str(tmp_path/'known'),auth={'password_env':'TEST_PASSWORD'})
    with pytest.raises(ValueError):TransportSettings.model_validate(base|{'publication_gap_seconds':899})
    with pytest.raises(ValueError):TransportSettings.model_validate(base|{'auth':{'password':'SECRET'}})


def test_cadence_uses_monotonic_and_restart_full_wait(tmp_path):
    """A failed previous attempt and a forward UTC jump cannot shorten the deadline; restart waits again."""
    from pas600_simulator.transport import Cadence
    state=tmp_path/'state.json'
    clock=[10.0]
    cadence=Cadence(state,900,monotonic=lambda:clock[0])
    assert cadence.remaining()==0
    cadence.finished()
    clock[0]=909
    assert cadence.remaining()==1
    clock[0]=910
    assert cadence.remaining()==0
    restarted=Cadence(state,900,monotonic=lambda:clock[0])
    assert restarted.remaining()==900


@pytest.mark.parametrize('permanent,expected_attempts',[(False,3),(True,1)])
def test_retry_budget_and_persistent_resume(tmp_path,monkeypatch,permanent,expected_attempts):
    """Only unit waits are virtual: transient failures exhaust three attempts; permanent errors stop at one.

    A resumed exhausted run retains ordinals and cannot obtain a fourth attempt.
    """
    import json
    from contextlib import asynccontextmanager
    import pas600_simulator.transport as transport
    from pas600_simulator.report import generate_run
    from pas600_simulator.scenario import SimulationScenario
    root=tmp_path/'run';generate_run(SimulationScenario(end='2026-01-01T00:15:00Z'),root)
    settings=transport.TransportSettings(destination_alias='budget',host='localhost',username='source',known_hosts_file=tmp_path/'known',auth={'password_env':'TEST_PASSWORD'})
    @asynccontextmanager
    async def virtual_wait(*args):
        """Skip900s exclusively in this unit budget test; real_time acceptance uses the actual OS cadence."""
        cadence=transport.Cadence(tmp_path/'marker',900)
        monkeypatch.setattr(cadence,'remaining',lambda:0)
        yield cadence
    async def fail(settings,files,record):
        """Inject one classified transport failure after the attempt journal has been committed."""
        record['session_end']='aborted' if permanent else 'unknown'
        raise transport.TransferError('identity_rejected' if permanent else 'transport_unavailable',permanent)
    monkeypatch.setattr(transport,'destination_lock',virtual_wait)
    monkeypatch.setattr(transport,'transfer',fail)
    with pytest.raises(transport.TransferError):asyncio.run(transport.publish_run(root,settings))
    attempts=json.loads((root/'control/transfers.pending.json').read_text())['attempts']
    assert [a['ordinal'] for a in attempts]==list(range(1,expected_attempts+1))
    if not permanent:
        with pytest.raises(transport.TransferError,match='attempts_exhausted'):asyncio.run(transport.publish_run(root,settings,resume=True))
        assert len(json.loads((root/'control/transfers.pending.json').read_text())['attempts'])==3


def test_concurrent_publish_rereads_journal_after_run_lock(tmp_path,monkeypatch):
    """Two simultaneous callers cannot both act on the same stale empty journal or overwrite its first attempt."""
    import json
    import pas600_simulator.transport as transport
    from pas600_simulator.report import generate_run
    from pas600_simulator.scenario import SimulationScenario
    root=tmp_path/'run';generate_run(SimulationScenario(end='2026-01-01T00:15:00Z'),root)
    monkeypatch.setenv('PAS600_SIM_STATE_DIRECTORY',str(tmp_path/'cadence'))
    settings=transport.TransportSettings(destination_alias='concurrent',host='localhost',username='source',known_hosts_file=tmp_path/'known',auth={'password_env':'TEST_PASSWORD'})
    async def completed(settings,files,record):
        """Keep the actual OS journal lock occupied long enough for the second caller to contend."""
        await asyncio.sleep(.2)
        record.update(session_end='clean',publication_status='transferred')
    monkeypatch.setattr(transport,'transfer',completed)
    async def contenders():
        """Run two callers in one event loop with independent flock file descriptions."""
        return await asyncio.gather(transport.publish_run(root,settings),transport.publish_run(root,settings),return_exceptions=True)
    results=asyncio.run(contenders())
    assert sum(isinstance(r,transport.TransferError) and r.code=='resume_required' for r in results)==1
    assert len(json.loads((root/'control/transfers.pending.json').read_text())['attempts'])==1
