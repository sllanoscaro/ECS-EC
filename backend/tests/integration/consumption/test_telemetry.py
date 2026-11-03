"""001 HTTP operations emit safe terminals through the actual007 emitter."""
import json
import pytest
from backend.tests.contract.consumption.test_http import authenticate
from backend.tests.integration.consumption.test_detail_queries import facade
from ecs_ec.observability.lifecycle import Telemetry, Policy

pytestmark = pytest.mark.integration


async def test_detail_terminals_and_sensitive_input_isolation(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, tmp_path):
    """Success/rejection correlate to the trusted request; raw query values never enter logs."""
    app = client._transport.app
    app.state.consumption = facade(database, clock)
    telemetry = Telemetry(Policy(spool=tmp_path), clock=clock, autostart=False)
    app.state.telemetry = telemetry
    await authenticate(client, account_factory, session_factory, identity_settings)
    try:
        for start, expected in [('2025-12-31T21:00:00-03:00', 200), ('PRIVATE_QUERY_MARKER', 422)]:
            response = await client.get('/api/v1/consumption/categories/CAT-05/detail', params={
                'start': start, 'end': '2025-12-31T22:00:00-03:00', 'timezone': 'America/Santiago'})
            assert response.status_code == expected
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        events = [json.loads(item) for item in payloads]
        terminals = [e for e in events if e['event'] == 'operation.completed']
        assert [e['outcome'] for e in terminals] == ['success', 'expected_rejection']
        assert all(e['operation'] == 'consumption.query_detail' and e['operation_ref'] for e in terminals)
        assert len({e['operation_ref'] for e in terminals}) == 2
        assert 'PRIVATE_QUERY_MARKER' not in json.dumps(events)
    finally:
        telemetry.shutdown()


async def test_technical_failure_does_not_change_detail(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, monkeypatch):
    """Failure of the actual007 adapter leaves functional GET and its response unchanged."""
    telemetry = Telemetry()
    def fail(*args, **kwargs):
        """Model an internal transport failure without allowing its secret text to escape."""
        raise RuntimeError('PRIVATE_TELEMETRY_FAILURE')
    monkeypatch.setattr(telemetry, 'begin', fail)
    app = client._transport.app
    app.state.telemetry = telemetry
    app.state.consumption = facade(database, clock)
    await authenticate(client, account_factory, session_factory, identity_settings)
    response = await client.get('/api/v1/consumption/categories/CAT-05/detail', params={
        'start': '2025-12-31T21:00:00-03:00', 'end': '2025-12-31T22:00:00-03:00', 'timezone': 'America/Santiago'})
    assert response.status_code == 200 and response.json()['state'] == 'no_data'
    assert 'PRIVATE_' not in response.text


async def test_configuration_commit_and_saturated_queue(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, tmp_path):
    """Administration succeeds with a saturated real007 queue; technical losses are observable."""
    app = client._transport.app
    app.state.consumption = facade(database, clock)
    telemetry = Telemetry(Policy(spool=tmp_path), clock=clock, autostart=False)
    app.state.telemetry = telemetry
    headers = await authenticate(client, account_factory, session_factory, identity_settings, role='administrador_tecnico')
    try:
        current = (await client.get('/api/v1/consumption/configuration')).json()
        for _ in range(1030):
            handle = telemetry.begin('consumption.query_detail', 'consumption')
            telemetry.complete(handle)
        command = dict(expected_revision=current['revision'], effective_from=None, timezone=current['timezone'],
            categories=[{k:v for k,v in c.items() if k != 'category_revision'} for c in current['categories']])
        command['categories'][4]['source_label'] = 'PRIVATE_LABEL_MARKER'
        response = await client.put('/api/v1/consumption/configuration', json=command, headers=headers)
        assert response.status_code == 200
        assert response.json()['categories'][4]['source_label'] == 'PRIVATE_LABEL_MARKER'
        assert telemetry.logs.dropped > 0 and telemetry.logs.depth <= 1024
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        assert b'PRIVATE_LABEL_MARKER' not in b''.join(payloads)
    finally:
        telemetry.shutdown()
