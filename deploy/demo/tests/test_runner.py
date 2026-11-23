"""Demo scenarios must append stable past-only intervals, including local midnight."""
from datetime import datetime, UTC
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runner import scenario
from pas600_simulator.generator import generate_samples


def test_growing_day_keeps_previous_values_and_never_generates_future():
    """A later publication must preserve the values already sent for the same day."""
    first = scenario(datetime(2026, 11, 3, 14, 7, 12, 123456, UTC), 'America/Santiago')
    later = scenario(datetime(2026, 11, 3, 14, 23, tzinfo=UTC), 'America/Santiago')
    old = {s.key: s.energy for s in generate_samples(first)}
    new = {s.key: s.energy for s in generate_samples(later)}
    assert old and old.items() <= new.items()
    assert later.end <= datetime(2026, 11, 3, 14, 23, tzinfo=UTC)
    assert all(c.meter.semantics == 'interval' for c in later.categories)


def test_midnight_waits_for_first_complete_interval():
    """Do not fabricate future measurements to populate an empty start of day."""
    assert scenario(datetime(2026, 11, 3, 3, 7, tzinfo=UTC), 'America/Santiago') is None
    data = scenario(datetime(2026, 11, 3, 3, 15, tzinfo=UTC), 'America/Santiago')
    assert len(list(generate_samples(data))) == 7


def test_transport_session_keeps_one_wait_and_recovers_external_attempts(tmp_path, monkeypatch):
    """Reentering in one process keeps the deadline; another process still forces safe recovery."""
    import asyncio
    from types import SimpleNamespace
    import pas600_simulator.transport as transport
    clock = [0]
    original = transport.Cadence
    monkeypatch.setattr(transport, 'Cadence', lambda path, gap: original(path, gap, monotonic=lambda: clock[0]))
    monkeypatch.setenv('PAS600_SIM_STATE_DIRECTORY', str(tmp_path))
    async def check():
        settings = SimpleNamespace(destination_alias='demo-test', publication_gap_seconds=900)
        session, stop = {}, asyncio.Event()
        async with transport.destination_lock(settings, 'publisher', stop, session) as cadence:
            assert cadence.remaining() == 0
            cadence.started()
            clock[0] = 20
            cadence.finished()
        clock[0] = 920
        async with transport.destination_lock(settings, 'publisher', stop, session) as cadence:
            assert cadence.remaining() == 0
            path = cadence.path
        path.write_text('{"state":"external"}')
        async with transport.destination_lock(settings, 'publisher', stop, session) as cadence:
            assert cadence.remaining() == 900
        async with transport.destination_lock(settings, 'publisher', stop) as cadence:
            assert cadence.remaining() == 900
    asyncio.run(check())


def test_startup_1820_and_incremental_1830_keep_exact_energy(tmp_path):
    """Initial catch-up ends at18:15; the18:30 run emits only18:15–18:30 with stable values."""
    import json
    from runner import next_boundary
    from pas600_simulator.report import generate_run
    from demo_profile import channels
    config = {'categories': [dict(c, has_meter=c['category_id'] != 'CAT-01') for c in channels()]}
    now = datetime(2026, 11, 3, 21, 20, tzinfo=UTC)
    first = scenario(now, 'America/Santiago', config)
    assert first.end.astimezone(UTC) == datetime(2026, 11, 3, 21, 15, tzinfo=UTC)
    assert next_boundary(now) == datetime(2026, 11, 3, 21, 30, tzinfo=UTC)
    later = scenario(next_boundary(now), 'America/Santiago', config)
    generate_run(later, tmp_path/'incremental', emit_from=first.end)
    rows = [json.loads(line) for line in (tmp_path/'incremental/control/expected.jsonl').read_text().splitlines()]
    expected = {s.key: str(s.energy) for s in generate_samples(later) if s.start >= first.end}
    assert len(rows) == 6
    assert {r['key']: r['energy'] for r in rows} == expected
    assert all(r['category_id'] != 'CAT-01' for r in rows)


def test_calendar_transport_is_local_only(monkeypatch, tmp_path):
    """The strict transport remains the default and calendar simulation refuses other environments."""
    import pytest
    from pydantic import ValidationError
    from pas600_simulator.transport import TransportSettings
    settings = dict(destination_alias='test', host='localhost', username='test',
        known_hosts_file=tmp_path/'known', auth={'password_env':'TEST_PASSWORD'}, local_calendar=True)
    monkeypatch.setenv('ENVIRONMENT', 'production')
    with pytest.raises(ValidationError):
        TransportSettings(**settings)
    monkeypatch.setenv('ENVIRONMENT', 'local')
    assert TransportSettings(**settings).local_calendar


def test_measured_general_is_independent_above_partial_bounds_and_preserves_partial_signals():
    from demo_profile import channels
    now=datetime(2026,11,4,2,45,tzinfo=UTC)
    calculated={'categories':[dict(c,has_meter=c['category_id']!='CAT-01') for c in channels()]}
    measured={'categories':[dict(c,has_meter=True) for c in channels()],'costs_demo':True}
    before={r.key:r.energy for r in generate_samples(scenario(now,'America/Santiago',calculated))}
    after=list(generate_samples(scenario(now,'America/Santiago',measured)))
    assert all(before[r.key]==r.energy for r in after if r.category_id!='CAT-01')
    totals={r.start:r.energy for r in after if r.category_id=='CAT-01'}
    for start,total in totals.items():
        assert total>sum(r.energy for r in after if r.start==start and r.category_id!='CAT-01')


def test_source_switch_skips_crossing_intervals_without_backdating_history():
    from runner import publication_start
    data=scenario(datetime(2026,11,4,2,45,tzinfo=UTC),'America/Santiago')
    config={'effective_from':'2026-11-04T02:28:14.146825+00:00'}
    assert publication_start(data,None,config)==datetime(2026,11,4,2,30,tzinfo=UTC)
    config['effective_from']='2026-11-04T02:30:00+00:00'
    assert publication_start(data,None,config)==datetime(2026,11,4,2,30,tzinfo=UTC)
    assert publication_start(data,datetime(2026,11,4,2,45,tzinfo=UTC),config)==data.end
