"""007 markers in real functional/native inputs never cross queues, spool, Loki or Jaeger."""

import io
import json
import subprocess
from uuid import uuid4, UUID
import pytest
from pypdf import PdfReader
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.catalog_storage import BuildingRow
from ecs_ec.acquisition.staging import Staging
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from backend.tests.contract.costs.test_bills_comparisons_api import invoice
from backend.tests.contract.reports.test_reports_api import terminal
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record
from backend.tests.integration.acquisition.test_recovery import service
from backend.tests.integration.acquisition.conftest import acquisition_environment as acquisition_environment  # noqa:F401

pytestmark = pytest.mark.integration


async def test_real_inputs_stay_out_of_all_technical_signals(
    costs_client,
    costs_environment,
    acquisition_environment,
    account_factory,
    session_factory,
    identity_settings,
    live_telemetry,
    deliver_telemetry,
    gateway_client,
    gateway_project,
    monkeypatch,
):
    """Real006 credentials,001 energy,004 bill,005 PDF and003 native name/content remain in their owners."""
    marker = "PRIVATE007_" + uuid4().hex
    app = costs_client._transport.app
    app.state.telemetry = app.state.reports.telemetry = live_telemetry
    app.state.consumption_reception.telemetry = live_telemetry
    costs_environment["reception"].telemetry = live_telemetry
    preauth = await costs_client.get("/api/v1/auth/csrf")
    denied = await costs_client.post(
        "/api/v1/auth/login",
        json={"email": marker + "@example.test", "password": marker + "_PASSWORD"},
        headers={
            "Origin": identity_settings.origin,
            "X-CSRF-Token": preauth.json()["csrf_token"],
        },
    )
    assert denied.status_code == 401
    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    bearer = costs_client.cookies.get("ecs_ec_session")
    headers.update(
        {
            "X-Request-ID": marker,
            "baggage": "private=" + marker,
            "traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01",
        }
    )
    energy = "123456.789987"
    outcome = await publish(
        costs_environment["reception"],
        [record(category_id="CAT-05", source_id=UUID(int=5), value=energy)],
    )
    assert outcome.results[0].status == "accepted"
    calculation = await costs_client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert calculation.status_code == 201, calculation.text
    headers["Idempotency-Key"] = "private-bill-007"
    money = "654321987"
    bill = await costs_client.post(
        "/api/v1/costs/bills",
        json=invoice(body, amount=money) | {"external_identifier": marker + "_BILL"},
        headers=headers,
    )
    assert bill.status_code == 201, bill.text
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        building = await uow.session.get(BuildingRow, app.state.costs.building_id)
        building.name = marker + "_PDF"
        await uow.commit()
    headers["Idempotency-Key"] = "private-pdf-007"
    admission = await costs_client.post(
        "/api/v1/reports", json={"scale": "anual", "year": 2024}, headers=headers
    )
    assert admission.status_code == 202, admission.text
    result = await terminal(costs_client, admission.json()["id"])
    assert result["state"] == "generado"
    binary = (await costs_client.get(result["download_path"])).content
    assert marker in "".join(
        page.extract_text() for page in PdfReader(io.BytesIO(binary)).pages
    )
    env = acquisition_environment
    stage = Staging(env["database"], env["clock"], env["settings"], env["binding"])
    await stage.start()
    handle = await stage.open(marker + "_20260101003000000_1.json")
    await stage.write(handle, 0, (marker + "_CSV_SECRET").encode())
    await stage.close(handle)
    stage.clean_eof = True
    acquisition = service(env)
    acquisition.telemetry = acquisition.reception.telemetry = live_telemetry
    await acquisition.process_sealed(await stage.finish())
    private_query = await costs_client.get(
        "/api/v1/consumption/categories/CAT-05/detail",
        params={
            "start": marker + "\nERROR",
            "end": "2026-01-02T00:00:00Z",
            "timezone": "America/Santiago",
        },
    )
    assert private_query.status_code == 422 and marker not in private_query.text
    from ecs_ec.costs import engine

    def fail(*args, **kwargs):
        """Exercise a raw sensitive exception through004's actual durable failure transaction."""
        raise RuntimeError(marker + "_EXCEPTION")

    monkeypatch.setattr(engine, "evaluate", fail)
    headers["Idempotency-Key"] = "private-failure-007"
    failure = await costs_client.post(
        "/api/v1/costs/calculations", json=body | {"reason": marker + "_RECALC"}, headers=headers
    )
    assert failure.status_code == 201 and failure.json()["execution_state"] == "fallido"
    secrets = [
        marker,
        bearer,
        energy,
        money,
        calculation.json()["id"],
        bill.json()["id"],
    ]
    queued = b"".join(live_telemetry.logs._data).decode() + str(
        [dict(span.attributes) for span in live_telemetry.traces._queue]
    )
    assert all(secret not in queued for secret in secrets)
    events, stored = await deliver_telemetry(live_telemetry)
    encoded = json.dumps(events) + json.dumps(stored)
    for trace_id in {event["trace_id"] for event in events if event["trace_id"]}:
        trace = await gateway_client.get("/jaeger/api/v3/traces/" + trace_id)
        assert trace.status_code == 200
        encoded += trace.text
    assert all(secret not in encoded for secret in secrets)
    for source in ("technical-gateway", "alloy", "loki", "jaeger", "grafana"):
        metadata = json.loads(
            subprocess.check_output(
                ["docker", "inspect", f"{gateway_project}-{source}-1"]
            )
        )[0]
        assert metadata["HostConfig"]["LogConfig"]["Type"] == "none"
