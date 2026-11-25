"""007 real fixed-filesystem rejection; prolonged retention uses its explicit resumable probe."""

import asyncio
import json
import os
from pathlib import Path
import ssl
import subprocess
import pytest
import httpx
from ecs_ec.observability.lifecycle import Policy, Telemetry
from ecs_ec.observability.capacity import QUOTAS
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from backend.tests.contract.reports.test_reports_api import terminal

pytestmark = pytest.mark.integration


@pytest.mark.real_time
def test_real_retention_probe_query_expiry_evidence():
    """Review actual24h probe query evidence; this assertion deliberately does not certify physical Badger GC."""
    from datetime import UTC, datetime

    raw = os.environ.get("OBS_RETENTION_PROBE_ROOT")
    if not raw:
        pytest.skip("Explicit completed real-time007 retention probe required")
    root = Path(raw)
    assert root.is_absolute() and root.name == "test" and not root.is_symlink()
    state = json.loads((root / "retention-probe.json").read_text())
    assert state["phase"] == "expired_query_confirmed_physical_review_pending"
    assert datetime.now(UTC) >= datetime.fromisoformat(state["expires_at"])
    before, after = state["before_restart"], state["after_restart"]
    for reading in (before, after, state["pre_ttl"]):
        assert reading["logs"] == reading["metric_operations"] == 10
        assert reading["traces"] == [200] * 10
    expired = state["observations"][-1]
    assert expired["logs"] == 0 and expired["metric_operations"] is None
    assert expired["traces"] == [404] * 10
    assert datetime.fromisoformat(expired["observed_at"]) <= datetime.fromisoformat(
        state["verification_deadline"]
    )
    assert state["physical_badger_accepted"] is False


@pytest.mark.real_time
def test_real_retention_original_physical_segments_removed():
    """Require removal of original Loki/Badger data files and expired spool within budget; absence in queries alone cannot pass."""
    from datetime import datetime

    raw = os.environ.get("OBS_RETENTION_PROBE_ROOT")
    if not raw:
        pytest.skip("Explicit real24h007 probe and physical observations required")
    state = json.loads((Path(raw) / "retention-probe.json").read_text())
    assert state["phase"] == "expired_query_confirmed_physical_review_pending"
    last = state["observations"][-1]
    assert datetime.fromisoformat(last["observed_at"]) <= datetime.fromisoformat(
        state["verification_deadline"]
    )
    for signal in ("logs", "traces"):
        baseline = state["physical_baseline"][signal]
        current = last["storage"][signal]
        assert not baseline["truncated"] and not current["truncated"]
        original = {
            item["path"]
            for item in baseline["files"]
            if signal == "logs" or Path(item["path"]).suffix in {".sst", ".vlog"}
        }
        assert original, (
            "No original physical data files were captured; query-only evidence is insufficient"
        )
        assert original.isdisjoint({item["path"] for item in current["files"]}), (
            "Original physical data files remain; review GC rather than treating404 as deletion"
        )
    assert state["spool_sources"]
    assert all(
        segment.get("physically_removed") and segment.get("within_verification_budget")
        for segment in state["spool_sources"]
    )


@pytest.fixture
async def quota_stack():
    """Require an explicit owned test manifest and trusted technical listener; never allocate host mounts implicitly."""
    raw = os.environ.get("OBS_QUOTA_TEST_ROOT")
    if not raw:
        pytest.skip(
            "Fixed007 quota filesystems and running monolith telemetry worker required"
        )
    root = Path(raw)
    assert (
        root.is_absolute()
        and root.name == "test"
        and (root / "environment").read_text().strip() == "test"
    )
    manifest = json.loads((root / "quota-manifest.json").read_text())
    assert manifest["owner_uid"] == os.getuid() and manifest["root"] == str(root)
    async with httpx.AsyncClient(
        base_url=os.environ.get("OBS_QUOTA_TEST_URL", "https://localhost:3446"),
        verify=ssl.create_default_context(cafile=str(root / "ca.crt")),
        auth=("prog-test-01", "Synthetic technical password 007"),
        trust_env=False,
        timeout=10,
    ) as client:
        yield (
            root,
            os.environ.get("OBS_QUOTA_TEST_PROJECT", "ecs007-step4-quotas"),
            client,
        )


async def status(root, allowed):
    """Wait for the real15s worker snapshot, not a fabricated clock or direct status-file modification."""
    for _ in range(200):
        try:
            value = json.loads((root / "quota-status/status.json").read_text())
            if value["allowed"] is allowed:
                return value
        except OSError, ValueError:
            pass
        await asyncio.sleep(0.2)
    raise AssertionError("Actual technical worker did not publish quota transition")


async def ingest(root, project):
    """Probe only application-mTLS OTLP from its private network; no human credentials or functional ports."""
    assert project.startswith("ecs007-")
    code = "import httpx,ssl;ctx=ssl.create_default_context(cafile='/tls/ca.crt');ctx.load_cert_chain('/tls/app.crt','/tls/app.key');r=httpx.post('https://technical-gateway:8444/v1/traces',content=b'',headers={'Content-Type':'application/x-protobuf'},verify=ctx,trust_env=False,timeout=6);print(r.status_code)"
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "docker",
            "run",
            "--rm",
            "--user",
            str(os.getuid()),
            "--network",
            project + "_technical_ingest",
            "-v",
            str(root / "clients/app") + ":/tls:ro",
            os.environ.get("OBS_TEST_IMAGE", "ecs007-step4-app:local"),
            "/app/.venv/bin/python",
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return int(result.stdout.strip())


@pytest.mark.parametrize("name", list(QUOTAS))
async def test_real_fixed_quota_rejects_at_ninety_percent_without_business_loss(
    quota_stack,
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    name,
):
    """Allocate real extents above90% of one technical budget; mTLS ingestion denies while004/005 commit normally."""
    root, project, client = quota_stack
    paths = {
        "spool": "spool",
        "alloy": "data/alloy",
        "loki": "data/loki",
        "jaeger": "data/jaeger",
        "grafana": "data/grafana",
    }
    directory = root / paths[name]
    before = await status(root, True)
    assert (
        before["valid"]
        and len({(root / path).stat().st_dev for path in paths.values()}) == 5
    )
    assert before["quotas"][name]["total_bytes"] <= QUOTAS[name]
    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    telemetry = Telemetry(
        Policy(environment="test", spool=root / "spool"), autostart=False
    )
    app = costs_client._transport.app
    app.state.telemetry = app.state.reports.telemetry = telemetry
    filler = directory / ".quota-fill-test"
    try:
        usage = os.statvfs(directory)
        total = usage.f_blocks * usage.f_frsize
        used = total - usage.f_bavail * usage.f_frsize
        with filler.open("xb") as stream:
            os.posix_fallocate(
                stream.fileno(), 0, max(4096, (total * 92 // 100) - used)
            )
        proof = await status(root, False)
        item = proof["quotas"][name]
        assert item["used_bytes"] * 10 >= item["total_bytes"] * 9
        assert await ingest(root, project) == 507
        assert (await client.get("/jaeger/api/v3/services")).status_code == 200
        calculation = await costs_client.post(
            "/api/v1/costs/calculations", json=body, headers=headers
        )
        assert (
            calculation.status_code == 201
            and calculation.json()["complete_total"] == "100000"
        )
        assert (
            await costs_client.get(
                "/api/v1/costs/calculations/" + calculation.json()["id"]
            )
        ).json() == calculation.json()
        if name == "spool":
            headers["Idempotency-Key"] = "full-quota-pdf"
            request = await costs_client.post(
                "/api/v1/reports",
                json={"scale": "anual", "year": 2024},
                headers=headers,
            )
            assert request.status_code == 202, request.text
            pdf = await terminal(costs_client, request.json()["id"])
            assert pdf["state"] == "generado"
            assert (await costs_client.get(pdf["download_path"])).content.startswith(
                b"%PDF-"
            )
            while telemetry.logs.drain_one():
                pass
            assert telemetry.logs.spool_dropped > 0
    finally:
        telemetry.shutdown()
        if filler.exists():
            filler.unlink()
        await status(root, True)
    assert await ingest(root, project) == 200


async def test_sampling_is_explicit_and_never_samples_terminal_logs(
    live_telemetry, deliver_telemetry, gateway_client
):
    """Actual SDK ratio0.1 exports10roots plus their10children from100 known IDs; all100 terminal logs remain."""
    from uuid import uuid4
    from opentelemetry.sdk.trace.id_generator import IdGenerator

    class KnownIds(IdGenerator):
        """Supply unique test IDs with low64-bit values centered in ten equal sampler buckets."""

        def __init__(self):
            """Separate runs by a random opaque prefix; deterministic low bits make the sampler assertion exact."""
            self.prefix = uuid4().int >> 64
            self.index = 0
            self.span = uuid4().int & ((1 << 63) - 1)

        def generate_trace_id(self):
            """Return one unique128-bit ID; exactly every tenth root is below the SDK's0.1 threshold."""
            self.index += 1
            return ((self.prefix + self.index) & ((1 << 64) - 1)) << 64 | (
                (2 * (self.index % 10) + 1) * (1 << 64) // 20
            )

        def generate_span_id(self):
            """Return a new nonzero64-bit span ID without changing the SDK's sampling decision."""
            self.span += 1
            return self.span

    sampled = Telemetry(
        Policy(
            environment="test",
            spool=live_telemetry.policy.spool,
            revision="007-sampling-test",
            trace_ratio=0.1,
        ),
        autostart=False,
    )
    sampled.traces.tracer.id_generator = KnownIds()
    try:
        for _ in range(100):
            handle = sampled.begin("cost.query", "costs")
            sampled.stage(handle, "read")
            sampled.complete(handle)
        assert sampled.traces.depth == 20
        events, stored = await deliver_telemetry(sampled)
        assert len([e for e in stored if e["event"] == "operation.completed"]) == 100
        assert all(e["policy_revision"] == "007-sampling-test" for e in stored)
        assert sampled.traces.exported == 20 and sampled.traces.dropped == 0
        roots = [e for e in events if e["event"] == "operation.completed"]
        missing = next(
            e
            for e in roots
            if int(e["trace_id"], 16) & ((1 << 64) - 1) > (1 << 64) // 10
        )
        assert (
            await gateway_client.get("/jaeger/api/v3/traces/" + missing["trace_id"])
        ).status_code == 404
    finally:
        sampled.shutdown()
