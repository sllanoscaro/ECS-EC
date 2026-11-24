"""005 financial PDFs preserve004's selected exact pairs through corrections and recalculations."""

from io import BytesIO
from uuid import UUID, uuid4
import pytest
from pypdf import PdfReader
from sqlalchemy import select, func
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Capture, Result
from ecs_ec.costs.models import Comparison

pytestmark = pytest.mark.integration


async def emit(client, headers, database):
    """Obtain the actual PDF and immutable typed capture, without supplying any financial data to005."""
    response = await client.post(
        "/api/v1/reports",
        json={"scale": "anual", "year": 2025},
        headers=headers | {"Idempotency-Key": uuid4().hex},
    )
    assert response.status_code == 202, response.text
    status = await terminal(client, response.json()["id"])
    assert status["state"] == "generado", status
    content = (await client.get(status["download_path"])).content
    async with UnitOfWork(database.sessions) as uow:
        capture = await uow.session.scalar(
            select(Capture).where(Capture.request_id == UUID(status["id"]))
        )
        return status, content, capture.data, capture.functional_hash


async def test_exact_pairs_pending_correction_and_recalculation(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """A=C1/B1/K1; B=C1/B2 pending; C=C1/B2/K2; D=C2/B2 pending, withA's bytes/hash untouched."""
    client = costs_client
    env = costs_environment
    body = await prepared(env)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    calc = (
        await client.post("/api/v1/costs/calculations", json=body, headers=headers)
    ).json()
    bill_response = await client.post(
        "/api/v1/costs/bills",
        json=invoice(body),
        headers=headers | {"Idempotency-Key": "bill-a"},
    )
    bill = bill_response.json()
    first = await client.post(
        "/api/v1/costs/comparisons",
        json={
            "calculation_id": calc["id"],
            "bill_revision_id": bill["bill_revision_id"],
        },
        headers=headers | {"Idempotency-Key": "pair-a"},
    )
    assert first.status_code == 201, first.text
    a = await emit(client, headers, env["database"])
    assert (
        a[2]["financial_snapshot"]["cycles"][0]["comparison"]["id"]
        == first.json()["id"]
    )
    env["clock"].advance(1)
    correction = await client.put(
        "/api/v1/costs/bills/" + bill["id"],
        json=invoice(body, amount="90000"),
        headers=headers
        | {"Idempotency-Key": "bill-b", "If-Match": bill_response.headers["etag"]},
    )
    assert correction.status_code == 200, correction.text
    b = await emit(client, headers, env["database"])
    cycle = b[2]["financial_snapshot"]["cycles"][0]
    assert (
        cycle["comparison_status"] == "missing_for_selected_revisions"
        and cycle["delta_amount"] is None
    )
    assert b[2]["financial_snapshot"]["comparison_totals"] == []
    assert (
        "Contraste pendiente para estas revisiones"
        in PdfReader(BytesIO(b[1])).pages[0].extract_text()
    )
    second = await client.post(
        "/api/v1/costs/comparisons",
        json={
            "calculation_id": calc["id"],
            "bill_revision_id": correction.json()["bill_revision_id"],
        },
        headers=headers | {"Idempotency-Key": "pair-b"},
    )
    assert second.status_code == 201, second.text
    c = await emit(client, headers, env["database"])
    assert (
        c[2]["financial_snapshot"]["cycles"][0]["comparison"]["id"]
        == second.json()["id"]
    )
    assert c[2]["financial_snapshot"]["comparison_totals"][0]["delta_amount"] == "10000"
    env["clock"].advance(1)
    recalc = await client.post(
        "/api/v1/costs/calculations",
        json=body | {"reason": "synthetic revision"},
        headers=headers | {"Idempotency-Key": "calc-b"},
    )
    assert recalc.status_code == 201, recalc.text
    d = await emit(client, headers, env["database"])
    assert d[2]["financial_snapshot"]["cycles"][0]["calculation"]["revision"] == 2
    assert (
        d[2]["financial_snapshot"]["cycles"][0]["comparison_status"]
        == "missing_for_selected_revisions"
    )
    assert d[2]["financial_snapshot"]["comparison_totals"] == []
    assert (await client.get(a[0]["download_path"])).content == a[1]
    async with UnitOfWork(env["database"].sessions) as uow:
        assert (
            await uow.session.scalar(select(func.count()).select_from(Comparison)) == 2
        )
        saved = await uow.session.scalar(
            select(Capture).where(Capture.request_id == UUID(a[0]["id"]))
        )
        assert saved.data == a[2] and saved.functional_hash == a[3]
