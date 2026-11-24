"""005 elected in-process supervisor with two bounded renders and durable crash reconciliation."""

import asyncio
import hashlib
import re
from contextlib import asynccontextmanager
from uuid import uuid4, UUID
from sqlalchemy import select, text
from ecs_ec.core.lifecycle import Module
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.retention import anniversary
from ecs_ec.reports.models import Request, Capture, Result, Binary
from ecs_ec.reports.schemas import Snapshot
from ecs_ec.reports.repository import record_failure, protect_snapshot
from ecs_ec.reports.renderer import render
from ecs_ec.reports.preflight import preflight, ValidationError
from ecs_ec.reports.layout import CompositionError
from ecs_ec.observability.context import Context


class Worker:
    """Own only report work; durable transitions and locks arbitrate multiple requests/recovery attempts."""

    def __init__(self, service):
        """Bind installed report service; keep all render computation outside async transactions."""
        self.service = service
        self.stop = asyncio.Event()
        self.tasks = []

    def continued(self, row):
        """Restore only producer-persisted trusted context; an interrupted span is never adopted as a live parent."""
        try:
            if not row.technical_context:
                return self.service.signal(
                    "begin", "report.generate", "reports", context=Context()
                )
            fields = {
                k: UUID(v) if k.endswith("_ref") and v else v
                for k, v in row.technical_context.items()
            }
            return self.service.signal(
                "continue_operation", "report.generate", "reports", Context(**fields)
            )
        except Exception:
            return self.service.signal(
                "begin", "report.generate", "reports", context=Context()
            )

    async def reconcile(self):
        """Mark previous process claims interrupted once; caller holds exclusive supervisor leadership."""
        handles = []
        try:
            async with UnitOfWork(self.service.database.sessions) as uow:
                rows = (
                    await uow.session.scalars(
                        select(Request)
                        .where(Request.state == "generando")
                        .with_for_update()
                    )
                ).all()
                for row in rows:
                    handle = self.continued(row)
                    handles.append(handle)
                    await record_failure(
                        uow, row, "generacion_interrumpida", self.service.clock
                    )
                await uow.commit()
            for handle in handles:
                self.service.signal(
                    "complete",
                    handle,
                    event="report.completed",
                    outcome="unexpected_error",
                    code="processing_interrupted",
                    duration_ms=None,
                )
        finally:
            for handle in handles:
                self.service.signal("release", handle)

    async def run_one(self):
        """Claim one pending request with SKIP LOCKED, render one copy, then publish result+bytes or failure+event."""
        handle = None
        try:
            service = self.service
            async with UnitOfWork(service.database.sessions) as uow:
                row = await uow.session.scalar(
                    select(Request)
                    .where(Request.state == "pendiente")
                    .order_by(Request.created_at, Request.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if row is None:
                    return False
                capture = await uow.session.scalar(
                    select(Capture).where(Capture.request_id == row.id)
                )
                row.state = "generando"
                row.revision += 1
                handle = self.continued(row)
                identifier = row.id
                data = capture.data
                capture_id = capture.id
                await uow.commit()
            reason = None
            content = None
            manifest = None
            facts = None
            phase = "render"
            try:
                service.signal("stage", handle, "wait")
                snapshot = Snapshot.model_validate(data)
                began = service.clock.monotonic()
                content, manifest = await asyncio.to_thread(
                    render, snapshot, identifier, service.clock.now()
                )
                service.signal(
                    "stage",
                    handle,
                    "render",
                    duration_ms=max(0, (service.clock.monotonic() - began) * 1000),
                )
                phase = "preflight"
                began = service.clock.monotonic()
                facts = await asyncio.to_thread(preflight, content, manifest)
                service.signal(
                    "stage",
                    handle,
                    "preflight",
                    duration_ms=max(0, (service.clock.monotonic() - began) * 1000),
                )
            except CompositionError:
                reason = "composicion_no_admisible"
            except ValidationError:
                reason = "validacion_documento_fallida"
            except Exception:
                reason = "generacion_no_completada"
            if reason:
                service.signal(
                    "stage",
                    handle,
                    phase,
                    outcome="unexpected_error",
                    code="processing_interrupted",
                )
            async with UnitOfWork(service.database.sessions) as uow:
                row = await uow.session.get(Request, identifier, with_for_update=True)
                if row.state != "generando":
                    service.signal("release", handle)
                    return True
                now = service.clock.now()
                if reason:
                    await record_failure(uow, row, reason, service.clock)
                else:
                    rid, bid = uuid4(), uuid4()
                    checksum = hashlib.sha256(content).hexdigest()
                    period = (
                        row.selection["date"]
                        if row.scale == "diario"
                        else f"{row.selection['year']}-{row.selection['month']:02}"
                        if row.scale == "mensual"
                        else str(row.selection["year"])
                    )
                    deadline = max(row.retain_until, anniversary(now, row.timezone))
                    from ecs_ec.consumption.catalog_storage import lock_configuration

                    await lock_configuration(uow, row.building_id)
                    await protect_snapshot(uow, snapshot, deadline)
                    row.retain_until = deadline
                    captured = await uow.session.get(Capture, capture_id)
                    captured.retain_until = max(captured.retain_until, deadline)
                    building = (
                        re.sub(r"[^A-Za-z0-9_-]+", "-", snapshot.building_name).strip(
                            "-"
                        )[:60]
                        or "edificio"
                    )
                    filename = f"ECS-EC-{building}-{row.scale}-{period}.pdf"
                    result = Result(
                        id=rid,
                        request_id=identifier,
                        snapshot_id=capture_id,
                        state="generado",
                        issued_at=now,
                        cutoff_at=row.cutoff_at,
                        filename=filename,
                        **facts,
                        layout_manifest=manifest,
                        functional_reason_code=None,
                        correlation_ref=uuid4(),
                        binary_id=bid,
                        sha256=checksum,
                        byte_length=len(content),
                        created_at=now,
                        retain_until=max(
                            row.retain_until, anniversary(now, row.timezone)
                        ),
                    )
                    uow.session.add(result)
                    await uow.session.flush()
                    uow.session.add(
                        Binary(
                            id=bid,
                            result_id=rid,
                            content_type="application/pdf",
                            content=content,
                            sha256=checksum,
                            byte_length=len(content),
                        )
                    )
                    row.state = "generado"
                    row.revision += 1
                await uow.commit()
            service.signal(
                "stage",
                handle,
                "publish",
                outcome="unexpected_error" if reason else "success",
                code="processing_interrupted" if reason else "ok",
            )
            service.signal(
                "complete",
                handle,
                event="report.completed",
                outcome="unexpected_error" if reason else "success",
                code="processing_interrupted" if reason else "ok",
            )
            return True
        finally:
            self.service.signal("release", handle)

    async def slot(self):
        """Run one capacity slot; transient DB errors preserve claims for elected restart reconciliation."""
        while not self.stop.is_set():
            try:
                if await self.run_one():
                    continue
            except Exception:
                pass
            try:
                await asyncio.wait_for(self.stop.wait(), 0.2)
            except TimeoutError:
                pass


def reports_module():
    """Register only005's supervisor in the existing009 lifecycle; other modules remain independent."""

    @asynccontextmanager
    async def lifespan(app):
        """Hold session leadership across both slots, reconcile once and join renders before the DB closes."""
        service = app.state.reports
        service.telemetry = getattr(app.state, "telemetry", None)
        worker = Worker(service)
        app.state.report_worker = worker
        async with service.database.engine.connect() as leader:
            acquired = await leader.scalar(text("SELECT pg_try_advisory_lock(5005009)"))
            await leader.commit()
            tasks = []
            try:
                if acquired:
                    await worker.reconcile()
                    tasks = [
                        asyncio.create_task(worker.slot(), name=f"reports-{i}")
                        for i in range(2)
                    ]
                    worker.tasks = tasks
                yield
            finally:
                worker.stop.set()
                if tasks:
                    await asyncio.gather(*tasks)
                if acquired:
                    await leader.execute(text("SELECT pg_advisory_unlock(5005009)"))
                    await leader.commit()

    return Module("reports", lifespan=lifespan)
