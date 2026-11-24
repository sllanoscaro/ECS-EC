"""005 shared publication primitives: safe failures, immutable hashes and atomic functional events."""

import hashlib
import json
from typing import Literal
from uuid import UUID, uuid4
from sqlalchemy import select
from ecs_ec.audit.events import (
    EventInput,
    EventWriter,
    Interval,
    PayloadRegistry,
    SafePayload,
)
from ecs_ec.core.retention import anniversary
from ecs_ec.reports.models import Result, Capture


class ReportsProblem(Exception):
    """Sanitized fixed report error; raw dependency/renderer exceptions never cross HTTP."""

    def __init__(self, code, status=409, field_errors=()):
        """Retain only a registered reason/status and approved field errors for the adapter."""
        self.code, self.status, self.field_errors = code, status, list(field_errors)
        super().__init__(code)


class FailurePayload(SafePayload):
    """Functional failure evidence contains only the report reference and a bounded reason vocabulary."""

    report_ref: UUID
    reason: Literal[
        "captura_no_disponible",
        "composicion_no_admisible",
        "validacion_documento_fallida",
        "generacion_interrumpida",
        "generacion_no_completada",
    ]


def canonical_hash(value):
    """Hash a JSON-compatible functional projection with deterministic key order and strict finite JSON."""
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def functional_hash(snapshot):
    """Compare functional evidence independently of operational retention extensions.

    Financial DTOs include retain_until on their evidence graph. Protecting that
    graph changes no revision, input, amount, coverage or selected pair. Preserve
    the full DTO in the capture, excluding only these deadlines from comparison.
    Report identity/issuance and technical context are never part of this snapshot.
    """

    def evidence(value):
        """Copy JSON recursively without mutating the producer's immutable projection."""
        if isinstance(value, dict):
            return {k: evidence(v) for k, v in value.items() if k != "retain_until"}
        if isinstance(value, list):
            return [evidence(v) for v in value]
        return value

    return canonical_hash(evidence(snapshot))


async def protect_snapshot(uow, snapshot, until):
    """Extend selected financial parents through004's owned graph under the common building lock.

    002 retains permanent ledger/configuration identities. This capture stores all
    numerical/quality evidence independently of withdrawable original payloads.
    Only an admission/publication extends protection; reads never reset retention.
    """
    from ecs_ec.costs.models import Calculation, BillRevision, Comparison
    from ecs_ec.costs.retention import protect

    for cycle in snapshot.financial_snapshot.cycles:
        for model, identifier in (
            (Calculation, cycle.calculation.id if cycle.calculation else None),
            (BillRevision, cycle.bill.bill_revision_id if cycle.bill else None),
            (Comparison, cycle.comparison.id if cycle.comparison else None),
        ):
            if identifier is not None:
                row = await uow.session.get(model, identifier)
                if row is None:
                    raise ValueError("financial_evidence_missing")
                await protect(uow, row, until)


async def record_failure(uow, request, reason, clock):
    """Append a single immutable failed result and pdf.failed in the caller's transaction, without committing."""
    existing = await uow.session.scalar(
        select(Result).where(Result.request_id == request.id)
    )
    if existing:
        return False
    now = clock.now()
    request.retain_until = max(request.retain_until, anniversary(now, request.timezone))
    snapshot = await uow.session.scalar(
        select(Capture).where(Capture.request_id == request.id)
    )
    if snapshot:
        snapshot.retain_until = max(snapshot.retain_until, request.retain_until)
    result = Result(
        id=uuid4(),
        request_id=request.id,
        snapshot_id=snapshot.id if snapshot else None,
        state="fallido",
        issued_at=now,
        cutoff_at=request.cutoff_at,
        filename=None,
        functional_reason_code=reason,
        correlation_ref=uuid4(),
        created_at=now,
        retain_until=max(request.retain_until, anniversary(now, request.timezone)),
    )
    uow.session.add(result)
    await uow.session.flush()
    registry = PayloadRegistry()
    registry.register("pdf.failed", FailurePayload)
    event = EventInput(
        event_id=uuid4(),
        type="pdf.failed",
        source_module="reports",
        source_entity_id=result.id,
        source_revision=1,
        occurred_at=now,
        measurement_window=Interval(start=request.window_start, end=request.window_end),
        accepted_new_data=False,
        safe_payload={"report_ref": request.id, "reason": reason},
        correlation_ref="report:" + request.id.hex,
    )
    await EventWriter(registry, clock, request.timezone).append(uow, event)
    request.state = "fallido"
    request.revision += 1
    return True
