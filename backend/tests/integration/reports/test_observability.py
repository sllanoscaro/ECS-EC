"""005 async producer emits007 technical evidence independently of009's durable events."""

import json
from uuid import uuid4
import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.observability.lifecycle import Telemetry, Policy

pytestmark = pytest.mark.integration


async def test_one_admission_completion_and_trusted_continuation(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
):
    """A replay plus status/download reads cannot inflate generation; the worker resumes the persisted operation."""
    client = costs_client
    service = client._transport.app.state.reports
    telemetry = Telemetry(Policy(environment="test", spool=tmp_path), autostart=False)
    service.telemetry = telemetry
    try:
        headers = await authenticate(
            client, account_factory, session_factory, identity_settings
        )
        headers["Idempotency-Key"] = uuid4().hex
        body = {"scale": "anual", "year": 2024}
        rejected = await client.post(
            "/api/v1/reports", json={"scale": "anual", "year": 9998}, headers=headers
        )
        assert rejected.status_code == 422
        first = await client.post("/api/v1/reports", json=body, headers=headers)
        assert first.status_code == 202, first.text
        assert (
            await client.post("/api/v1/reports", json=body, headers=headers)
        ).json() == first.json()
        status = await terminal(client, first.json()["id"])
        assert status["state"] == "generado"
        assert (await client.get(status["download_path"])).status_code == 200
        assert (await client.get(status["download_path"])).status_code == 200
        payloads = []
        telemetry.logs._writer = payloads.append
        while telemetry.logs.drain_one():
            pass
        events = [json.loads(p) for p in payloads]
        admitted = [e for e in events if e["event"] == "report.admitted"]
        completed = [e for e in events if e["event"] == "report.completed"]
        assert len(admitted) == len(completed) == 1
        assert admitted[0]["operation_ref"] == completed[0]["operation_ref"]
        assert admitted[0]["execution_ref"] != completed[0]["execution_ref"]
        assert completed[0]["duration_ms"] >= 0
        assert {"capture", "wait", "render", "preflight", "publish"} <= {
            e["stage"] for e in events
        }
        assert not any(
            e["event"] == "operation.completed" and e["operation"] == "report.generate"
            for e in events
        )
        assert "building_name" not in json.dumps(
            events
        ) and "energy_kwh" not in json.dumps(events)
    finally:
        telemetry.shutdown()
        service.telemetry = None


@pytest.mark.parametrize("failure", ["transport", "saturation"])
async def test_technical_failure_cannot_change_pdf(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
    failure,
):
    """Broken optional transport and a full bounded queue still yield a real privately downloadable PDF."""
    service = costs_client._transport.app.state.reports
    telemetry = Telemetry(Policy(environment="test", spool=tmp_path), autostart=False)
    service.telemetry = telemetry
    try:
        if failure == "transport":

            def fail(*args, **kwargs):
                """Fail only the technical adapter; the functional commit remains independent."""
                raise RuntimeError("PRIVATE_TECHNICAL_FAILURE")

            monkeypatch.setattr(telemetry, "begin", fail)
        else:
            for _ in range(1100):
                telemetry.complete(telemetry.begin("report.query", "reports"))
        headers = await authenticate(
            costs_client, account_factory, session_factory, identity_settings
        )
        response = await costs_client.post(
            "/api/v1/reports", json={"scale": "anual", "year": 2024}, headers=headers
        )
        status = await terminal(costs_client, response.json()["id"])
        assert status["state"] == "generado"
        assert (await costs_client.get(status["download_path"])).content.startswith(
            b"%PDF-"
        )
        if failure == "saturation":
            assert telemetry.logs.dropped > 0 and telemetry.logs.depth <= 1024
    finally:
        telemetry.shutdown()
        service.telemetry = None
