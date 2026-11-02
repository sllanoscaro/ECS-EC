"""004 PostgreSQL metadata; shared audit/consumption tables remain owned by009/001/002."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column

from ecs_ec.core.database import Base


class Retained:
    """Every historical revision identifies its actor/process, creation instant and calendar minimum."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_ref: Mapped[str] = mapped_column(String(200))
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Supply(Retained, Base):
    """Singleton supply configuration; calculations copy every revision's values before subsequent edits."""

    __tablename__ = 'cost_supply'
    __table_args__ = (UniqueConstraint('building_id'), CheckConstraint('revision > 0', name='positive_revision'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONB)


class ProfileVersion(Retained, Base):
    """One immutable complete calendar; draft/published selection is fixed at creation."""

    __tablename__ = 'cost_profile_version'
    __table_args__ = (UniqueConstraint('supply_id', 'revision'),
        CheckConstraint("revision > 0 AND publication_state IN ('draft','published')", name='state_revision'),
        CheckConstraint('(revision = 1) = (previous_version_id IS NULL)', name='previous_revision'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    supply_id: Mapped[UUID] = mapped_column(ForeignKey('cost_supply.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    previous_version_id: Mapped[UUID | None] = mapped_column(ForeignKey('cost_profile_version.id', ondelete='RESTRICT'))
    publication_state: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict] = mapped_column(JSONB)


class ProfileSegment(Retained, Base):
    """Relational validity boundaries of a captured typed profile segment, never updated in place."""

    __tablename__ = 'cost_profile_segment'
    __table_args__ = (CheckConstraint('valid_to IS NULL OR valid_from < valid_to', name='validity'),
        ExcludeConstraint(('profile_version_id', '='), (text("tstzrange(valid_from,valid_to,'[)')"), '&&'), name='cost_segment_no_overlap', using='gist'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_version_id: Mapped[UUID] = mapped_column(ForeignKey('cost_profile_version.id', ondelete='RESTRICT'))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSONB)


class ProfileCharge(Retained, Base):
    """Unique typed charge and exact nullable price; a missing price never becomes zero."""

    __tablename__ = 'cost_profile_charge'
    __table_args__ = (UniqueConstraint('segment_id', 'code'), CheckConstraint('unit_price IS NULL OR unit_price >= 0', name='price'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    segment_id: Mapped[UUID] = mapped_column(ForeignKey('cost_profile_segment.id', ondelete='RESTRICT'))
    code: Mapped[str] = mapped_column(String(100))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)


class Idempotency(Retained, Base):
    """Atomic actor/operation/key record storing the original authorized response, including status/ETag."""

    __tablename__ = 'cost_operation_idempotency'
    __table_args__ = (UniqueConstraint('actor_ref', 'operation', 'key'),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[UUID] = mapped_column()
    http_status: Mapped[int] = mapped_column(Integer)
    response: Mapped[dict] = mapped_column(JSONB)


class BillingCycle(Retained, Base):
    """Immutable effective cycle identity; the reference month belongs to each calculation snapshot."""

    __tablename__ = 'cost_billing_cycle'
    __table_args__ = (UniqueConstraint('supply_id', 'start_at', 'end_at'), CheckConstraint('start_at < end_at', name='period'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    supply_id: Mapped[UUID] = mapped_column(ForeignKey('cost_supply.id', ondelete='RESTRICT'))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))
    data: Mapped[dict] = mapped_column(JSONB)


class InputSnapshot(Retained, Base):
    """Protected complete input values and derived maxima, independent from current/withdrawn source detail."""

    __tablename__ = 'cost_input_snapshot'
    id: Mapped[UUID] = mapped_column(primary_key=True)
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey('cost_billing_cycle.id', ondelete='RESTRICT'))
    profile_version_id: Mapped[UUID | None] = mapped_column(ForeignKey('cost_profile_version.id', ondelete='RESTRICT'))
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    schema_version: Mapped[int] = mapped_column(Integer)
    engine_version: Mapped[str] = mapped_column(String(100))
    input_hash: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSONB)
    monthly_maxima: Mapped[list] = mapped_column(JSONB)


class Calculation(Retained, Base):
    """Append-only persisted result with independent execution, temporal and sufficiency dimensions."""

    __tablename__ = 'cost_calculation'
    __table_args__ = (UniqueConstraint('cycle_id', 'revision'),
        CheckConstraint('revision > 0 AND ((revision = 1) = (previous_id IS NULL))', name='revision_chain'),
        CheckConstraint("execution_state IN ('completado','fallido') AND temporal_state IN ('en_curso','cerrado') AND sufficiency IN ('completo','parcial','no_calculable')", name='states'),
        CheckConstraint("(complete_total IS NOT NULL) = (sufficiency = 'completo' AND execution_state = 'completado')", name='complete_total'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey('cost_billing_cycle.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    previous_id: Mapped[UUID | None] = mapped_column(ForeignKey('cost_calculation.id', ondelete='RESTRICT'))
    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey('cost_input_snapshot.id', ondelete='RESTRICT'))
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    execution_state: Mapped[str] = mapped_column(String(20))
    temporal_state: Mapped[str] = mapped_column(String(20))
    sufficiency: Mapped[str] = mapped_column(String(20))
    available_subtotal: Mapped[Decimal] = mapped_column(Numeric())
    complete_total: Mapped[Decimal | None] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)


class CalculationComponent(Retained, Base):
    """Unique per-calculation monetary component; limited values remain SQLNULL, never surrogate zeros."""

    __tablename__ = 'cost_calculation_component'
    __table_args__ = (UniqueConstraint('calculation_id', 'code'),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    calculation_id: Mapped[UUID] = mapped_column(ForeignKey('cost_calculation.id', ondelete='RESTRICT'))
    code: Mapped[str] = mapped_column(String(100))
    basis_value: Mapped[Decimal | None] = mapped_column(Numeric())
    presented_amount: Mapped[Decimal | None] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)


class Bill(Retained, Base):
    """Logical invoice identity, unique per supply after documented NFKC/casefold/whitespace normalization."""

    __tablename__ = 'cost_bill'
    __table_args__ = (UniqueConstraint('supply_id', 'external_identifier_normalized'),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    supply_id: Mapped[UUID] = mapped_column(ForeignKey('cost_supply.id', ondelete='RESTRICT'))
    external_identifier_normalized: Mapped[str] = mapped_column(String(300))


class BillRevision(Retained, Base):
    """Immutable invoice correction; quantities read/billed and signed line amounts stay separate in typed data."""

    __tablename__ = 'cost_bill_revision'
    __table_args__ = (UniqueConstraint('bill_id', 'revision'),
        CheckConstraint('revision > 0 AND ((revision = 1) = (previous_id IS NULL))', name='revision_chain'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    bill_id: Mapped[UUID] = mapped_column(ForeignKey('cost_bill.id', ondelete='RESTRICT'))
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey('cost_billing_cycle.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    previous_id: Mapped[UUID | None] = mapped_column(ForeignKey('cost_bill_revision.id', ondelete='RESTRICT'))
    data: Mapped[dict] = mapped_column(JSONB)


class BillLine(Retained, Base):
    """Signed original document concept; unknown quantity/tax_amount isSQLNULL rather than zero."""

    __tablename__ = 'cost_bill_line'
    __table_args__ = (UniqueConstraint('bill_revision_id', 'code'),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    bill_revision_id: Mapped[UUID] = mapped_column(ForeignKey('cost_bill_revision.id', ondelete='RESTRICT'))
    code: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric())
    quantity: Mapped[Decimal | None] = mapped_column(Numeric())
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)


class Comparison(Retained, Base):
    """Immutable explicit pair comparison; correcting either side never mutates this resource."""

    __tablename__ = 'cost_comparison'
    __table_args__ = (UniqueConstraint('calculation_id', 'bill_revision_id', 'revision'), CheckConstraint('revision > 0', name='revision'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    calculation_id: Mapped[UUID] = mapped_column(ForeignKey('cost_calculation.id', ondelete='RESTRICT'))
    bill_revision_id: Mapped[UUID] = mapped_column(ForeignKey('cost_bill_revision.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delta_amount: Mapped[Decimal | None] = mapped_column(Numeric())
    delta_percent: Mapped[Decimal | None] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)


class ComparisonLine(Retained, Base):
    """Captured aligned quantities/amounts for one unique concept, with stable references on the parent."""

    __tablename__ = 'cost_comparison_line'
    __table_args__ = (UniqueConstraint('comparison_id', 'code'),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    comparison_id: Mapped[UUID] = mapped_column(ForeignKey('cost_comparison.id', ondelete='RESTRICT'))
    code: Mapped[str] = mapped_column(String(100))
    calculated_amount: Mapped[Decimal] = mapped_column(Numeric())
    billed_amount: Mapped[Decimal] = mapped_column(Numeric())
    data: Mapped[dict] = mapped_column(JSONB)
