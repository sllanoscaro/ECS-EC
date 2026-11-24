"""002 technical executions observe committed outcomes without becoming business evidence."""

import json
from uuid import UUID, uuid4
import pytest
from backend.tests.contract.consumption.test_reception_contract import (
    BUILDING,
    PROCESS,
    publish,
)
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.reception import Reception
from ecs_ec.observability.lifecycle import Policy, Telemetry

pytestmark = pytest.mark.integration


def drain(telemetry):
    """Read the actual bounded007 queue through its byte writer, without a collector substitute."""
    payloads = []
    telemetry.logs._writer = payloads.append
    while telemetry.logs.drain_one():
        pass
    return [json.loads(payload) for payload in payloads]


async def test_partial_execution_recovery_and_logical_terminal(
    history_environment, database, clock, tmp_path, monkeypatch
):
    """Three committed categories survive failure; recovery counts all five once and reads/replays emit nothing."""
    telemetry = Telemetry(
        Policy(spool=tmp_path / "spool"), clock=clock, autostart=False
    )
    service = history_environment
    service.telemetry = telemetry
    original = service._category

    async def interrupted(attempt, building, category, *args, **kwargs):
        """Stop after three independent category commits, before CAT-04 and CAT-05."""
        if category == "CAT-04":
            raise RuntimeError("PRIVATE_SOURCE_MARKER")
        return await original(attempt, building, category, *args, **kwargs)

    monkeypatch.setattr(service, "_category", interrupted)
    attempt = uuid4()
    records = [
        record(category_id=f"CAT-{i:02}", source_id=UUID(int=i)) for i in range(1, 6)
    ]
    try:
        with pytest.raises(RuntimeError):
            await publish(service, records, attempt=attempt)
        partial = await service.read_attempt(attempt, BUILDING, PROCESS)
        assert len(
            partial.outcome.results
        ) == 3 and partial.outcome.pending_positions == (3, 4)
        recovered = Reception(
            database,
            clock,
            authorized_processes={PROCESS: {BUILDING}},
            telemetry=telemetry,
        )
        outcome = await publish(recovered, records, attempt=attempt)
        assert len(outcome.results) == 5 and all(
            r.status == "accepted" for r in outcome.results
        )
        events = drain(telemetry)
        executions = [e for e in events if e["event"] == "execution.completed"]
        terminals = [e for e in events if e["event"] == "reception.completed"]
        assert len(executions) == 2 and len(terminals) == 1
        assert (
            executions[0]["outcome"] == "unexpected_error"
            and executions[0]["counts"] is None
        )
        assert executions[0]["attempt_ref"] == executions[1]["attempt_ref"]
        assert executions[0]["execution_ref"] != executions[1]["execution_ref"]
        assert executions[1]["context_status"] == "recovered"
        assert terminals[0]["counts"]["records_accepted"] == 5
        assert "PRIVATE_SOURCE_MARKER" not in json.dumps(events)
        assert await publish(recovered, records, attempt=attempt) == outcome
        await recovered.read_attempt(attempt, BUILDING, PROCESS)
        assert drain(telemetry) == []
        duplicate = await publish(recovered, records)
        events = drain(telemetry)
        terminal = next(e for e in events if e["event"] == "reception.completed")
        assert terminal["publication_ref"] == terminals[0]["publication_ref"]
        assert terminal["attempt_ref"] != terminals[0]["attempt_ref"]
        assert all(r.status == "duplicate" for r in duplicate.results)
        assert terminal["counts"]["records_duplicate"] == 5
    finally:
        telemetry.shutdown()
        service.telemetry = None


async def test_unavailable_emitter_cannot_prevent_admission(
    history_environment, tmp_path, clock, monkeypatch
):
    """An exception from the actual007 admission adapter leaves durable002 results unchanged."""
    telemetry = Telemetry(
        Policy(spool=tmp_path / "broken"), clock=clock, autostart=False
    )
    history_environment.telemetry = telemetry

    def broken(*args, **kwargs):
        """Represent a technical failure without leaking exception content into signals."""
        raise RuntimeError("PRIVATE_TELEMETRY_ERROR")

    monkeypatch.setattr(telemetry, "begin", broken)
    try:
        assert (await publish(history_environment, [record()])).results[
            0
        ].status == "accepted"
    finally:
        telemetry.shutdown()
        history_environment.telemetry = None


async def test_early_retention_and_aggregate_signals_are_safe(
    history_environment, database, clock, tmp_path
):
    """Actual aggregate flushes, minimum-admission waits and protected withdrawals use only007 catalog codes."""
    from ecs_ec.consumption.retention import Retention

    telemetry = Telemetry(
        Policy(spool=tmp_path / "owner-signals"), clock=clock, autostart=False
    )
    history_environment.telemetry = telemetry
    try:
        first = await publish(history_environment, [record()])
        clock.advance(899)
        early = await publish(
            history_environment,
            [record(start="2025-01-01T01:00:00Z", end="2025-01-01T02:00:00Z")],
        )
        assert early.results[0].reason_code == "too_early"
        invalid = await publish(
            history_environment,
            [
                record(value="NaN"),
                record(unit="unsupported"),
                record(source_id=uuid4()),
            ],
        )
        assert all(result.status == "rejected" for result in invalid.results)
        withdrawn = await Retention(
            database,
            clock,
            authorized_processes={PROCESS: {BUILDING}},
            telemetry=telemetry,
        ).withdraw_detail(
            building_id=BUILDING,
            record_ids=(first.results[0].measurement_id,),
            process=PROCESS,
            reason="protected_test",
        )
        assert withdrawn[0]["reason_code"] == "protected"
        events = drain(telemetry)
        assert any(
            e["stage"] == "aggregate" and e["operation"] == "reception.accept"
            for e in events
        )
        assert any(e["stage"] == "wait" and e["code"] == "too_early" for e in events)
        assert any(
            e["event"] == "reception.completed"
            and e["outcome"] == "expected_rejection"
            and e["counts"]["records_other_rejected"] == 1
            for e in events
        )
        assert any(
            e["operation"] == "consumption.retention"
            and e["event"] == "operation.completed"
            and e["outcome"] == "expected_rejection"
            for e in events
        )
        assert any(
            event["event"] == "reception.completed"
            and event["counts"]["records_invalid"] == 3
            and event["counts"]["records_other_rejected"] == 0
            for event in events
        )
        assert not any(
            key in json.dumps(events)
            for key in [
                "source_evidence_ref",
                "energy_kwh",
                "input_manifest",
                "test:correlation",
            ]
        )
    finally:
        telemetry.shutdown()
        history_environment.telemetry = None


async def test_pending_calculation_uses_real_emitter(
    history_environment, database, clock, tmp_path
):
    """002 pending work emits safe aggregate stages and preserves the actual001 calculator's committed total."""
    from backend.tests.integration.consumption.test_pending_totals import (
        calculated_config,
        partials,
    )
    from ecs_ec.consumption.pending_totals import PendingTotals

    telemetry = Telemetry(
        Policy(spool=tmp_path / "pending-signals"), clock=clock, autostart=False
    )
    history_environment.telemetry = telemetry
    try:
        await calculated_config(database, clock)
        await publish(history_environment, partials()[:1])
        await publish(history_environment, partials()[1:])
        await PendingTotals(database, clock, telemetry=telemetry).run_due()
        events = drain(telemetry)
        aggregates = [e for e in events if e["operation"] == "consumption.aggregate"]
        assert any(
            e["event"] == "operation.completed" and e["outcome"] == "success"
            for e in aggregates
        )
        assert any(
            e["stage"] == "aggregate" and e["parent_operation_ref"] for e in aggregates
        )
    finally:
        telemetry.shutdown()
        history_environment.telemetry = None
