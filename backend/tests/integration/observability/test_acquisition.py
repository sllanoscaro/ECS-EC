"""007 consumes installed001/002/003 adapters and durable outcomes, never emits on their behalf."""

import json
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.models import NativePublication
from ecs_ec.acquisition.sftp_server import start_listener
from ecs_ec.observability.lifecycle import Policy, Telemetry
from backend.tests.integration.acquisition.conftest import (
    acquisition_environment as acquisition_environment,
    sftp_environment as sftp_environment,
)  # noqa: F401
from backend.tests.integration.acquisition.test_recovery import (
    service,
    sealed,
    native_bytes,
)
from backend.tests.integration.consumption.test_history_telemetry import (
    drain,
    test_partial_execution_recovery_and_logical_terminal as test_partial_execution_recovery_and_logical_terminal,
    test_early_retention_and_aggregate_signals_are_safe as test_early_retention_and_aggregate_signals_are_safe,
    test_pending_calculation_uses_real_emitter as test_pending_calculation_uses_real_emitter,
)
from backend.tests.integration.acquisition.test_telemetry import (
    test_recovery_keeps_durable_context_and_does_not_emit_on_completed_read as test_recovery_keeps_durable_context_and_does_not_emit_on_completed_read,
    test_recovery_supervisor_failure_has_unavailable_context as test_recovery_supervisor_failure_has_unavailable_context,
)

pytestmark = pytest.mark.integration


async def test_real_sftp_clean_and_aborted_with_queryable_spans(
    sftp_environment, tmp_path
):
    """Actual SFTP EOF/abort, adaptation and002 incorporation have matching safe log/span outcomes."""
    import asyncio
    import asyncssh

    env = sftp_environment
    env["listener"].close()
    await env["listener"].wait_closed()
    settings = env["settings"].model_copy(
        update={
            "host_key_file": env["private"].parent / "host",
            "auth_file": env["private"].parent / "auth",
        }
    )
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "transport"),
        clock=env["clock"],
        autostart=False,
    )
    listener = await start_listener(env["database"], env["clock"], settings, telemetry)
    known = tmp_path / "known-current"
    known.write_bytes(
        f"[127.0.0.1]:{listener.get_port()} ".encode()
        + asyncssh.read_private_key(settings.host_key_file).export_public_key()
    )
    try:
        for clean in (True, False):
            connection = await asyncssh.connect(
                "127.0.0.1",
                listener.get_port(),
                username="pas600",
                client_keys=[str(env["private"])],
                known_hosts=str(known),
            )
            sftp = await connection.start_sftp_client()
            stream = await sftp.open("20260101003000000_1.json", "xb", encoding=None)
            await stream.write(native_bytes())
            if clean:
                await stream.close()
                sftp.exit()
                await sftp.wait_closed()
                connection.close()
                await connection.wait_closed()
            else:
                connection.abort()
                await connection.wait_closed()
        # Wait for the real asynchronous server cleanup, never synthesize its terminal.
        for _ in range(100):
            if len(telemetry.traces._queue) >= 8:
                break
            await asyncio.sleep(0.01)
        async with env["database"].sessions() as session:
            publication = (await session.scalars(select(NativePublication))).one()
            publication_id = publication.id
        acquisition = service(env)
        acquisition.telemetry = acquisition.reception.telemetry = telemetry
        result = await acquisition.process_sealed(publication_id)
        assert result["results"][0]["status"] == "accepted"
        events = drain(telemetry)
        transport = [
            event
            for event in events
            if event["operation"] == "acquisition.receive"
            and event["event"] == "operation.completed"
        ]
        assert len(transport) == 2
        assert {event["outcome"] for event in transport} == {
            "success",
            "expected_rejection",
        }
        terminal = next(
            event for event in events if event["event"] == "reception.completed"
        )
        process = next(
            event
            for event in events
            if event["operation"] == "acquisition.process"
            and event["event"] == "operation.completed"
        )
        assert process["parent_operation_ref"] == next(event["operation_ref"] for event in transport if event["outcome"] == "success")
        assert terminal["parent_operation_ref"] == process["operation_ref"]
        assert terminal["publication_ref"] == process["publication_ref"]
        assert process["counts"]["files_seen"] == process["counts"]["files_parsed"] == 1
        assert terminal["counts"]["records_accepted"] == 1
        spans = telemetry.traces.take_batch()
        roots = {format(span.context.span_id, "016x"): span for span in spans}
        for event in transport + [process, terminal]:
            span = roots[event["span_id"]]
            assert span.attributes["outcome"] == event["outcome"]
            assert format(span.context.trace_id, "032x") == event["trace_id"]
        text = json.dumps(events) + str([dict(span.attributes) for span in spans])
        assert "SIMULATED-PAS600" not in text and "modbus:" not in text
        assert "20260101003000000_1.json" not in text
    finally:
        listener.close()
        await listener.wait_closed()
        telemetry.shutdown()


async def test_unreadable_and_resend_installed_adapter(
    acquisition_environment, tmp_path
):
    """Unreadable input and a real duplicate resend keep safe counts, stable publication and distinct attempts."""
    env = acquisition_environment
    acquisition = service(env)
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "files"),
        clock=env["clock"],
        autostart=False,
    )
    acquisition.telemetry = acquisition.reception.telemetry = telemetry
    try:
        publication = await sealed(env)
        first = await acquisition.process_sealed(publication)
        assert first["results"][0]["status"] == "accepted"
        assert await sealed(env) == publication
        await acquisition.recover()
        unreadable = await sealed(env, b"PRIVATE_UNREADABLE_NATIVE_MARKER")
        await acquisition.process_sealed(unreadable)
        events = drain(telemetry)
        receptions = [e for e in events if e["event"] == "reception.completed"]
        assert len(receptions) == 2
        assert receptions[0]["publication_ref"] == receptions[1]["publication_ref"]
        assert receptions[0]["attempt_ref"] != receptions[1]["attempt_ref"]
        assert receptions[1]["counts"]["records_duplicate"] == 1
        assert receptions[1]["outcome"] == "expected_rejection"
        files = [
            e
            for e in events
            if e["operation"] == "acquisition.process"
            and e["event"] == "operation.completed"
        ]
        assert len(files) == 3 and files[-1]["counts"]["files_unreadable"] == 1
        assert files[-1]["outcome"] == "expected_rejection"
        assert "PRIVATE_UNREADABLE_NATIVE_MARKER" not in json.dumps(events)
    finally:
        telemetry.shutdown()


async def test_live_acquisition_and_reception_traces(
    acquisition_environment, live_telemetry, deliver_telemetry
):
    """Native003 bytes produce real001/002 durable consumption and queryable external log/trace references."""
    env = acquisition_environment
    acquisition = service(env)
    acquisition.telemetry = acquisition.reception.telemetry = live_telemetry
    result = await acquisition.process_sealed(await sealed(env))
    assert result["results"][0]["status"] == "accepted"
    events, stored = await deliver_telemetry(live_telemetry)
    process = next(
        e
        for e in stored
        if e["operation"] == "acquisition.process"
        and e["event"] == "operation.completed"
    )
    reception = next(e for e in stored if e["event"] == "reception.completed")
    assert reception["parent_operation_ref"] == process["operation_ref"]
    assert reception["publication_ref"] == process["publication_ref"]
    assert reception["counts"]["records_accepted"] == 1
