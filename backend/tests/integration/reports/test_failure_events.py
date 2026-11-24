"""005 admitted failures publish result and009 event atomically, with no recursive dependency on008."""

from uuid import UUID
import pytest
from sqlalchemy import select, func
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Request, Result, Binary
from ecs_ec.reports.worker import Worker

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("boundary", ["capture", "render", "preflight"])
async def test_admitted_failure_is_atomic(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
    boundary,
):
    """Real requests fail at an internal boundary while durable result/event retain one identity and no downloadable buffer."""
    import ecs_ec.reports.services as services
    import ecs_ec.reports.worker as worker
    from ecs_ec.reports.preflight import ValidationError

    def fail(*args, **kwargs):
        """Inject a controlled runtime failure without replacing functional data providers."""
        raise (
            ValidationError("synthetic_preflight")
            if boundary == "preflight"
            else RuntimeError("synthetic_failure")
        )

    async def fail_capture(*args, **kwargs):
        """Stop005 capture before its projection is committed; producer data remains untouched."""
        raise RuntimeError("synthetic_capture_failure")

    if boundary == "capture":
        monkeypatch.setattr(services, "capture_snapshot", fail_capture)
    else:
        monkeypatch.setattr(
            worker, "render" if boundary == "render" else "preflight", fail
        )
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    response = await client.post(
        "/api/v1/reports", json={"scale": "anual", "year": 2024}, headers=headers
    )
    assert response.status_code == 202, response.text
    identifier = response.json()["id"]
    status = await terminal(client, identifier)
    assert status["state"] == "fallido"
    assert (
        await client.get("/api/v1/reports/" + identifier + "/download")
    ).status_code == 409
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        result = await uow.session.scalar(
            select(Result).where(Result.request_id == UUID(identifier))
        )
        events = (
            await uow.session.scalars(
                select(FunctionalEvent).where(
                    FunctionalEvent.event_type == "pdf.failed"
                )
            )
        ).all()
        assert len(events) == 1 and events[0].source_entity_id == result.id
        assert (
            result.binary_id is None
            and await uow.session.scalar(select(func.count()).select_from(Binary)) == 0
        )
    await client.get("/api/v1/reports/" + identifier)
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        assert (
            await uow.session.scalar(
                select(func.count())
                .select_from(FunctionalEvent)
                .where(FunctionalEvent.event_type == "pdf.failed")
            )
            == 1
        )
