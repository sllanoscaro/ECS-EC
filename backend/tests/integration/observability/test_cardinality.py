"""0071000 opaque references, immutable replay and real Alloy position loss against pinned Loki."""

import asyncio
import json
from pathlib import Path
import subprocess
import time
import pytest
from backend.tests.integration.observability.test_metrics import value
from backend.tests.integration.observability.test_collection_continuity import (
    component,
    ready,
)

pytestmark = pytest.mark.integration


async def test_thousand_references_have_stable_series_and_replay_count(
    live_telemetry,
    deliver_telemetry,
    gateway_client,
    gateway_project,
    gateway_root,
    live_collector_health,
):
    """Keep1000 unique raw terminals, surface native replay inflation and expose collector restarts without ID labels."""
    await live_collector_health(live_telemetry)
    for _ in range(1000):
        handle = live_telemetry.begin("consumption.query_detail", "consumption")
        live_telemetry.complete(handle)
        # Exercise real bounded admission with its disk worker, not a synthetic infinite queue.
        while live_telemetry.logs.drain_one():
            pass
    cut = time.time_ns() - 1
    await deliver_telemetry(live_telemetry)
    boot = live_telemetry.logs.boot_id
    assert live_telemetry.logs.dropped == 0 and live_telemetry.logs.spool_dropped == 0
    assert (
        await value(
            gateway_client,
            "operations_total",
            "consumption.query_detail",
            boot,
            time_ns=cut,
        )
        == 1000
    )
    raw = (
        '{service_name="ecs-ec",environment="test",operation="consumption.query_detail"} |= '
        + json.dumps('"boot_id":"' + boot + '"')
    )
    response = await gateway_client.get(
        "/logs/loki/api/v1/query_range",
        params={
            "query": raw,
            "start": str(cut - 30000000000),
            "end": str(cut),
            "limit": 10000,
        },
    )
    assert response.status_code == 200, response.text[:300]
    streams = response.json()["data"]["result"]
    assert len(streams) == 2
    assert all(
        set(stream["stream"])
        == {"service_name", "environment", "operation", "outcome", "severity"}
        for stream in streams
    )
    original = next(
        line
        for path in (gateway_root / "spool").glob("events-*.jsonl")
        for line in path.read_bytes().splitlines()
        if ('"boot_id":"' + boot + '"').encode() in line
        and b'"event":"operation.completed"' in line
    )
    live_telemetry.logs._write(original)
    await asyncio.sleep(2)
    replayed = await value(
        gateway_client,
        "operations_total",
        "consumption.query_detail",
        boot,
        time_ns=cut,
    )
    # Pinned Loki may count the same immutable delivery twice in a metric range
    # even though raw log queries deduplicate it. Keep this failure visible and
    # verify the panel guard rather than changing labels or claiming exact totals.
    assert replayed in {1000, 1001}
    replay = await gateway_client.get(
        "/logs/loki/api/v1/query_range",
        params={
            "query": raw,
            "start": str(cut - 30000000000),
            "end": str(cut),
            "limit": 10000,
        },
    )
    unique = {
        json.loads(line)["event_id"]
        for stream in replay.json()["data"]["result"]
        for _, line in stream["values"]
        if json.loads(line)["event"] == "operation.completed"
    }
    assert len(unique) == 1000
    # Feed the actual Loki response and aggregate to the same browser reconciler.
    # With no bracketing heartbeat this window is conservatively limited; an
    # inflated native aggregate must additionally explain that specific replay.
    core = (
        Path(__file__).resolve().parents[4]
        / "deploy/observability/grafana/plugins/ecsec-coverage-panel/reconcile.mjs"
    ).as_uri()
    script = """import {lokiRows,reconcile} from CORE;
let input='';for await(const chunk of process.stdin)input+=chunk;
const fixture=JSON.parse(input);
const result=reconcile(lokiRows(fixture.response),{
startNs:BigInt(fixture.cut)-30000000000n,endNs:BigInt(fixture.cut)+1n,
nowNs:BigInt(fixture.cut)+60000000000n,environment:'test',revision:'007-v1',
retentionHours:24,traceRatio:1,logsReachable:true,truncated:false,
logicalAggregate:fixture.aggregate,aggregateQueryReachable:true,
traceEvidence:{reachable:false,ids:new Set()}});
console.log(JSON.stringify({causes:result.causes,measures:result.measures}));
""".replace("CORE", json.dumps(core))
    reconciled = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(
            {"response": replay.json(), "cut": str(cut), "aggregate": replayed}
        ),
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    panel = json.loads(reconciled.stdout)
    assert panel["measures"]["operations_total"] == 1000
    assert panel["measures"]["unexpected_error_percent"] is None
    if replayed != 1000:
        assert "replay_en_agregado" in panel["causes"]
    positions = gateway_root / "data/alloy/loki.source.file.spool/positions.yml"
    assert positions.is_file()
    component(gateway_project, "stop", "alloy")
    saved = positions.read_bytes()
    try:
        positions.unlink()  # Only this explicitly selected disposable test checkpoint.
        component(gateway_project, "start", "alloy")
        # A newly appended terminal must be delivered after recovery. This tests
        # reaching the live file end without trusting Alloy's persisted byte gauge.
        live_telemetry.complete(live_telemetry.begin("cost.query", "costs"))
        await deliver_telemetry(live_telemetry)
        await live_collector_health(live_telemetry)
        assert live_telemetry.status.snapshot()["collector_restarts_total"] == 1
        assert (
            await value(
                gateway_client,
                "operations_total",
                "consumption.query_detail",
                boot,
                time_ns=cut,
            )
            >= 1000
        )
        replay = await gateway_client.get(
            "/logs/loki/api/v1/query_range",
            params={
                "query": raw,
                "start": str(cut - 30000000000),
                "end": str(cut),
                "limit": 10000,
            },
        )
        assert len(replay.json()["data"]["result"]) == 2
        assert (
            len(
                {
                    json.loads(line)["event_id"]
                    for stream in replay.json()["data"]["result"]
                    for _, line in stream["values"]
                    if json.loads(line)["event"] == "operation.completed"
                }
            )
            == 1000
        )
    finally:
        # If startup failed, restore only the fixture's own checkpoint before retrying.
        if not positions.exists():
            positions.parent.mkdir(parents=True, exist_ok=True)
            positions.write_bytes(saved)
        await ready(gateway_client, "/logs/loki/api/v1/labels")
