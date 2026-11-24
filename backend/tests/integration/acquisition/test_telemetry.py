"""Actual007 emissions remain optional and cannot affect committed003/002 outcomes."""

import json
import pytest
from ecs_ec.observability.lifecycle import Telemetry, Policy
from backend.tests.integration.acquisition.test_recovery import service, sealed

pytestmark = pytest.mark.integration


async def test_real_emitter_and_unavailable_sink(
    acquisition_environment, tmp_path, monkeypatch
):
    """A safe ordinary terminal is emitted; a failing real adapter leaves accepted consumption unchanged."""
    env = acquisition_environment
    acquisition = service(env)
    telemetry = Telemetry(
        Policy(spool=tmp_path / "spool"), clock=env["clock"], autostart=False
    )
    acquisition.telemetry = telemetry
    try:
        publication = await sealed(env)
        outcome = await acquisition.process_sealed(publication)
        assert outcome["results"][0]["status"] == "accepted"
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        events = [json.loads(item) for item in payloads]
        terminals = [
            e
            for e in events
            if e["event"] == "operation.completed"
            and e["operation"] == "acquisition.process"
        ]
        assert len(terminals) == 1 and terminals[0]["outcome"] == "success"
        assert "modbus:" not in json.dumps(
            events
        ) and "SIMULATED-PAS600" not in json.dumps(events)

        def broken(*args, **kwargs):
            """Fail the actual technical adapter only; raw error text must never escape the producer."""
            raise RuntimeError("PRIVATE_TELEMETRY_MARKER")

        monkeypatch.setattr(telemetry, "begin", broken)
        assert await acquisition.process_sealed(publication) == outcome
        from backend.tests.integration.acquisition.test_recovery import native_bytes

        env["clock"].advance(900)
        payload = json.loads(native_bytes(108))
        series = payload["message"]["content"]["data"]["timeseries"][0]
        series["timestamp"] = "2026-01-01T00:15:00Z"
        series["records"][0]["v"] = 104
        next_publication = await sealed(env, json.dumps(payload).encode())
        next_outcome = await acquisition.process_sealed(next_publication)
        assert any(result["status"] == "accepted" for result in next_outcome["results"])
    finally:
        telemetry.shutdown()


async def test_real_listener_emits_one_safe_terminal(sftp_environment, tmp_path):
    """A real SFTP probe has one ordinary expected-rejection terminal and cannot fabricate a reception002 success."""
    import asyncssh
    from ecs_ec.acquisition.sftp_server import start_listener

    env = sftp_environment
    env["listener"].close()
    await env["listener"].wait_closed()
    telemetry = Telemetry(
        Policy(spool=tmp_path / "receiver-spool"), clock=env["clock"], autostart=False
    )
    settings = env["settings"].model_copy(
        update={
            "host_key_file": env["private"].parent / "host",
            "auth_file": env["private"].parent / "auth",
        }
    )
    listener = await start_listener(env["database"], env["clock"], settings, telemetry)
    host = asyncssh.read_private_key(settings.host_key_file)
    known = tmp_path / "receiver-known"
    known.write_bytes(
        f"[127.0.0.1]:{listener.get_port()} ".encode() + host.export_public_key()
    )
    try:
        async with asyncssh.connect(
            "127.0.0.1",
            listener.get_port(),
            username="pas600",
            client_keys=[str(env["private"])],
            known_hosts=str(known),
        ) as connection:
            sftp = await connection.start_sftp_client()
            async with sftp.open(".ecs-ec-probe", "xb") as stream:
                await stream.write("probe")
            await sftp.remove(".ecs-ec-probe")
            sftp.exit()
            await sftp.wait_closed()
        listener.close()
        await listener.wait_closed()
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        events = [json.loads(item) for item in payloads]
        terminals = [
            e
            for e in events
            if e["event"] == "operation.completed"
            and e["operation"] == "acquisition.receive"
        ]
        assert len(terminals) == 1 and terminals[0]["outcome"] == "expected_rejection"
        assert not any(e["event"] == "reception.completed" for e in events)
    finally:
        listener.close()
        await listener.wait_closed()
        telemetry.shutdown()


async def test_recovery_keeps_durable_context_and_does_not_emit_on_completed_read(
    acquisition_environment, tmp_path, monkeypatch
):
    """A new003 service recovers the same logical context; completed reads cannot fabricate processing."""
    from backend.tests.integration.consumption.test_history_telemetry import drain

    env = acquisition_environment
    acquisition = service(env)
    telemetry = Telemetry(
        Policy(spool=tmp_path / "recovery-spool"), clock=env["clock"], autostart=False
    )
    acquisition.telemetry = telemetry
    publication = await sealed(env)
    original = acquisition.reception.accept

    async def interrupted(*args, **kwargs):
        """Simulate a failure after durable adaptation but before002 incorporation."""
        raise RuntimeError("PRIVATE_NATIVE_FILENAME")

    monkeypatch.setattr(acquisition.reception, "accept", interrupted)
    try:
        with pytest.raises(RuntimeError):
            await acquisition.process_sealed(publication)
        monkeypatch.setattr(acquisition.reception, "accept", original)
        recovered = service(env)
        recovered.telemetry = telemetry
        recovered.reception.telemetry = telemetry
        outcome = await recovered.process_sealed(publication)
        assert outcome["results"][0]["status"] == "accepted"
        events = drain(telemetry)
        terminals = [
            e
            for e in events
            if e["operation"] == "acquisition.process"
            and e["event"] == "operation.completed"
        ]
        assert len(terminals) == 2
        assert terminals[0]["operation_ref"] == terminals[1]["operation_ref"]
        assert terminals[0]["execution_ref"] != terminals[1]["execution_ref"]
        assert terminals[1]["context_status"] == "recovered"
        reception = next(
            event for event in events if event["event"] == "reception.completed"
        )
        assert reception["parent_operation_ref"] == terminals[1]["operation_ref"]
        assert reception["publication_ref"] == terminals[1]["publication_ref"]
        assert reception["operation_ref"] != terminals[1]["operation_ref"]
        assert "PRIVATE_NATIVE_FILENAME" not in json.dumps(events)
        assert await recovered.process_sealed(publication) == outcome
        assert drain(telemetry) == []
    finally:
        telemetry.shutdown()


async def test_recovery_supervisor_failure_has_unavailable_context(
    acquisition_environment, tmp_path, monkeypatch
):
    """A failed coordinator poll is observable without inventing a publication and cancellation remains intact."""
    import asyncio
    from ecs_ec.acquisition.lifecycle import recovery_loop
    from backend.tests.integration.consumption.test_history_telemetry import drain

    env = acquisition_environment
    acquisition = service(env)
    telemetry = Telemetry(
        Policy(spool=tmp_path / "supervisor-spool"), clock=env["clock"], autostart=False
    )
    acquisition.telemetry = telemetry
    calls = 0

    async def interrupted():
        """Fail one poll before a durable context can be loaded, then exercise real loop cancellation."""
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("PRIVATE_COORDINATOR_DETAIL")
        raise asyncio.CancelledError()

    monkeypatch.setattr(acquisition, "recover", interrupted)
    try:
        with pytest.raises(asyncio.CancelledError):
            await recovery_loop(acquisition)
        events = drain(telemetry)
        terminal = next(
            event for event in events if event["event"] == "operation.completed"
        )
        assert (
            terminal["outcome"] == "unexpected_error"
            and terminal["context_status"] == "unavailable"
        )
        assert terminal["operation_ref"] is None and terminal["publication_ref"] is None
        assert not any(event["event"] == "reception.completed" for event in events)
        assert "PRIVATE_COORDINATOR_DETAIL" not in json.dumps(events)
    finally:
        telemetry.shutdown()
