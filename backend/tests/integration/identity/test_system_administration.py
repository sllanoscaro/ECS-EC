"""Partial006 administration integration against real001/002/004; PDF005 remains an explicit unmet gate."""

from uuid import UUID
import pytest
from sqlalchemy import select
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.integration.identity.test_read_integrations import business_state
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import IncorporatedRecord

pytestmark = pytest.mark.integration


async def test_administrative_admission_and_duplicate_source(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Anonymous/Operator cannot reach maintenance; invalid source reuse leaves the committed revision intact."""
    client, env = costs_client, costs_environment
    await prepared(env)
    for method, path in [
        ("get", "/consumption/configuration"),
        ("get", "/costs/supply"),
        ("get", "/costs/profiles"),
        ("put", "/consumption/configuration"),
        ("put", "/costs/supply"),
        ("post", "/costs/profiles"),
        ("post", "/costs/calculations"),
        ("post", "/costs/bills"),
    ]:
        response = await getattr(client, method)("/api/v1" + path)
        assert response.status_code == 401
    await authenticate(
        client, account_factory, session_factory, identity_settings, "operador"
    )
    before = await business_state(env["database"])
    for method, path in [
        ("get", "/consumption/configuration"),
        ("get", "/costs/supply"),
        ("get", "/costs/profiles"),
        ("put", "/consumption/configuration"),
        ("put", "/costs/supply"),
        ("post", "/costs/profiles"),
        ("post", "/costs/calculations"),
        ("post", "/costs/bills"),
    ]:
        response = await getattr(client, method)("/api/v1" + path)
        assert response.status_code == 403
    assert await business_state(env["database"]) == before
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    current = (await client.get("/api/v1/consumption/configuration")).json()
    command = dict(
        expected_revision=current["revision"],
        effective_from=None,
        timezone=current["timezone"],
        categories=[
            {k: v for k, v in entry.items() if k != "category_revision"}
            for entry in current["categories"]
        ],
    )
    command["categories"][4]["source_id"] = command["categories"][2]["source_id"]
    response = await client.put(
        "/api/v1/consumption/configuration", json=command, headers=headers
    )
    assert response.status_code in (409, 422)
    assert (await client.get("/api/v1/consumption/configuration")).json() == current
    assert await business_state(env["database"]) == before


async def test_mandatory_retention_is_not_an_editable_identity_setting(
    costs_environment,
):
    """The actual002 retention provider rejects removal before its calendar deadline, without any006 settings API."""
    from ecs_ec.consumption.retention import Retention

    env = costs_environment
    await prepared(env)
    async with UnitOfWork(env["database"].sessions) as uow:
        record = await uow.session.scalar(
            select(IncorporatedRecord).where(IncorporatedRecord.category_id == "CAT-01")
        )
        identifier = record.id
    result = await Retention(
        env["database"],
        env["clock"],
        authorized_processes={"process:identity_test": {UUID(int=99)}},
    ).withdraw_detail(
        building_id=UUID(int=99),
        record_ids=(identifier,),
        process="process:identity_test",
        reason="protected_fixture",
    )
    assert result[0]["reason_code"] == "protected"


async def test_invalid_mutation_does_not_extend_activity(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Explicit dependencies do not turn a rejected malformed body into interactive session activity."""
    from ecs_ec.identity.models import Session
    from ecs_ec.identity.security import digest

    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    bearer = costs_client.cookies["ecs_ec_session"]
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        row = await uow.session.scalar(
            select(Session).where(Session.token_digest == digest(bearer))
        )
        previous = (row.last_activity_at, row.idle_expires_at)
    costs_environment["clock"].advance(29 * 60)
    response = await costs_client.put(
        "/api/v1/consumption/configuration", json={"malformed": True}, headers=headers
    )
    assert response.status_code == 422
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        row = await uow.session.scalar(
            select(Session).where(Session.token_digest == digest(bearer))
        )
        assert (row.last_activity_at, row.idle_expires_at) == previous


async def test_reception_minimum_is_enforced_by_real002(costs_environment):
    """No006 setting can bypass fifteen minutes; a fresh valid interval is rejected at899 seconds and admitted at900."""
    from backend.tests.contract.consumption.test_reception_contract import publish
    from backend.tests.unit.consumption.test_validation import record

    env = costs_environment
    first = await publish(env["reception"], [record()])
    assert first.results[0].status == "accepted"
    env["clock"].advance(899)
    next_record = record(start="2025-01-01T01:00:00Z", end="2025-01-01T02:00:00Z")
    early = await publish(env["reception"], [next_record])
    assert (
        early.results[0].status == "rejected"
        and early.results[0].reason_code == "too_early"
    )
    env["clock"].advance(1)
    assert (await publish(env["reception"], [next_record])).results[
        0
    ].status == "accepted"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/consumption/configuration"),
        ("POST", "/costs/profiles"),
        ("PUT", "/costs/supply"),
    ],
)
@pytest.mark.parametrize("failure", ["anonymous", "operator", "csrf", "origin"])
async def test_each_denied_attempt_has_one_trusted_audit(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    method,
    path,
    failure,
):
    """Real route denials precede payload parsing; actor, unchanged business state and calendar protection are durable."""
    from ecs_ec.audit.models import AuditRecord
    from ecs_ec.core.retention import anniversary

    env, client = costs_environment, costs_client
    await prepared(env)
    headers = {}
    actor = "unauthenticated"
    if failure != "anonymous":
        headers = await authenticate(
            client,
            account_factory,
            session_factory,
            identity_settings,
            "operador" if failure == "operator" else "administrador_tecnico",
        )
        actor = (
            "account:"
            + (await client.get("/api/v1/auth/session")).json()["account"]["id"]
        )
    # GET has no CSRF/origin requirement: use revoked cookies for those two denial cases.
    if method == "GET" and failure in {"csrf", "origin"}:
        client.cookies.set("ecs_ec_session", "invalid-session")
        actor = "unauthenticated"
    if failure == "csrf":
        headers.pop("X-CSRF-Token", None)
    if failure == "origin":
        headers["Origin"] = "https://untrusted.example.test"
    before = await business_state(env["database"])
    response = await client.request(
        method, "/api/v1" + path, json={} if method != "GET" else None, headers=headers
    )
    assert response.status_code == (401 if actor == "unauthenticated" else 403)
    operation = response.json()["operation_ref"]
    async with UnitOfWork(env["database"].sessions) as uow:
        rows = (
            await uow.session.scalars(
                select(AuditRecord).where(
                    AuditRecord.safe_payload["operation_ref"].astext == operation
                )
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].actor_ref == actor and rows[0].result == "denied"
        assert rows[0].retain_until >= anniversary(
            rows[0].recorded_at, "America/Santiago"
        )
    assert await business_state(env["database"]) == before


async def test_database_failure_does_not_claim_durable_denial(
    costs_client, costs_environment, monkeypatch
):
    """When the actual audit writer cannot persist, HTTP503 carries no assertion of durable rejection."""
    from ecs_ec.identity.services import Identity

    async def unavailable(*args, **kwargs):
        """Fail only at the owner006 audit persistence boundary, without exposing database details."""
        raise RuntimeError("PRIVATE_DATABASE_LOCATION")

    monkeypatch.setattr(Identity, "rejection", unavailable)
    before = await business_state(costs_environment["database"])
    response = await costs_client.get("/api/v1/consumption/configuration")
    assert (
        response.status_code == 503
        and response.json()["code"] == "identity_unavailable"
    )
    assert "PRIVATE_DATABASE_LOCATION" not in response.text
    assert await business_state(costs_environment["database"]) == before


async def test_configuration_evidence_failure_rolls_back_whole_change(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """A failed009 event after the real001 audit flush leaves no revision, orphan event or allowed audit."""
    from sqlalchemy import func
    from sqlalchemy.exc import SQLAlchemyError
    from ecs_ec.audit.events import EventWriter
    from ecs_ec.audit.models import FunctionalEvent, AuditRecord

    client, env = costs_client, costs_environment
    await prepared(env)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    current = (await client.get("/api/v1/consumption/configuration")).json()
    command = dict(
        expected_revision=current["revision"],
        effective_from=None,
        timezone=current["timezone"],
        categories=[
            {k: v for k, v in entry.items() if k != "category_revision"}
            for entry in current["categories"]
        ],
    )
    command["categories"][3].update(has_meter=False, source_id=None, source_label=None)

    async def evidence_count():
        """Inspect only001's durable sources, excluding independent006 denial evidence."""
        async with UnitOfWork(env["database"].sessions) as uow:
            return (
                await uow.session.scalar(
                    select(func.count())
                    .select_from(FunctionalEvent)
                    .where(FunctionalEvent.source_module == "consumption")
                ),
                await uow.session.scalar(
                    select(func.count())
                    .select_from(AuditRecord)
                    .where(AuditRecord.action == "consumption.configuration.changed")
                ),
            )

    before = await business_state(env["database"]), await evidence_count()
    original = EventWriter.append

    async def fail_after_audit(self, uow, event):
        """Abort after an actual flush of source.changed; transaction ownership remains001's."""
        if event.event_type == "administration.changed":
            raise SQLAlchemyError("PRIVATE_DB_DETAIL")
        return await original(self, uow, event)

    monkeypatch.setattr(EventWriter, "append", fail_after_audit)
    response = await client.put(
        "/api/v1/consumption/configuration", json=command, headers=headers
    )
    assert response.status_code == 503, response.text
    assert "PRIVATE_DB_DETAIL" not in response.text
    assert (await business_state(env["database"]), await evidence_count()) == before
    assert (await client.get("/api/v1/consumption/configuration")).json() == current


async def test_actual004_audit_results_are_visible_in006_history(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """004's durable recorded result projects to006 allowed and remains filterable with its trusted actor."""
    from backend.tests.contract.costs.test_bills_comparisons_api import invoice

    client = costs_client
    body = await prepared(costs_environment)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    actor = (await client.get("/api/v1/auth/session")).json()["account"]["id"]
    calculation = await client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    bill = await client.post(
        "/api/v1/costs/bills",
        json=invoice(body),
        headers=headers | {"Idempotency-Key": "history-real-bill"},
    )
    assert calculation.status_code == bill.status_code == 201
    costs_environment["clock"].advance(1)
    for action, identifier in [
        ("costs.calculation.created", calculation.json()["id"]),
        ("costs.bill.created", bill.json()["bill_revision_id"]),
    ]:
        response = await client.get(
            "/api/v1/identity/administration-history",
            params={"action": action, "result": "allowed"},
        )
        assert response.status_code == 200
        entries = response.json()["items"]
        assert len(entries) == 1
        assert entries[0]["actor"] == {
            "kind": "account",
            "account_id": actor,
            "process_code": None,
        }
        assert (
            entries[0]["result"] == "allowed"
            and entries[0]["target"]["id"] == identifier
        )


async def test_actual004_failed_audit_projects_as_rejected(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """A committed004 failure is visible as rejected, preserving the source's failed evidence and actor."""
    from ecs_ec.costs import engine
    from ecs_ec.audit.models import AuditRecord

    body = await prepared(costs_environment)
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )

    def interrupted(*args):
        """Fail calculation inside its real owner; its durable failure handling remains active."""
        raise RuntimeError("PRIVATE_ENGINE_DETAIL")

    monkeypatch.setattr(engine, "evaluate", interrupted)
    result = await costs_client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert result.status_code == 201 and result.json()["execution_state"] == "fallido"
    costs_environment["clock"].advance(1)
    response = await costs_client.get(
        "/api/v1/identity/administration-history",
        params={"action": "costs.calculation.created", "result": "rejected"},
    )
    entries = response.json()["items"]
    assert len(entries) == 1 and entries[0]["result"] == "rejected"
    assert entries[0]["target"]["id"] == result.json()["id"]
    assert "PRIVATE_ENGINE_DETAIL" not in response.text
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        stored = await uow.session.get(AuditRecord, UUID(entries[0]["id"]))
        assert stored.result == "failed"
