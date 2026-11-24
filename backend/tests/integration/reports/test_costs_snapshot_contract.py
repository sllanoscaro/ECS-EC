"""005 obtains available60 and paired40/38/2 from actual004 calculations, bills and comparisons."""

import pytest
from uuid import UUID
from backend.tests.costs_fixtures import seed_supply
from backend.tests.unit.consumption.test_validation import record
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.costs.test_bills_comparisons_api import invoice
from backend.tests.integration.reports.test_costs_pdf_end_to_end import emit

pytestmark = pytest.mark.integration


async def test_available_and_paired_scopes_are_distinct(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Three actual closed cycles contribute60; only first/third contribute40calculated,38billed and2difference."""
    env = costs_environment
    client = costs_client
    supply = await seed_supply(env["database"], env["clock"], price="1")
    starts = ["00:00", "00:15", "00:30"]
    ends = ["00:15", "00:30", "00:45"]
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                value=str(v),
                start=f"2026-01-01T{s}:00Z",
                end=f"2026-01-01T{e}:00Z",
            )
            for v, s, e in zip((10, 20, 30), starts, ends)
        ],
    )
    env["clock"].advance(3600)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    for i, (start, end) in enumerate(zip(starts, ends)):
        body = dict(
            supply_id=str(supply.id),
            start_at=f"2026-01-01T{start}:00Z",
            end_at=f"2026-01-01T{end}:00Z",
            timezone="America/Santiago",
            boundary_criterion="synthetic:exact",
        )
        calc = await client.post(
            "/api/v1/costs/calculations",
            json=body,
            headers=headers | {"Idempotency-Key": f"calc-{i}"},
        )
        assert calc.status_code == 201, calc.text
        if i != 1:
            bill = await client.post(
                "/api/v1/costs/bills",
                json=invoice(body, amount=str(9 if i == 0 else 29))
                | {"external_identifier": f"synthetic-paired-{i}"},
                headers=headers | {"Idempotency-Key": f"bill-{i}"},
            )
            assert bill.status_code == 201, bill.text
            pair = await client.post(
                "/api/v1/costs/comparisons",
                json={
                    "calculation_id": calc.json()["id"],
                    "bill_revision_id": bill.json()["bill_revision_id"],
                },
                headers=headers | {"Idempotency-Key": f"pair-{i}"},
            )
            assert pair.status_code == 201, pair.text
    result = await emit(client, headers, env["database"])
    f = result[2]["financial_snapshot"]
    assert len(f["cycles"]) == 3 and f["available_totals"][0]["amount"] == "60"
    paired = f["comparison_totals"][0]
    assert (
        paired["cycle_count"],
        paired["calculated"],
        paired["billed"],
        paired["delta_amount"],
    ) == (2, "40", "38", "2")


@pytest.mark.parametrize(
    "start,end,count",
    [
        ("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", 1),
        ("2025-12-31T23:00:00Z", "2026-01-01T01:00:00Z", 0),
    ],
)
async def test_effective_close_uses_half_open_bounds(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    start,
    end,
    count,
):
    """A real cycle belongs at its close, including the lower boundary and excluding the upper boundary."""
    from backend.tests.contract.costs.test_calculations_api import prepared
    from ecs_ec.consumption.models import instant

    env = costs_environment
    body = await prepared(env)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    result = await costs_client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert result.status_code == 201, result.text
    service = costs_client._transport.app.state.costs
    principal = await service.identity.resolve_session(
        costs_client.cookies["ecs_ec_session"]
    )
    captured = await service.read_snapshot(
        env["building_id"], instant(start), instant(end), env["clock"].now(), principal
    )
    assert len(captured.cycles) == count
