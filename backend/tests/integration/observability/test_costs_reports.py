"""007 coverage consumes actual004/005 producers and compares technical signals with durable results."""

import json
import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from backend.tests.contract.costs.test_bills_comparisons_api import invoice
from backend.tests.integration.consumption.test_history_telemetry import drain
from backend.tests.integration.reports.test_observability import (
    test_one_admission_completion_and_trusted_continuation as test_one_admission_completion_and_trusted_continuation,
)
from backend.tests.integration.reports.test_costs_pdf_end_to_end import (
    test_exact_pairs_pending_correction_and_recalculation as test_exact_pairs_pending_correction_and_recalculation,
)
from backend.tests.integration.reports.test_failure_events import (
    test_admitted_failure_is_atomic as test_admitted_failure_is_atomic,
)
from ecs_ec.observability.lifecycle import Policy, Telemetry

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("failed", [False, True])
async def test_cost_results_and_queries_match_spans(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
    failed,
):
    """Persisted engine failures stay HTTP201 but technical ERROR; expected denial and reads have distinct terminals."""
    app = costs_client._transport.app
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "004"),
        clock=costs_environment["clock"],
        autostart=False,
    )
    app.state.telemetry = telemetry
    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    if failed:
        from ecs_ec.costs import engine

        def fail(*args, **kwargs):
            """Interrupt only arithmetic, leaving real capture, rollback and durable failure publication active."""
            raise RuntimeError("PRIVATE_ENGINE_INPUT_MARKER")

        monkeypatch.setattr(engine, "evaluate", fail)
    try:
        response = await costs_client.post(
            "/api/v1/costs/calculations", json=body, headers=headers
        )
        assert response.status_code == 201, response.text
        calculation = response.json()
        assert calculation["execution_state"] == ("fallido" if failed else "completado")
        assert (
            await costs_client.get("/api/v1/costs/calculations/" + calculation["id"])
        ).status_code == 200
        if not failed:
            headers["Idempotency-Key"] = "bill-007"
            bill = (
                await costs_client.post(
                    "/api/v1/costs/bills", json=invoice(body), headers=headers
                )
            ).json()
            headers["Idempotency-Key"] = "compare-007"
            compared = await costs_client.post(
                "/api/v1/costs/comparisons",
                json={
                    "calculation_id": calculation["id"],
                    "bill_revision_id": bill["bill_revision_id"],
                },
                headers=headers,
            )
            assert compared.status_code == 201, compared.text
            assert compared.json()["delta_amount"] == "0"
        events = drain(telemetry)
        terminal = [
            e
            for e in events
            if e["event"] == "operation.completed"
            and e["operation"] == "cost.calculate"
        ]
        assert len(terminal) == 1
        assert terminal[0]["outcome"] == ("unexpected_error" if failed else "success")
        assert {e["stage"] for e in events if e["operation"] == "cost.calculate"} >= {
            "capture",
            "calculate",
            "commit",
        }
        assert any(
            e["operation"] == "cost.query" and e["event"] == "operation.completed"
            for e in events
        )
        if not failed:
            assert any(
                e["operation"] == "cost.compare" and e["event"] == "operation.completed"
                for e in events
            )
            assert any(
                e["source_module"] == "costs"
                and e["operation"] == "administration.change"
                and e["outcome"] == "success"
                for e in events
            )
        spans = telemetry.traces.take_batch()
        span = next(
            s
            for s in spans
            if format(s.context.span_id, "016x") == terminal[0]["span_id"]
        )
        assert span.attributes["outcome"] == terminal[0]["outcome"]
        assert "PRIVATE_ENGINE_INPUT_MARKER" not in json.dumps(events) + str(
            [dict(s.attributes) for s in spans]
        )
    finally:
        telemetry.shutdown()


async def test_live_costs_pdf_and_identity_traces(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    live_telemetry,
    deliver_telemetry,
):
    """Real004 calculation/contrast,005 generation/download and006 history persist in both external signals."""
    from backend.tests.contract.reports.test_reports_api import terminal

    app = costs_client._transport.app
    app.state.telemetry = app.state.reports.telemetry = live_telemetry
    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    calculation = await costs_client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert calculation.status_code == 201, calculation.text
    headers["Idempotency-Key"] = "live-bill-007"
    bill = await costs_client.post(
        "/api/v1/costs/bills", json=invoice(body), headers=headers
    )
    assert bill.status_code == 201, bill.text
    headers["Idempotency-Key"] = "live-comparison-007"
    compared = await costs_client.post(
        "/api/v1/costs/comparisons",
        json={
            "calculation_id": calculation.json()["id"],
            "bill_revision_id": bill.json()["bill_revision_id"],
        },
        headers=headers,
    )
    assert compared.status_code == 201, compared.text
    assert (
        await costs_client.get("/api/v1/costs/calculations/" + calculation.json()["id"])
    ).status_code == 200
    headers["Idempotency-Key"] = "live-pdf-007"
    request = await costs_client.post(
        "/api/v1/reports", json={"scale": "anual", "year": 2024}, headers=headers
    )
    assert request.status_code == 202, request.text
    result = await terminal(costs_client, request.json()["id"])
    assert result["state"] == "generado"
    assert (await costs_client.get(result["download_path"])).content.startswith(
        b"%PDF-"
    )
    assert (
        await costs_client.get("/api/v1/identity/administration-history")
    ).status_code == 200
    events, stored = await deliver_telemetry(live_telemetry)
    completed = {
        event["operation"]
        for event in stored
        if event["event"] in {"operation.completed", "report.completed"}
    }
    assert {
        "cost.calculate",
        "cost.compare",
        "cost.query",
        "report.generate",
        "report.query",
        "report.download",
        "identity.authorize",
        "administration.change",
        "administration.query",
    } <= completed
    assert len([e for e in events if e["event"] == "report.completed"]) == 1
    assert len([e for e in events if e["event"] == "report.admitted"]) == 1


@pytest.mark.parametrize("boundary", ["capture", "render", "preflight"])
async def test_admitted_pdf_failure_signals_match_durable_event(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
    boundary,
):
    """Each real005 failure is durably proved by its owner and has one safe terminal in007."""
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "pdf-failure"), autostart=False
    )
    app = costs_client._transport.app
    app.state.telemetry = app.state.reports.telemetry = telemetry
    try:
        await test_admitted_failure_is_atomic(
            costs_client,
            costs_environment,
            account_factory,
            session_factory,
            identity_settings,
            monkeypatch,
            boundary,
        )
        events = drain(telemetry)
        completed = [event for event in events if event["event"] == "report.completed"]
        assert len(completed) == 1 and completed[0]["outcome"] == "unexpected_error"
        assert (
            len([event for event in events if event["event"] == "report.admitted"]) == 1
        )
        assert not any(
            event["event"] == "operation.completed"
            and event["operation"] == "report.generate"
            for event in events
        )
        assert "synthetic_capture_failure" not in json.dumps(events)
    finally:
        telemetry.shutdown()
