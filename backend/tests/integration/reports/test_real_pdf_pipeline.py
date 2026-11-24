"""005 actual002 measurements and004 calculations survive persistence, PDF generation and repeated download."""

from uuid import UUID, uuid4
from io import BytesIO
import pytest
from pypdf import PdfReader
from sqlalchemy import select
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.reports.models import Capture
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "selection",
    [
        {"scale": "diario", "date": "2025-12-31"},
        {"scale": "mensual", "year": 2025, "month": 12},
        {"scale": "anual", "year": 2025},
    ],
)
async def test_pdf_values_are_real_producer_values(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    selection,
):
    """Each scale preserves known1000kWh and100000CLP from real sources, even though the cycle starts inUTCJanuary."""
    env = costs_environment
    client = costs_client
    body = await prepared(env)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    calculation = await client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert calculation.status_code == 201, calculation.text
    headers["Idempotency-Key"] = uuid4().hex
    response = await client.post("/api/v1/reports", json=selection, headers=headers)
    assert response.status_code == 202, response.text
    status = await terminal(client, response.json()["id"])
    assert status["state"] == "generado", status
    content = (await client.get(status["download_path"])).content
    text = PdfReader(BytesIO(content)).pages[0].extract_text()
    assert "1000" in text and "100000" in text and "CLP" in text
    async with UnitOfWork(env["database"].sessions) as uow:
        capture = await uow.session.scalar(
            select(Capture).where(Capture.request_id == UUID(status["id"]))
        )
        assert capture.data["energy_rows"][0]["energy_kwh"] == "1000"
        assert (
            len(capture.data["chart_blocks"])
            == {"diario": 24, "mensual": 31, "anual": 12}[selection["scale"]]
        )
        assert (
            capture.data["financial_snapshot"]["cycles"][0]["calculation"]["id"]
            == calculation.json()["id"]
        )
        assert (
            capture.data["cutoff_at"] == capture.data["financial_snapshot"]["cutoff_at"]
        )
    assert (await client.get(status["download_path"])).content == content


async def test_twelve_cycles_are_legible_on_one_page(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """A real annual selection with12 closed cycles fits without hiding cycle scope, financial state or quality."""
    from datetime import timedelta
    from backend.tests.costs_fixtures import seed_supply
    from backend.tests.unit.consumption.test_validation import record
    from backend.tests.contract.consumption.test_reception_contract import publish
    from ecs_ec.consumption.models import instant

    env = costs_environment
    client = costs_client
    supply = await seed_supply(env["database"], env["clock"])
    start = instant("2026-01-02T04:00:00Z")
    windows = [
        (start + timedelta(minutes=15 * i), start + timedelta(minutes=15 * (i + 1)))
        for i in range(12)
    ]
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                value="100",
                start=s.isoformat(),
                end=e.isoformat(),
            )
            for s, e in windows
        ],
    )
    env["clock"].advance(
        (instant("2026-01-03T00:00:00Z") - env["clock"].now()).total_seconds()
    )
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    for s, e in windows:
        response = await client.post(
            "/api/v1/costs/calculations",
            json=dict(
                supply_id=str(supply.id),
                start_at=s.isoformat(),
                end_at=e.isoformat(),
                timezone="America/Santiago",
                boundary_criterion="synthetic:exact",
            ),
            headers=headers | {"Idempotency-Key": uuid4().hex},
        )
        assert response.status_code == 201, response.text
    response = await client.post(
        "/api/v1/reports",
        json={"scale": "anual", "year": 2026},
        headers=headers | {"Idempotency-Key": uuid4().hex},
    )
    status = await terminal(client, response.json()["id"])
    assert status["state"] == "generado", status
    pdf = PdfReader(BytesIO((await client.get(status["download_path"])).content))
    assert len(pdf.pages) == 1 and "120000" in pdf.pages[0].extract_text()
