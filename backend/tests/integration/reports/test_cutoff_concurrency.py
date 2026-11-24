"""005 render consumes committed capture even if real004 sources change while the CPU worker runs."""

import asyncio, threading
import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from backend.tests.contract.costs.test_bills_comparisons_api import invoice
from backend.tests.integration.reports.test_costs_pdf_end_to_end import emit
from ecs_ec.reports.models import Capture
from sqlalchemy import select
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_bill_revision_during_render_does_not_recapture(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """A barrier inside the real renderer permits a real correction after capture, with no open005 source transaction."""
    import ecs_ec.reports.worker as worker

    client = costs_client
    env = costs_environment
    body = await prepared(env)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    await client.post("/api/v1/costs/calculations", json=body, headers=headers)
    bill = await client.post(
        "/api/v1/costs/bills",
        json=invoice(body),
        headers=headers | {"Idempotency-Key": "cutoff-bill"},
    )
    started = threading.Event()
    release = threading.Event()
    original = worker.render

    def blocked(*args):
        """Pause CPU composition only; all producer operations and actual rendering remain real."""
        started.set()
        if not release.wait(10):
            raise RuntimeError("test_render_barrier_timeout")
        return original(*args)

    monkeypatch.setattr(worker, "render", blocked)
    task = asyncio.create_task(emit(client, headers, env["database"]))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        env["clock"].advance(1)
        changed = await client.put(
            "/api/v1/costs/bills/" + bill.json()["id"],
            json=invoice(body, amount="90000"),
            headers=headers
            | {
                "Idempotency-Key": "cutoff-correction",
                "If-Match": bill.headers["etag"],
            },
        )
        assert changed.status_code == 200, changed.text
        from backend.tests.unit.consumption.test_validation import record
        from backend.tests.contract.consumption.test_reception_contract import publish
        from uuid import UUID

        await publish(
            env["reception"],
            [
                record(
                    category_id="CAT-01",
                    source_id=UUID(int=1),
                    value="2000",
                    start="2026-01-01T01:00:00Z",
                    end="2026-01-01T02:00:00Z",
                )
            ],
        )
        recalculated = await client.post(
            "/api/v1/costs/calculations",
            json=body | {"reason": "synthetic while rendering"},
            headers=headers | {"Idempotency-Key": "cutoff-recalculation"},
        )
        assert recalculated.status_code == 201, recalculated.text

    finally:
        release.set()
    a = await task
    assert a[2]["financial_snapshot"]["cycles"][0]["bill"]["revision"] == 1
    b = await emit(client, headers, env["database"])
    assert b[2]["financial_snapshot"]["cycles"][0]["bill"]["revision"] == 2
    assert a[2]["energy_rows"][0]["energy_kwh"] == "1000"
    assert b[2]["energy_rows"][0]["energy_kwh"] == "3000"
    assert a[2]["financial_snapshot"]["cycles"][0]["calculation"]["revision"] == 1
    assert b[2]["financial_snapshot"]["cycles"][0]["calculation"]["revision"] == 2
    assert (await client.get(a[0]["download_path"])).content == a[1]
