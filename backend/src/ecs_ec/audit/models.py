"""Platform-owned PostgreSQL evidence tables; opaque references have no destructive FKs."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ecs_ec.core.database import Base


class FunctionalEvent(Base):
    """Immutable producer event, deduplicated by module/entity/revision/type, not by consumer."""

    __tablename__ = "functional_event"
    __table_args__ = (
        UniqueConstraint("source_module", "source_entity_id", "source_revision", "event_type", name="uq_event_provenance"),
        CheckConstraint("source_revision > 0", name="positive_revision"),
        CheckConstraint("retain_until > recorded_at", name="retention"),
        CheckConstraint("jsonb_typeof(safe_payload) = 'object'", name="payload_object"),
        CheckConstraint("effective_window IS NULL OR (jsonb_typeof(effective_window) = 'object' AND effective_window ?& ARRAY['start','end'] AND (effective_window->>'start')::timestamptz < (effective_window->>'end')::timestamptz)", name="effective_window"),
        Index("ix_event_recorded", "recorded_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100))
    source_module: Mapped[str] = mapped_column(String(100))
    source_entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    source_revision: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # A missing measured period is SQL NULL, distinct from a JSON literal null.
    effective_window: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    accepted_new_data: Mapped[bool] = mapped_column(Boolean, default=False)
    safe_payload: Mapped[dict] = mapped_column(JSONB)
    correlation_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditRecord(Base):
    """Repeatable functional attempts; actor is an opaque account/process reference."""

    __tablename__ = "functional_audit"
    __table_args__ = (
        CheckConstraint("entity_revision IS NULL OR entity_revision > 0", name="positive_revision"),
        CheckConstraint("retain_until > recorded_at", name="retention"),
        CheckConstraint("jsonb_typeof(safe_payload) = 'object'", name="payload_object"),
        Index("ix_audit_entity", "entity_type", "entity_id", "recorded_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_ref: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    entity_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(100))
    safe_payload: Mapped[dict] = mapped_column(JSONB)
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CoverageRecord(Base):
    """Evidence of history scope at a cutoff, distinct from a technical heartbeat."""

    __tablename__ = "functional_coverage"
    __table_args__ = (
        CheckConstraint("window_start < window_end", name="valid_window"),
        CheckConstraint("observed_count IS NULL OR observed_count >= 0", name="nonnegative_count"),
        CheckConstraint("integrity IN ('completa','incompleta','desconocida')", name="integrity"),
        CheckConstraint("jsonb_typeof(covered_periods) = 'array' AND jsonb_typeof(known_gaps) = 'array'", name="period_arrays"),
        CheckConstraint("integrity != 'completa' OR (observed_count IS NOT NULL AND jsonb_array_length(covered_periods) > 0 AND jsonb_array_length(known_gaps) = 0)", name="complete_evidence"),
        CheckConstraint("integrity != 'incompleta' OR jsonb_array_length(known_gaps) > 0", name="incomplete_evidence"),
        CheckConstraint("retain_until > created_at", name="retention"),
        Index("ix_coverage_content_window", "content_type", "window_start", "window_end", "cutoff_at"),
        Index("ix_coverage_source_cutoff", "source_ref", "cutoff_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    content_type: Mapped[str] = mapped_column(String(100))
    source_ref: Mapped[str] = mapped_column(String(200))
    source_revision: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    integrity: Mapped[str] = mapped_column(String(20))
    observed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    covered_periods: Mapped[list] = mapped_column(JSONB)
    known_gaps: Mapped[list] = mapped_column(JSONB)
    limitation_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[str] = mapped_column(String(200))
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
