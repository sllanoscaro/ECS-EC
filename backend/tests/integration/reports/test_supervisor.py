"""005 bounded real render execution, interrupted-claim recovery and transactional failure evidence."""

import asyncio, threading
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, func
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.audit.events import EventWriter
from ecs_ec.reports.models import Request, Result, Binary
from ecs_ec.reports.worker import Worker

pytestmark = pytest.mark.integration


async def test_reconciliation_is_atomic_and_idempotent(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
    tmp_path,
):
    """A rolled-back pdf.failed leaves the claim retryable; two subsequent reconciliations append just one failure."""
    client = costs_client
    service = client._transport.app.state.reports
    from ecs_ec.observability.lifecycle import Telemetry, Policy

    telemetry = Telemetry(Policy(environment="test", spool=tmp_path), autostart=False)
    service.telemetry = telemetry
    active = client._transport.app.state.report_worker
    active.stop.set()
    await asyncio.gather(*active.tasks)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    response = await client.post(
        "/api/v1/reports", json={"scale": "anual", "year": 2024}, headers=headers
    )
    identifier = UUID(response.json()["id"])
    async with UnitOfWork(service.database.sessions) as uow:
        row = await uow.session.get(Request, identifier, with_for_update=True)
        row.state = "generando"
        row.revision += 1
        await uow.commit()
    original = EventWriter.append

    async def fail(self, uow, event):
        """Abort the actual producer transaction after failed result flush, before its event can commit."""
        if event.event_type == "pdf.failed":
            raise RuntimeError("synthetic_event_failure")
        return await original(self, uow, event)

    monkeypatch.setattr(EventWriter, "append", fail)
    with pytest.raises(RuntimeError):
        await Worker(service).reconcile()
    assert len(telemetry.traces._active) == 0
    async with UnitOfWork(service.database.sessions) as uow:
        assert (await uow.session.get(Request, identifier)).state == "generando"
        assert await uow.session.scalar(select(func.count()).select_from(Result)) == 0
    monkeypatch.setattr(EventWriter, "append", original)
    await Worker(service).reconcile()
    await Worker(service).reconcile()
    status = (await client.get("/api/v1/reports/" + str(identifier))).json()
    assert status["functional_reason_code"] == "generacion_interrumpida"
    async with UnitOfWork(service.database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Result)) == 1
        assert (
            await uow.session.scalar(
                select(func.count())
                .select_from(FunctionalEvent)
                .where(FunctionalEvent.event_type == "pdf.failed")
            )
            == 1
        )
        assert await uow.session.scalar(select(func.count()).select_from(Binary)) == 0

    telemetry.shutdown()
    service.telemetry = None


async def test_supervisor_has_two_actual_render_slots(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """Three real requests can claim at most two CPU renderers while the third remains durably pending."""
    import ecs_ec.reports.worker as module

    original = module.render
    release = threading.Event()
    lock = threading.Lock()
    started = threading.Event()
    active = 0
    maximum = 0

    def blocked(*args):
        """Count concurrent real render calls without holding a DB transaction or replacing their output."""
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
            if active == 2:
                started.set()
        try:
            if not release.wait(10):
                raise RuntimeError("synthetic_barrier_timeout")
            return original(*args)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(module, "render", blocked)
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    identifiers = []
    try:
        for _ in range(3):
            response = await client.post(
                "/api/v1/reports",
                json={"scale": "anual", "year": 2024},
                headers=headers | {"Idempotency-Key": uuid4().hex},
            )
            assert response.status_code == 202, response.text
            identifiers.append(response.json()["id"])
        assert await asyncio.to_thread(started.wait, 5)
        async with UnitOfWork(costs_environment["database"].sessions) as uow:
            assert (
                await uow.session.scalar(
                    select(func.count())
                    .select_from(Request)
                    .where(Request.state == "generando")
                )
                == 2
            )
            assert (
                await uow.session.scalar(
                    select(func.count())
                    .select_from(Request)
                    .where(Request.state == "pendiente")
                )
                == 1
            )
    finally:
        release.set()
    for identifier in identifiers:
        assert (await terminal(client, identifier))["state"] == "generado"
    assert maximum == 2
