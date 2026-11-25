"""Opt-in stack isolation fixtures; business tests use existing owner fixtures/PostgreSQL."""

from uuid import uuid4
import pytest


@pytest.fixture
def technical_project(tmp_path):
    """Allocate unique test-only project, external resource directory and volume prefix.

    No containers start implicitly and no production volumes are selected or removed.
    Callers must tear down only the resources they explicitly created with this name.
    """
    return {
        "project": "ecs-obs-test-" + uuid4().hex,
        "root": tmp_path,
        "environment": "test",
    }


@pytest.fixture
def gateway_root():
    """Require explicit local test material; refuse local/vps/foreign roots before provisioning."""
    import os
    from pathlib import Path

    raw = os.environ.get("OBS_TEST_ROOT")
    if not raw:
        pytest.skip("OBS_TEST_ROOT required: real isolated007 stack is opt-in")
    root = Path(raw).resolve()
    if root.name != "test" or (root / "environment").read_text().strip() != "test":
        raise pytest.UsageError("Only explicitly prepared test environment is allowed")
    return root


@pytest.fixture
def gateway_provision(gateway_root):
    """Mutate only the selected test registry using a known synthetic fixture password."""
    from scripts.observability.manage_programmer import update

    def provision(action):
        """Enable/revoke only the dedicated opaque test subject, never a human credential."""
        return update(
            gateway_root.parent,
            "test",
            "prog-test-01",
            action,
            b"Synthetic technical password 007" if action == "grant" else None,
        )

    return provision


@pytest.fixture
async def gateway_client(gateway_root):
    """Connect through trusted local test TLS/Basic; never ignore certificate errors or use prod."""
    import os
    import ssl
    from urllib.parse import urlsplit
    import httpx

    url = os.environ.get("OBS_TEST_URL", "https://localhost:3444")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "localhost"
        or not parsed.port
        or parsed.port < 1024
    ):
        raise pytest.UsageError("OBS_TEST_URL requires localhost HTTPS test listener")
    tls = ssl.create_default_context(cafile=str(gateway_root / "ca.crt"))
    async with httpx.AsyncClient(
        base_url=url,
        verify=tls,
        trust_env=False,
        auth=("prog-test-01", "Synthetic technical password 007"),
        timeout=35,
    ) as client:
        yield client


@pytest.fixture
def gateway_project():
    """Select the explicit isolated Compose project; default preserves the original harness."""
    import os

    return os.environ.get("OBS_TEST_PROJECT", "ecs007-validation")


@pytest.fixture
def gateway_image():
    """Return a local application image used only for private network probes, never deployed."""
    import os

    return os.environ.get("OBS_TEST_IMAGE", "ecs007-validation-app:local")


@pytest.fixture
def live_telemetry(gateway_root):
    """Create the actual007 emitter at real UTC with a private test spool; caller owns explicit export."""
    from ecs_ec.observability.lifecycle import Policy, Telemetry

    telemetry = Telemetry(
        Policy(environment="test", spool=gateway_root / "spool"), autostart=False
    )
    try:
        yield telemetry
    finally:
        telemetry.shutdown()


@pytest.fixture
def deliver_telemetry(gateway_root, gateway_project, gateway_image, gateway_client):
    """Deliver actual sanitized bytes/spans via Alloy and OTLP, then query as Programador.

    A disposable docker process performs only network transport from the private
    ingestion bridge. It has the application certificate, no database or human keys.
    This harness is not evidence of production exporter latency or heartbeat coverage.
    """

    async def deliver(telemetry, *, logs_expected=True, traces_expected=True):
        """Drain after owner commits; require every own event and root trace to be queryable within30s."""
        import asyncio
        import json
        import os
        import subprocess
        import time
        from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans

        events = []

        def write(data):
            """Preserve immutable sanitized bytes on disk while retaining test-only expectations."""
            telemetry.logs._write(data)
            events.append(json.loads(data))

        telemetry.logs._writer = write
        while telemetry.logs.drain_one():
            pass
        sampled_ids = set()
        spans = telemetry.traces.take_batch()
        while spans:
            sampled_ids.update(format(span.context.trace_id, "032x") for span in spans)
            code = "import asyncio,sys; from ecs_ec.observability.tracing import DeadlineExporter; from opentelemetry.sdk.trace.export import SpanExportResult; e=DeadlineExporter('https://technical-gateway:8444/v1/traces',ca='/tls/ca.crt',cert='/tls/app.crt',key='/tls/app.key'); raise SystemExit(0 if asyncio.run(e.send(sys.stdin.buffer.read())) is SpanExportResult.SUCCESS else 1)"
            command = [
                "docker",
                "run",
                "--rm",
                "-i",
                "--user",
                str(os.getuid()),
                "--network",
                gateway_project + "_technical_ingest",
                "-v",
                str(gateway_root / "clients/app") + ":/tls:ro",
                gateway_image,
                "/app/.venv/bin/python",
                "-c",
                code,
            ]
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                input=encode_spans(spans).SerializeToString(),
                capture_output=True,
                timeout=12,
            )
            from opentelemetry.sdk.trace.export import SpanExportResult

            telemetry.traces.observe_batch(
                len(spans),
                SpanExportResult.SUCCESS
                if result.returncode == 0
                else SpanExportResult.FAILURE,
            )
            assert (result.returncode == 0) is traces_expected, (
                "Unexpected private OTLP delivery outcome"
            )
            spans = telemetry.traces.take_batch()
        expected = {event["event_id"] for event in events}
        observed = []
        for _ in range(60 if logs_expected else 1):
            response = await gateway_client.get(
                "/logs/loki/api/v1/query_range",
                params={
                    "query": '{service_name="ecs-ec",environment="test"} | json boot="boot_id" | boot="'
                    + telemetry.logs.boot_id
                    + '"',
                    "limit": 10000,
                    "start": str(time.time_ns() - 120_000_000_000),
                    "end": str(time.time_ns()),
                    "direction": "forward",
                },
            )
            if not logs_expected:
                assert response.status_code in {502, 503, 504}
                break
            assert response.status_code == 200, response.text[:200]
            observed = [
                json.loads(line)
                for stream in response.json()["data"]["result"]
                for _, line in stream["values"]
            ]
            if expected <= {event["event_id"] for event in observed}:
                break
            await asyncio.sleep(0.5)
        assert not logs_expected or expected <= {
            event["event_id"] for event in observed
        }, "Alloy/Loki did not persist every admitted event"
        for trace_id in {
            event["trace_id"]
            for event in events
            if traces_expected
            and event["event"]
            in {"operation.completed", "report.completed", "reception.completed"}
            and event["trace_id"] in sampled_ids
        }:
            for _ in range(40):
                trace = await gateway_client.get("/jaeger/api/v3/traces/" + trace_id)
                if trace.status_code != 404:
                    break
                await asyncio.sleep(0.5)
            assert trace.status_code == 200, trace.text[:200]
            assert trace_id.lower() in trace.text.lower() or trace.json().get(
                "result"
            ), "No persisted trace returned"
        return events, observed

    return deliver


@pytest.fixture
def live_collector_health(gateway_root, gateway_project, gateway_image):
    """Observe only permitted actual Alloy counters from its private mTLS health listener."""

    async def observe(telemetry):
        """Copy real transport counters/UTC process start into the test emitter; never fabricate health success."""
        import asyncio, json, os, subprocess
        from datetime import UTC, datetime

        code = """import httpx,ssl,json
ctx=ssl.create_default_context(cafile='/tls/ca.crt');ctx.load_cert_chain('/tls/health.crt','/tls/health.key')
with httpx.Client(verify=ctx,trust_env=False,timeout=2) as client:
 r=client.get('https://technical-gateway:8446/collector-health');r.raise_for_status()
 allowed={'loki_write_sent_entries_total':0,'loki_write_dropped_entries_total':0,'process_start_time_seconds':None}
 for line in r.text.splitlines():
  p=line.split()
  if len(p)==2 and p[0].split('{')[0] in allowed:
   name=p[0].split('{')[0];value=float(p[1]);allowed[name]=value if name=='process_start_time_seconds' else allowed[name]+int(value)
 print(json.dumps(allowed))
"""
        command = [
            "docker",
            "run",
            "--rm",
            "--user",
            str(os.getuid()),
            "--network",
            gateway_project + "_technical_ingest",
            "-v",
            str(gateway_root / "clients/health") + ":/tls:ro",
            gateway_image,
            "/app/.venv/bin/python",
            "-c",
            code,
        ]
        while telemetry.logs.drain_one():
            pass
        for _ in range(20):
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=8,
                check=True,
            )
            values = json.loads(result.stdout)
            if values["loki_write_sent_entries_total"] > 0:
                break
            await asyncio.sleep(0.5)
        assert values["loki_write_sent_entries_total"] > 0
        assert values["process_start_time_seconds"] is not None
        telemetry.status.observe_collector(
            success=True, dropped=values["loki_write_dropped_entries_total"]
        )
        observed_start = (
            datetime.fromtimestamp(values["process_start_time_seconds"], UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        if (
            telemetry.status.collector_started_at is not None
            and telemetry.status.collector_started_at != observed_start
        ):
            telemetry.status.collector_restarts += 1
        telemetry.status.collector_started_at = (
            datetime.fromtimestamp(values["process_start_time_seconds"], UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        telemetry.health()
        while telemetry.logs.drain_one():
            pass

    return observe
