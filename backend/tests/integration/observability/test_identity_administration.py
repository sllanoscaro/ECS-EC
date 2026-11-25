"""007 validates real006/001 and authorized004 administration, early denials and rollback without duplicating owner emissions."""

from backend.tests.integration.identity.test_telemetry import (
    test_login_authorization_mutation_recovery_signals as test_login_authorization_mutation_recovery_signals,
    test_mutation_and_authorization_survive_technical_failure as test_mutation_and_authorization_survive_technical_failure,
    test_unexpected_hash_failure_is_safe_terminal as test_unexpected_hash_failure_is_safe_terminal,
    test_concurrent_recoveries_keep_contexts_separate as test_concurrent_recoveries_keep_contexts_separate,
)
from backend.tests.integration.consumption.test_telemetry import (
    test_detail_terminals_and_sensitive_input_isolation as test_detail_terminals_and_sensitive_input_isolation,
    test_configuration_commit_and_saturated_queue as test_configuration_commit_and_saturated_queue,
)


import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.integration.consumption.test_history_telemetry import drain
from ecs_ec.observability.lifecycle import Policy, Telemetry


@pytest.mark.parametrize(
    "role,status", [("operador", 403), ("administrador_tecnico", 200)]
)
async def test_history_target_and_authorization_are_separate(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    role,
    status,
):
    """Exactly one target terminal accompanies real006 history reads/denials, independently of policy decisions."""
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "history"), autostart=False
    )
    costs_client._transport.app.state.telemetry = telemetry
    try:
        await authenticate(
            costs_client, account_factory, session_factory, identity_settings, role
        )
        response = await costs_client.get("/api/v1/identity/administration-history")
        assert response.status_code == status
        events = drain(telemetry)
        target = [
            e
            for e in events
            if e["operation"] == "administration.query"
            and e["event"] == "operation.completed"
        ]
        assert len(target) == 1
        assert target[0]["outcome"] == (
            "success" if status == 200 else "expected_rejection"
        )
        assert any(
            e["operation"] == "identity.authorize"
            and e["event"] == "operation.completed"
            for e in events
        )
    finally:
        telemetry.shutdown()


@pytest.mark.parametrize(
    "path,operation",
    [
        ("/api/v1/costs/profiles", "administration.change"),
        ("/api/v1/costs/calculations", "cost.calculate"),
        ("/api/v1/reports", "report.generate"),
    ],
)
async def test_invalid_body_before_owner_emits_one_target(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    path,
    operation,
):
    """Framework validation must remain observable without inventing a generation or calling a rejected owner."""
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "validation"), autostart=False
    )
    costs_client._transport.app.state.telemetry = telemetry
    try:
        headers = await authenticate(
            costs_client, account_factory, session_factory, identity_settings
        )
        response = await costs_client.post(
            path, json={"unexpected": "PRIVATE_INVALID_PAYLOAD"}, headers=headers
        )
        assert response.status_code == 422
        events = drain(telemetry)
        target = [
            e
            for e in events
            if e["operation"] == operation and e["event"] == "operation.completed"
        ]
        assert len(target) == 1 and target[0]["outcome"] == "expected_rejection"
        assert not any(
            e["event"] in {"report.admitted", "report.completed"} for e in events
        )
        assert "PRIVATE_INVALID_PAYLOAD" not in str(events)
    finally:
        telemetry.shutdown()


async def test_real_costs_rollback_has_no_success_or_orphan_evidence(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
):
    """A failure after004's evidence flush rolls back business009 rows and has one unexpected target terminal."""
    from backend.tests.contract.costs.test_calculations_api import prepared
    from ecs_ec.costs.adapters import Evidence
    from ecs_ec.costs.models import Calculation
    from ecs_ec.audit.models import AuditRecord
    from sqlalchemy import select, func

    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "rollback"), autostart=False
    )
    app = costs_client._transport.app
    app.state.telemetry = telemetry
    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    original = Evidence.append

    async def interrupted(self, *args, **kwargs):
        """Raise after the actual writer has flushed, allowing004's UoW to prove rollback."""
        await original(self, *args, **kwargs)
        raise RuntimeError("PRIVATE_COST_AUDIT_MARKER")

    monkeypatch.setattr(Evidence, "append", interrupted)
    costs_client._transport.raise_app_exceptions = False
    try:
        response = await costs_client.post(
            "/api/v1/costs/calculations", json=body, headers=headers
        )
        assert (
            response.status_code == 500
            and "PRIVATE_COST_AUDIT_MARKER" not in response.text
        )
        async with costs_environment["database"].sessions() as session:
            assert (
                await session.scalar(select(func.count()).select_from(Calculation)) == 0
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AuditRecord)
                    .where(AuditRecord.action == "costs.calculation.created")
                )
                == 0
            )
        events = drain(telemetry)
        target = [
            event
            for event in events
            if event["operation"] == "cost.calculate"
            and event["event"] == "operation.completed"
        ]
        assert len(target) == 1 and target[0]["outcome"] == "unexpected_error"
        assert not any(
            event["operation"] == "cost.calculate" and event["stage"] == "commit"
            for event in events
        )
    finally:
        telemetry.shutdown()


async def test_actual004_supply_and_profile_administration(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
):
    """Real004 supply/calendar creation, revision/replay/conflicts have one typed target terminal per attempted request."""
    from backend.tests.contract.costs.test_profiles_api import (
        test_supply_and_profile_replay_preconditions as actual_case,
    )

    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "profile-signals"), autostart=False
    )
    costs_client._transport.app.state.telemetry = telemetry
    try:
        await actual_case(
            costs_client, account_factory, session_factory, identity_settings
        )
        events = drain(telemetry)
        changes = [
            event
            for event in events
            if event["operation"] == "administration.change"
            and event["event"] == "operation.completed"
        ]
        assert len(changes) == 10
        assert {event["outcome"] for event in changes} == {
            "success",
            "expected_rejection",
        }
        assert all(event["source_module"] == "costs" for event in changes)
        assert len({event["operation_ref"] for event in changes}) == len(changes)
        assert any(
            event["operation"] == "administration.change" and event["stage"] == "commit"
            for event in events
        )
        assert any(
            event["operation"] == "identity.authorize"
            and event["event"] == "operation.completed"
            for event in events
        )
    finally:
        telemetry.shutdown()


async def test_actual002_aggregate_query_target(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
):
    """The installed002 aggregate route is observed once with its actual projection, independently of006 decisions."""
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "aggregate-query"), autostart=False
    )
    costs_client._transport.app.state.telemetry = telemetry
    try:
        await authenticate(
            costs_client,
            account_factory,
            session_factory,
            identity_settings,
            "operador",
        )
        response = await costs_client.get(
            "/api/v1/consumption/categories/CAT-05/aggregates",
            params={
                "start": "2025-12-31T21:00:00-03:00",
                "end": "2026-01-01T21:00:00-03:00",
                "timezone": "America/Santiago",
                "granularity": "day",
            },
        )
        assert response.status_code == 200, response.text
        events = drain(telemetry)
        target = [
            event
            for event in events
            if event["operation"] == "consumption.query_aggregates"
            and event["event"] == "operation.completed"
        ]
        assert len(target) == 1 and target[0]["outcome"] == "success"
    finally:
        telemetry.shutdown()
