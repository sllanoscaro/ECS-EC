"""Functional audit and coverage writers; semantics and read permissions belong to producers."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ecs_ec.audit.events import Code, EvidenceInput, Interval, OpaqueRef, PayloadRegistry, Revision, UTCInstant
from ecs_ec.audit.models import AuditRecord, CoverageRecord
from ecs_ec.core.clock import Clock, utc
from ecs_ec.core.errors import InvalidEvidence
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork


class AuditInput(EvidenceInput):
    """One attempt with an opaque actor and approved payload; repeat attempts have distinct UUIDs."""

    actor_ref: OpaqueRef
    action: Code
    entity_type: Code
    entity_id: UUID
    entity_revision: Revision | None = None
    occurred_at: UTCInstant
    result: Code
    safe_payload: dict


class FunctionalAudit:
    """Persist producer-approved actions without assuming identity tables or administrative semantics."""

    def __init__(self, schemas: PayloadRegistry, clock: Clock, timezone: str):
        """Receive action schemas/results, an internal clock and the retention timezone."""
        self.schemas, self.clock, self.timezone = schemas, clock, timezone

    async def append(self, uow: UnitOfWork, action: AuditInput) -> AuditRecord:
        """Validate and flush one attempt in the caller's transaction; do not commit or deduplicate."""
        try:
            action = AuditInput.model_validate(action.model_dump())
        except Exception:
            raise InvalidEvidence() from None
        safe = self.schemas.validate(action.action, action.safe_payload, action.result)
        now = utc(self.clock.now())
        row = AuditRecord(id=uuid4(), **action.model_dump(exclude={"safe_payload"}), safe_payload=safe,
                          recorded_at=now, retain_until=anniversary(now, self.timezone))
        uow.session.add(row)
        await uow.session.flush()
        return row


class CoverageInput(EvidenceInput):
    """Coverage at one source revision/cutoff; unavailable history never becomes an implicit zero."""

    content_type: Code
    source_ref: OpaqueRef
    source_revision: OpaqueRef | None = None
    cutoff_at: UTCInstant
    window_start: UTCInstant
    window_end: UTCInstant
    integrity: Literal["completa", "incompleta", "desconocida"]
    observed_count: Annotated[int, Field(ge=0, le=2147483647, strict=True)] | None
    covered_periods: list[Interval]
    known_gaps: list[Interval]
    limitation_code: Code | None = None
    recorded_by: OpaqueRef

    @model_validator(mode="after")
    def consistent(self):
        """Validate interval bounds, disjointness, complete partition and evidence for observed counts."""
        if self.window_start >= self.window_end:
            raise ValueError("Window start must precede end")
        for group in (self.covered_periods, self.known_gaps):
            previous = None
            for period in sorted(group, key=lambda interval: interval.start):
                if period.start < self.window_start or period.end > self.window_end:
                    raise ValueError("Periods must be bounded by the window")
                if previous is not None and period.start < previous:
                    raise ValueError("Periods must not overlap")
                previous = period.end
        for covered in self.covered_periods:
            if covered.end > self.cutoff_at:
                raise ValueError("Observed evidence cannot extend beyond its cutoff")
            if any(covered.start < gap.end and gap.start < covered.end for gap in self.known_gaps):
                raise ValueError("Covered periods and known gaps must be disjoint")
        if self.integrity == "completa":
            if self.observed_count is None or self.known_gaps or not self.covered_periods:
                raise ValueError("Complete coverage requires a known count and no gaps")
            cursor = self.window_start
            for period in sorted(self.covered_periods, key=lambda interval: interval.start):
                if period.start != cursor:
                    raise ValueError("Complete periods must be contiguous")
                cursor = period.end
            if cursor != self.window_end:
                raise ValueError("Complete coverage must span the entire window")
        if self.integrity == "incompleta" and not self.known_gaps:
            raise ValueError("Incomplete coverage requires a known gap")
        if self.integrity == "desconocida" and self.observed_count is not None and not self.covered_periods:
            raise ValueError("Observed count requires available covered evidence")
        return self


class CoverageService:
    """Store coverage history without global uniqueness, business reads or technical-log inference."""

    def __init__(self, clock: Clock, timezone: str):
        """Receive the internal creation clock and building retention timezone."""
        self.clock, self.timezone = clock, timezone

    async def append(self, uow: UnitOfWork, evidence: CoverageInput) -> CoverageRecord:
        """Revalidate, serialize UTC intervals and flush evidence in the producer's transaction."""
        try:
            evidence = CoverageInput.model_validate(evidence.model_dump())
        except Exception:
            raise InvalidEvidence() from None
        now = utc(self.clock.now())
        values = evidence.model_dump(exclude={"covered_periods", "known_gaps"})
        for field in ("covered_periods", "known_gaps"):
            values[field] = [period.model_dump(mode="json") for period in sorted(
                getattr(evidence, field), key=lambda interval: interval.start)]
        row = CoverageRecord(id=uuid4(), **values, created_at=now, retain_until=anniversary(now, self.timezone))
        uow.session.add(row)
        await uow.session.flush()
        return row
