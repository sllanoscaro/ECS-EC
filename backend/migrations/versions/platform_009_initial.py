"""Initial platform evidence only; no accounts, measurements or notification tables.

Revision: platform_009_initial. This reviewed migration freezes its own schema and does
not import mutable application models. Protected evidence is never dropped on downgrade.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "platform_009_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create durable evidence, provenance uniqueness and representable integrity constraints."""
    op.create_table("functional_event",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source_module", sa.String(100), nullable=False),
        sa.Column("source_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_window", pg.JSONB(none_as_null=True), nullable=True),
        sa.Column("accepted_new_data", sa.Boolean(), nullable=False),
        sa.Column("safe_payload", pg.JSONB(), nullable=False),
        sa.Column("correlation_ref", sa.String(200), nullable=True),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_module", "source_entity_id", "source_revision", "event_type", name="uq_event_provenance"),
        sa.CheckConstraint("source_revision > 0", name="positive_revision"),
        sa.CheckConstraint("retain_until > recorded_at", name="retention"),
        sa.CheckConstraint("jsonb_typeof(safe_payload) = 'object'", name="payload_object"),
        sa.CheckConstraint("effective_window IS NULL OR (jsonb_typeof(effective_window) = 'object' AND effective_window ?& ARRAY['start','end'] AND (effective_window->>'start')::timestamptz < (effective_window->>'end')::timestamptz)", name="effective_window"),
    )
    op.create_index("ix_event_recorded", "functional_event", ["recorded_at", "id"])
    op.create_table("functional_audit",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_ref", sa.String(200), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_revision", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(100), nullable=False),
        sa.Column("safe_payload", pg.JSONB(), nullable=False),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("entity_revision IS NULL OR entity_revision > 0", name="positive_revision"),
        sa.CheckConstraint("retain_until > recorded_at", name="retention"),
        sa.CheckConstraint("jsonb_typeof(safe_payload) = 'object'", name="payload_object"),
    )
    op.create_index("ix_audit_entity", "functional_audit", ["entity_type", "entity_id", "recorded_at"])
    op.create_table("functional_coverage",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("source_ref", sa.String(200), nullable=False),
        sa.Column("source_revision", sa.String(200), nullable=True),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity", sa.String(20), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=True),
        sa.Column("covered_periods", pg.JSONB(), nullable=False),
        sa.Column("known_gaps", pg.JSONB(), nullable=False),
        sa.Column("limitation_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("window_start < window_end", name="valid_window"),
        sa.CheckConstraint("observed_count IS NULL OR observed_count >= 0", name="nonnegative_count"),
        sa.CheckConstraint("integrity IN ('completa','incompleta','desconocida')", name="integrity"),
        sa.CheckConstraint("jsonb_typeof(covered_periods) = 'array' AND jsonb_typeof(known_gaps) = 'array'", name="period_arrays"),
        sa.CheckConstraint("integrity != 'completa' OR (observed_count IS NOT NULL AND jsonb_array_length(covered_periods) > 0 AND jsonb_array_length(known_gaps) = 0)", name="complete_evidence"),
        sa.CheckConstraint("integrity != 'incompleta' OR jsonb_array_length(known_gaps) > 0", name="incomplete_evidence"),
        sa.CheckConstraint("retain_until > created_at", name="retention"),
    )
    op.create_index("ix_coverage_content_window", "functional_coverage", ["content_type", "window_start", "window_end", "cutoff_at"])
    op.create_index("ix_coverage_source_cutoff", "functional_coverage", ["source_ref", "cutoff_at"])


def downgrade():
    """Refuse automated destruction of protected evidence; restore a reviewed backup instead."""
    raise RuntimeError("Protected platform evidence cannot be automatically dropped")
