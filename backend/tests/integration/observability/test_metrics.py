"""007 real Loki expressions are checked against known owner outcomes at one exact cut."""

import time
import pytest
from ecs_ec.observability.queries import metric_query
from backend.tests.contract.costs.test_calculations_api import authenticate

pytestmark = pytest.mark.integration


async def value(client, name, operation, boot_id, *, time_ns=None):
    """Evaluate one closed catalog expression as Programador; empty vectors remain nullable."""
    response = await client.get(
        "/logs/loki/api/v1/query",
        params={
            "query": metric_query(name, "test", operation, 30000, boot_id=boot_id),
            "time": str(time_ns or time.time_ns()),
        },
    )
    assert response.status_code == 200, response.text[:500]
    values = response.json()["data"]["result"]
    assert len(values) <= 1, values
    return float(values[0]["value"][1]) if values else None


async def test_ten_actual_queries_eight_success_two_errors(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    live_telemetry,
    deliver_telemetry,
    gateway_client,
    monkeypatch,
):
    """Actual001 HTTP responses define8/2; Loki excludes their stages and separate006 authorizations."""
    app = costs_client._transport.app
    app.state.telemetry = live_telemetry
    await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )

    async def unavailable(*args, **kwargs):
        """Fail only the real001 read boundary for the final two calls, without substituting their results."""
        raise ValueError("PRIVATE_QUERY_FAILURE")

    responses = []
    for index in range(10):
        if index == 8:
            monkeypatch.setattr(app.state.consumption, "detail", unavailable)
        responses.append(
            await costs_client.get(
                "/api/v1/consumption/categories/CAT-05/detail",
                params={
                    "start": "2025-12-31T21:00:00-03:00",
                    "end": "2025-12-31T22:00:00-03:00",
                    "timezone": "America/Santiago",
                },
            )
        )
    assert [r.status_code for r in responses] == [200] * 8 + [503] * 2
    await deliver_telemetry(live_telemetry)
    assert (
        await value(
            gateway_client,
            "operations_total",
            "consumption.query_detail",
            live_telemetry.logs.boot_id,
        )
        == 10
    )
    assert (
        await value(
            gateway_client,
            "unexpected_error_percent",
            "consumption.query_detail",
            live_telemetry.logs.boot_id,
        )
        == 20
    )


async def test_real_reception_five_positions_three_new(
    live_telemetry, deliver_telemetry, gateway_client, history_environment
):
    """002 defines five positions:3accepted/1invalid/1duplicate; Loki counts its one logical terminal only."""
    from uuid import UUID
    from backend.tests.contract.consumption.test_reception_contract import publish
    from backend.tests.unit.consumption.test_validation import record

    history_environment.telemetry = live_telemetry
    rows = [
        record(category_id=f"CAT-{i:02}", source_id=UUID(int=i)) for i in range(1, 4)
    ]
    rows += [record(unit="INVALID_UNIT"), rows[0]]
    outcome = await publish(history_environment, rows)
    assert [r.status for r in outcome.results] == [
        "accepted",
        "accepted",
        "accepted",
        "rejected",
        "duplicate",
    ]
    await deliver_telemetry(live_telemetry)
    for name, expected in [
        ("operations_total", 1),
        ("records_seen", 5),
        ("records_accepted", 3),
        ("records_invalid", 1),
        ("records_duplicate", 1),
        ("records_other_rejected", 0),
    ]:
        assert (
            await value(
                gateway_client, name, "reception.accept", live_telemetry.logs.boot_id
            )
            == expected
        )


async def test_closed_known_window_and_real_browser(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    live_telemetry,
    deliver_telemetry,
    live_collector_health,
    gateway_root,
    tmp_path,
    monkeypatch,
):
    """A real closed window reconciles every sequence, actual Alloy health and queryable Jaeger references in UI."""
    import asyncio, json, os, subprocess

    app = costs_client._transport.app
    app.state.telemetry = live_telemetry
    await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    await live_collector_health(live_telemetry)
    start_ms = time.time_ns() // 1000000
    await asyncio.sleep(0.01)

    async def fail(*args, **kwargs):
        """Cause two safe001 failures after eight actual successful reads."""
        raise ValueError("PRIVATE_METRIC_FAILURE")

    for index in range(10):
        if index == 8:
            monkeypatch.setattr(app.state.consumption, "detail", fail)
        response = await costs_client.get(
            "/api/v1/consumption/categories/CAT-05/detail",
            params={
                "start": "2025-12-31T21:00:00-03:00",
                "end": "2025-12-31T22:00:00-03:00",
                "timezone": "America/Santiago",
            },
        )
        assert response.status_code == (200 if index < 8 else 503)
    end_ms = time.time_ns() // 1000000 + 1
    await asyncio.sleep(0.02)
    events, stored = await deliver_telemetry(live_telemetry)
    await live_collector_health(live_telemetry)
    # A closed coverage window needs a following heartbeat; its real age is checked
    # in the browser after45s, without changing a server or storage clock.
    reference = tmp_path / "diagnosis.json"
    reference.write_text(
        json.dumps(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "boot_id": live_telemetry.logs.boot_id,
                "references": [
                    {"operation_ref": e["operation_ref"], "trace_id": e["trace_id"]}
                    for e in events
                    if e["operation"] == "consumption.query_detail"
                    and e["event"] == "operation.completed"
                ],
            }
        )
    )
    reference.chmod(0o600)
    technical = tmp_path / "password"
    technical.write_text("Synthetic technical password 007")
    technical.chmod(0o600)
    await asyncio.sleep(max(0, 46 - (time.time_ns() // 1000000 - end_ms) / 1000))
    env = {
        **os.environ,
        "OBS_E2E_PASSWORD_FILE": str(technical),
        "OBS_E2E_REFERENCE_FILE": str(reference),
        "OBS_E2E_URL": os.environ.get("OBS_TEST_URL", "https://localhost:3444"),
        "NODE_EXTRA_CA_CERTS": str(gateway_root / "ca.crt"),
    }
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "node",
            "--jitless",
            "node_modules/@playwright/test/cli.js",
            "test",
            "tests/e2e/observability-metrics.spec.ts",
            "tests/e2e/observability-diagnosis.spec.ts",
            "--workers=1",
        ],
        cwd="frontend",
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout[-7000:] + result.stderr[-1000:]


async def test_partial_recovery_uses_separate_error_denominators(
    history_environment,
    database,
    clock,
    live_telemetry,
    deliver_telemetry,
    gateway_client,
    monkeypatch,
):
    """Actual002 commits3 then2 after recovery:50% execution errors,0% completed-attempt errors,5new records."""
    from uuid import UUID, uuid4
    from ecs_ec.consumption.reception import Reception
    from backend.tests.contract.consumption.test_reception_contract import (
        publish,
        BUILDING,
        PROCESS,
    )
    from backend.tests.unit.consumption.test_validation import record

    history_environment.telemetry = live_telemetry
    original = history_environment._category

    async def interrupted(attempt, building, category, *args, **kwargs):
        """Stop the actual next category transaction after three committed categories."""
        if category == "CAT-04":
            raise RuntimeError("PRIVATE_PARTIAL_FAILURE")
        return await original(attempt, building, category, *args, **kwargs)

    monkeypatch.setattr(history_environment, "_category", interrupted)
    rows = [
        record(category_id=f"CAT-{i:02}", source_id=UUID(int=i)) for i in range(1, 6)
    ]
    attempt = uuid4()
    with pytest.raises(RuntimeError):
        await publish(history_environment, rows, attempt=attempt)
    recovered = Reception(
        database,
        clock,
        authorized_processes={PROCESS: {BUILDING}},
        telemetry=live_telemetry,
    )
    result = await publish(recovered, rows, attempt=attempt)
    assert len(result.results) == 5 and all(
        row.status == "accepted" for row in result.results
    )
    sequence = live_telemetry.logs.sequence
    assert await publish(recovered, rows, attempt=attempt) == result
    assert live_telemetry.logs.sequence == sequence
    cut = time.time_ns() - 1
    await deliver_telemetry(live_telemetry)
    for name, expected in [
        ("operations_total", 1),
        ("attempt_executions_total", 2),
        ("records_accepted", 5),
        ("unexpected_error_percent", 0),
        ("execution_unexpected_error_percent", 50),
    ]:
        assert (
            await value(
                gateway_client,
                name,
                "reception.accept",
                live_telemetry.logs.boot_id,
                time_ns=cut,
            )
            == expected
        )


async def test_known_durations_and_nullable_denominator(
    live_telemetry, deliver_telemetry, gateway_client
):
    """100/200/300ms technical executions have mean200/p50200/p95290; a missing duration is excluded."""
    from datetime import UTC, datetime, timedelta
    from ecs_ec.core.clock import FrozenClock
    from ecs_ec.observability.lifecycle import Telemetry, Policy

    controlled = Telemetry(
        Policy(environment="test", spool=live_telemetry.policy.spool),
        clock=FrozenClock(datetime.now(UTC) - timedelta(seconds=3)),
        autostart=False,
    )
    try:
        for duration in (0.1, 0.2, 0.3):
            handle = controlled.begin("cost.query", "costs")
            controlled.clock.advance(duration)
            controlled.complete(handle)
        controlled.complete(controlled.begin("cost.query", "costs"), duration_ms=None)
        cut = time.time_ns() - 1
        await deliver_telemetry(controlled)
        for name, expected in [
            ("processing_duration_mean_ms", 200),
            ("processing_duration_p50_ms", 200),
            ("processing_duration_p95_ms", 290),
        ]:
            assert await value(
                gateway_client, name, "cost.query", controlled.logs.boot_id, time_ns=cut
            ) == pytest.approx(expected)
        assert (
            await value(
                gateway_client,
                "unexpected_error_percent",
                "cost.compare",
                controlled.logs.boot_id,
                time_ns=cut,
            )
            is None
        )
    finally:
        controlled.shutdown()


async def test_adjacent_loki_windows_preserve_nanosecond_boundaries(
    live_telemetry, deliver_telemetry, gateway_client
):
    """Actual Loki ranges count start/end-1ns in the first window and the exact end only in the next."""
    import json
    from datetime import UTC, datetime
    from uuid import uuid4

    payloads = []
    live_telemetry.logs._writer = payloads.append
    live_telemetry.complete(
        live_telemetry.begin("consumption.query_detail", "consumption")
    )
    while live_telemetry.logs.drain_one():
        pass
    base = next(
        json.loads(data)
        for data in payloads
        if json.loads(data)["event"] == "operation.completed"
    )
    begin = (time.time_ns() // 1000000000 - 70) * 1000000000
    live_telemetry.logs._writer = live_telemetry.logs._write
    for offset in (0, 29999999999, 30000000000):
        ns = begin + offset
        timestamp = (
            datetime.fromtimestamp(ns // 1000000000, UTC).strftime("%Y-%m-%dT%H:%M:%S")
            + "."
            + f"{ns % 1000000000:09d}"
            + "Z"
        )
        event = {
            **base,
            "event_id": str(uuid4()),
            "timestamp": timestamp,
            "trace_id": None,
            "span_id": None,
        }
        assert live_telemetry.logs.emit(event) == "enqueued"
    await deliver_telemetry(live_telemetry)
    assert (
        await value(
            gateway_client,
            "operations_total",
            "consumption.query_detail",
            live_telemetry.logs.boot_id,
            time_ns=begin + 30000000000 - 1,
        )
        == 2
    )
    assert (
        await value(
            gateway_client,
            "operations_total",
            "consumption.query_detail",
            live_telemetry.logs.boot_id,
            time_ns=begin + 60000000000 - 1,
        )
        == 1
    )
