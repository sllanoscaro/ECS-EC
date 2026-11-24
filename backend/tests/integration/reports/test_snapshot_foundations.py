"""005 immutable PostgreSQL capture/result constraints and coherent admission across real002/004 readers."""

import asyncio
from uuid import uuid4, UUID
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Request, Capture, Result, Binary
from ecs_ec.reports.schemas import Snapshot

pytestmark = pytest.mark.integration


async def request_report(
    client, account_factory, session_factory, identity_settings, body=None
):
    """Admit via the real protected API and wait for a real terminal result; return stable resource identity."""
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    headers["Idempotency-Key"] = uuid4().hex
    response = await client.post(
        "/api/v1/reports",
        json=body or {"scale": "anual", "year": 2024},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    identifier = UUID(response.json()["id"])
    status = await terminal(client, str(identifier))
    assert status["state"] == "generado", status
    return identifier, headers, status


async def test_snapshot_and_binary_are_immutable(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Direct SQL mutation or deletion of confirmed snapshot/bytes fails; schema remains typed and complete."""
    identifier, _, _ = await request_report(
        costs_client, account_factory, session_factory, identity_settings
    )
    db = costs_environment["database"]
    async with UnitOfWork(db.sessions) as uow:
        snapshot = await uow.session.scalar(
            select(Capture).where(Capture.request_id == identifier)
        )
        assert len(Snapshot.model_validate(snapshot.data).energy_rows) == 7
        sid = snapshot.id
    for statement in [
        "UPDATE report_snapshot SET functional_hash='changed' WHERE id=:id",
        "DELETE FROM report_snapshot WHERE id=:id",
    ]:
        async with UnitOfWork(db.sessions) as uow:
            with pytest.raises(DBAPIError):
                await uow.session.execute(text(statement), {"id": sid})
                await uow.commit()
    async with UnitOfWork(db.sessions) as uow:
        result = await uow.session.scalar(
            select(Result).where(Result.request_id == identifier)
        )
        binary = await uow.session.get(Binary, result.binary_id)
        assert (
            binary.byte_length == len(binary.content) and binary.sha256 == result.sha256
        )
        binary.content = b"%PDF-corrupt"
        with pytest.raises(DBAPIError):
            await uow.commit()


async def test_concurrent_same_key_is_one_generation(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Concurrent authorized retries share one committed request and immutable capture under the actor/key lock."""
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    body = {"scale": "anual", "year": 2024}
    responses = await asyncio.gather(
        *(client.post("/api/v1/reports", json=body, headers=headers) for _ in range(3))
    )
    assert [r.status_code for r in responses] == [202, 202, 202], [
        r.text for r in responses
    ]
    assert len({r.json()["id"] for r in responses}) == 1
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        assert len((await uow.session.scalars(select(Request))).all()) == 1
        assert len((await uow.session.scalars(select(Capture))).all()) == 1
