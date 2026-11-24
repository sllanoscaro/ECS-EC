"""005 owns durable requests, immutable captures/results and private verified BYTEA artifacts."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ecs_ec.core.database import Base


class Request(Base):
    """One actor/idempotency-key admits one durable calendar request with a fixed data cutoff."""

    __tablename__ = "report_request"
    __table_args__ = (
        UniqueConstraint("requested_by", "operation", "idempotency_key"),
        CheckConstraint(
            "scale IN ('diario','mensual','anual') AND state IN ('pendiente','generando','generado','fallido') AND revision>0",
            name="state",
        ),
        CheckConstraint(
            "window_start < window_end AND retain_until > created_at", name="window"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(
        ForeignKey("consumption_building.id", ondelete="RESTRICT"), index=True
    )
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("identity_account.id", ondelete="RESTRICT")
    )
    operation: Mapped[str] = mapped_column(String(40), default="reports.generate")
    scale: Mapped[str] = mapped_column(String(10))
    selection: Mapped[dict] = mapped_column(JSONB)
    timezone: Mapped[str] = mapped_column(String(100))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(12), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    admitted_response: Mapped[dict] = mapped_column(JSONB)
    technical_context: Mapped[dict] = mapped_column(JSONB, default=dict)


class Capture(Base):
    """Typed schema-validated immutable functional copy; hashes exclude issuance and technical correlation."""

    __tablename__ = "report_snapshot"
    __table_args__ = (
        CheckConstraint(
            "schema_version=1 AND jsonb_array_length(data->'energy_rows')=7",
            name="schema",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_request.id", ondelete="RESTRICT"), unique=True
    )
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSONB)
    functional_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Result(Base):
    """Only an atomic final publication exposes a generated PDF; admitted failures remain without bytes."""

    __tablename__ = "report_result"
    __table_args__ = (
        CheckConstraint("state IN ('generado','fallido')", name="state"),
        CheckConstraint(
            "(state='generado' AND snapshot_id IS NOT NULL AND page_count=1 AND page_width_mm=210 AND page_height_mm=297 AND minimum_font_pt>=10 AND sha256 IS NOT NULL AND byte_length>0 AND binary_id IS NOT NULL AND functional_reason_code IS NULL) OR (state='fallido' AND sha256 IS NULL AND byte_length IS NULL AND binary_id IS NULL AND functional_reason_code IS NOT NULL)",
            name="complete",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_request.id", ondelete="RESTRICT"), unique=True
    )
    snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_snapshot.id", ondelete="RESTRICT")
    )
    state: Mapped[str] = mapped_column(String(12))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    filename: Mapped[str | None] = mapped_column(String(200))
    page_count: Mapped[int | None] = mapped_column(Integer)
    page_width_mm: Mapped[int | None] = mapped_column(Integer)
    page_height_mm: Mapped[int | None] = mapped_column(Integer)
    minimum_font_pt: Mapped[int | None] = mapped_column(Integer)
    layout_manifest: Mapped[dict | None] = mapped_column(JSONB)
    validation_version: Mapped[str] = mapped_column(String(30), default="005-v1")
    functional_reason_code: Mapped[str | None] = mapped_column(String(60))
    correlation_ref: Mapped[UUID] = mapped_column()
    binary_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "report_binary.id",
            ondelete="RESTRICT",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        )
    )
    sha256: Mapped[str | None] = mapped_column(String(64))
    byte_length: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Binary(Base):
    """Private immutable artifact whose PostgreSQL length/hash constraints verify the actual downloaded bytes."""

    __tablename__ = "report_binary"
    __table_args__ = (
        CheckConstraint(
            "content_type='application/pdf' AND byte_length=octet_length(content) AND byte_length>0 AND sha256=encode(sha256(content),'hex')",
            name="integrity",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    result_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "report_result.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        unique=True,
    )
    content_type: Mapped[str] = mapped_column(String(30), default="application/pdf")
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    byte_length: Mapped[int] = mapped_column(Integer)
