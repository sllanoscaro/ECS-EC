"""005 authorization, durable admission and protected reads; render workers never recapture mutable sources."""

import hashlib
from uuid import uuid4
from sqlalchemy import select, text
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.retention import anniversary
from ecs_ec.reports.models import Request, Capture, Result, Binary
from ecs_ec.reports.calendar import window
from ecs_ec.reports.snapshots import capture_snapshot
from ecs_ec.reports.repository import (
    ReportsProblem,
    canonical_hash,
    functional_hash,
    record_failure,
    protect_snapshot,
)


class Reports:
    """Compose installed006/002/004/009 services, with optional007 telemetry and a separate bounded supervisor."""

    def __init__(self, database, clock, identity, consumption, costs):
        """Keep internal providers; no network, database session or renderer is opened during construction."""
        self.database, self.clock, self.identity, self.consumption, self.costs = (
            database,
            clock,
            identity,
            consumption,
            costs,
        )
        self.telemetry = None

    def signal(self, method, *args, **kwargs):
        """Treat every telemetry call as best effort; failure cannot change a functional commit or response."""
        try:
            if self.telemetry:
                return getattr(self.telemetry, method)(*args, **kwargs)
        except Exception:
            pass

    def view(self, row, result=None):
        """Expose only approved metadata, never snapshot/source values, requester identity or internal geometry."""
        return dict(
            id=str(row.id),
            scale=row.scale,
            window=dict(
                start=row.window_start.isoformat(), end=row.window_end.isoformat()
            ),
            timezone=row.timezone,
            cutoff_at=row.cutoff_at.isoformat(),
            state=row.state,
            created_at=row.created_at.isoformat(),
            issued_at=result.issued_at.isoformat() if result else None,
            filename=result.filename if result else None,
            functional_reason_code=result.functional_reason_code if result else None,
            download_path=f"/api/v1/reports/{row.id}/download"
            if row.state == "generado"
            else None,
            sha256=result.sha256 if result else None,
            byte_length=result.byte_length if result else None,
        )

    async def admit(self, principal, selection, key):
        """Authorize before replay, serialize each actor/key and confirm selection plus immutable capture before202."""
        building = self.identity.settings.building_id
        self.identity.authorize(principal, "reports.generate", building)
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 100
            or any(ord(c) < 33 or ord(c) > 126 for c in key)
        ):
            raise ReportsProblem(
                "idempotency_key_required",
                422,
                [
                    dict(
                        path="Idempotency-Key",
                        code="required",
                        message="Indique una clave de solicitud válida.",
                    )
                ],
            )
        lock = int(canonical_hash([str(principal.account_id), key])[:15], 16)
        # Acquire session leadership before opening the repeatable capture, so a waiter sees the winner's commit.
        async with self.database.engine.connect() as leader:
            await leader.execute(text("SELECT pg_advisory_lock(:key)"), {"key": lock})
            await leader.commit()
            try:
                return await self._admit_locked(principal, selection, key, building)
            finally:
                await leader.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": lock}
                )
                await leader.commit()

    async def _admit_locked(self, principal, selection, key, building):
        """Capture only after the absent-row actor/key lock is acquired; release transaction before rendering."""
        body = selection.model_dump(mode="json", exclude_none=True)
        body_hash = canonical_hash(body)
        # Persist producer-owned trusted opaque context separately from all functional snapshot/hash/PDF data.
        handle = None
        try:
            async with UnitOfWork(self.database.sessions) as uow:
                await uow.session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                )
                from ecs_ec.identity.models import Account, Session
                from ecs_ec.identity.schemas import Principal
                from ecs_ec.identity.errors import IdentityProblem
                from ecs_ec.consumption.catalog_storage import BuildingRow

                account = await uow.session.get(
                    Account, principal.account_id, with_for_update=True
                )
                session = await uow.session.get(
                    Session, principal.session_id, with_for_update=True
                )
                if not self.identity.session_valid(account, session, self.clock.now()):
                    raise IdentityProblem("session_required", 401)
                principal = Principal.from_rows(account, session, building)
                self.identity.authorize(principal, "reports.generate", building)
                # 005 freezes reads inRR; this is evidence protection, never001 reconfiguration.
                await uow.session.get(BuildingRow, building, with_for_update=True)
                previous = await uow.session.scalar(
                    select(Request).where(
                        Request.requested_by == principal.account_id,
                        Request.idempotency_key == key,
                    )
                )
                if previous:
                    if previous.request_hash != body_hash:
                        raise ReportsProblem("idempotency_conflict")
                    return previous.admitted_response
                now = self.clock.now()
                # The installation's actual zone is authoritative, independent of browser or process-local settings.
                from ecs_ec.consumption.catalog_storage import BuildingRow

                installed = await uow.session.get(BuildingRow, building)
                if installed is None:
                    raise ReportsProblem("capture_unavailable", 503)
                zone = installed.timezone
                try:
                    start, end = window(selection, zone, now)
                except ValueError, OverflowError:
                    raise ReportsProblem(
                        "future_period",
                        422,
                        [
                            dict(
                                path="selection",
                                code="future_period",
                                message="Seleccione un período que ya haya comenzado.",
                            )
                        ],
                    ) from None
                handle = self.signal("begin", "report.generate", "reports")
                context = handle.context if handle else None
                identifier = uuid4()
                deadline = anniversary(now, zone)
                response = dict(
                    id=str(identifier),
                    scale=selection.scale,
                    window=dict(start=start.isoformat(), end=end.isoformat()),
                    timezone=zone,
                    cutoff_at=now.isoformat(),
                    state="pendiente",
                    status_path=f"/api/v1/reports/{identifier}",
                    download_path=None,
                )
                row = Request(
                    id=identifier,
                    building_id=building,
                    requested_by=principal.account_id,
                    operation="reports.generate",
                    scale=selection.scale,
                    selection=body,
                    timezone=zone,
                    window_start=start,
                    window_end=end,
                    cutoff_at=now,
                    created_at=now,
                    retain_until=deadline,
                    state="pendiente",
                    revision=1,
                    idempotency_key=key,
                    request_hash=body_hash,
                    admitted_response=response,
                    technical_context={
                        k: str(v) if k.endswith("_ref") and v else v
                        for k, v in context.fields().items()
                    }
                    if context
                    else {},
                )
                uow.session.add(row)
                await uow.session.flush()
                try:
                    async with uow.session.begin_nested():
                        snapshot = await capture_snapshot(
                            identity=self.identity,
                            consumption=self.consumption,
                            costs=self.costs,
                            building_id=building,
                            start=start,
                            end=end,
                            scale=selection.scale,
                            cutoff_at=now,
                            principal=principal,
                            unit_of_work=uow,
                        )
                        await protect_snapshot(uow, snapshot, deadline)
                        data = snapshot.model_dump(mode="json")
                        uow.session.add(
                            Capture(
                                id=uuid4(),
                                request_id=identifier,
                                schema_version=1,
                                data=data,
                                functional_hash=functional_hash(data),
                                created_at=now,
                                retain_until=deadline,
                            )
                        )
                        await uow.session.flush()
                    self.signal("stage", handle, "capture")
                except Exception:
                    self.signal(
                        "stage",
                        handle,
                        "capture",
                        outcome="unexpected_error",
                        code="processing_interrupted",
                    )
                    await record_failure(uow, row, "captura_no_disponible", self.clock)
                await uow.commit()
                self.signal("admitted", handle)
                if row.state == "fallido":
                    self.signal(
                        "complete",
                        handle,
                        event="report.completed",
                        outcome="unexpected_error",
                        code="processing_interrupted",
                        duration_ms=None,
                    )
                else:
                    self.signal("release", handle)
                return response
        finally:
            self.signal("release", handle)

    async def status(self, principal, identifier):
        """Authorize the current principal and return scoped metadata from a short readonly transaction."""
        self.identity.authorize(
            principal, "reports.read", self.identity.settings.building_id
        )
        handle = self.signal("begin", "report.query", "reports")
        outcome, code = "success", "ok"
        try:
            async with UnitOfWork(self.database.sessions) as uow:
                row = await uow.session.get(Request, identifier)
                if row is None or row.building_id != principal.building_id:
                    raise ReportsProblem("report_not_found", 404)
                result = await uow.session.scalar(
                    select(Result).where(Result.request_id == row.id)
                )
                return self.view(row, result)
        except ReportsProblem as error:
            outcome, code = (
                ("expected_rejection", "invalid_input")
                if error.status < 500
                else ("unexpected_error", "database_unavailable")
            )
            raise
        except Exception:
            outcome, code = "unexpected_error", "database_unavailable"
            raise
        finally:
            self.signal("complete", handle, outcome=outcome, code=code)

    async def download(self, principal, identifier):
        """Return exact stored verified bytes after current authorization; reading never regenerates or changes deadlines."""
        self.identity.authorize(
            principal, "reports.read", self.identity.settings.building_id
        )
        handle = self.signal("begin", "report.download", "reports")
        outcome, code = "success", "ok"
        try:
            async with UnitOfWork(self.database.sessions) as uow:
                row = await uow.session.get(Request, identifier)
                if row is None or row.building_id != principal.building_id:
                    raise ReportsProblem("report_not_found", 404)
                result = await uow.session.scalar(
                    select(Result).where(Result.request_id == row.id)
                )
                if not result or result.state != "generado":
                    raise ReportsProblem("download_unavailable")
                binary = await uow.session.get(Binary, result.binary_id)
                if (
                    not binary
                    or len(binary.content) != result.byte_length
                    or hashlib.sha256(binary.content).hexdigest() != result.sha256
                ):
                    raise ReportsProblem("binary_unavailable", 503)
                return binary.content, result.filename
        except ReportsProblem as error:
            outcome, code = (
                ("expected_rejection", "invalid_input")
                if error.status < 500
                else ("unexpected_error", "database_unavailable")
            )
            raise
        except Exception:
            outcome, code = "unexpected_error", "database_unavailable"
            raise
        finally:
            self.signal("complete", handle, outcome=outcome, code=code)
