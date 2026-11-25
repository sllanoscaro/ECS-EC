"""008 owned durable PostgreSQL identities, restrictive references and bounded delivery states.

All business writes receive the injected clock in services. No cascade deletes protected
history. Deferred references permit atomically publishing rule/version/schedule graphs.
SMTP addresses exist only on attempts, never pending deliveries or technical telemetry.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy import UniqueConstraint as Unique
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as col

from ecs_ec.core.database import Base


def Check(expression, *, name=None):
    """Name every check deterministically for009's explicit SQL naming convention."""
    from hashlib import sha256

    return CheckConstraint(
        expression, name=name or "c_" + sha256(expression.encode()).hexdigest()[:12]
    )


def ref(table, *, nullable=False, deferred=False):
    """Create an owned restrictive UUID reference; defer only graph cycles, never delete cascades."""
    return col(
        PGUUID(as_uuid=True),
        ForeignKey(
            table + ".id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=deferred,
            name=("fk_" + table + "_graph_" + str(ref.index())) if deferred else None,
        ),
        nullable=nullable,
    )


def _next_ref_index():
    """Allocate deterministic graph-constraint names during metadata construction, not row creation."""
    _next_ref_index.counter += 1
    return _next_ref_index.counter


_next_ref_index.counter = 0
ref.index = _next_ref_index


class Historical:
    """Common provenance and protected retention; caller supplies domain timestamps on every real write."""

    created_at: Mapped[datetime] = col(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    recorded_by: Mapped[str] = col(String(200), default="process:notifications")
    retain_until: Mapped[datetime] = col(DateTime(timezone=True))


class Rule(Base):
    """Mutable administrative head; historical immutable versions remain referenced."""

    __tablename__ = "notification_rule"
    __table_args__ = (
        Check("length(btrim(name)) BETWEEN 1 AND 120", name="notification_rule_name"),
        Check(
            "status IN ('desactivada','activa','pausada')",
            name="notification_rule_status",
        ),
        Check("revision>0", name="notification_rule_revision"),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    building_id: Mapped[UUID] = col(PGUUID(as_uuid=True))
    name: Mapped[str] = col(String(120))
    current_version_id: Mapped[UUID] = ref("notification_rule_version", deferred=True)
    status: Mapped[str] = col(String(20), default="desactivada")
    revision: Mapped[int] = col(Integer, default=1)
    created_by: Mapped[UUID] = ref("identity_account")
    created_at: Mapped[datetime] = col(DateTime(timezone=True))
    updated_at: Mapped[datetime] = col(DateTime(timezone=True))


class RuleVersion(Historical, Base):
    """One immutable mode/configuration and recipient set; retirement only extends history."""

    __tablename__ = "notification_rule_version"
    __table_args__ = (
        Unique("rule_id", "version_number"),
        Check("version_number>0"),
        Check(
            "(mode='periodica' AND schedule_id IS NOT NULL AND condition_id IS NULL) OR (mode='urgente' AND condition_id IS NOT NULL AND schedule_id IS NULL)"
        ),
        Check(
            "jsonb_typeof(content_types)='array' AND jsonb_array_length(content_types)>0"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = ref("notification_rule")
    version_number: Mapped[int] = col(Integer)
    mode: Mapped[str] = col(String(20))
    content_types: Mapped[list] = col(JSONB)
    timezone: Mapped[str] = col(String(100))
    config: Mapped[dict] = col(JSONB)
    schedule_id: Mapped[UUID | None] = ref(
        "notification_schedule", nullable=True, deferred=True
    )
    condition_id: Mapped[UUID | None] = ref(
        "notification_condition", nullable=True, deferred=True
    )
    template_version: Mapped[str] = col(String(40), default="008-v1")
    created_by: Mapped[UUID] = ref("identity_account")
    retired_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)


class Recipient(Base):
    """A registered006 account identity, never an arbitrary delivery email."""

    __tablename__ = "notification_version_recipient"
    version_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey(
            "notification_rule_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        primary_key=True,
    )
    account_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("identity_account.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class Schedule(Base):
    """Normalized nominal calendar; fields irrelevant to a recurrence are forbidden by SQL."""

    __tablename__ = "notification_schedule"
    __table_args__ = (
        Unique("version_id"),
        Check(
            "(kind='intervalo' AND interval_value IS NOT NULL AND interval_unit IS NOT NULL AND interval_value>0 AND interval_unit IN ('minutos','horas') AND local_time IS NULL AND weekday IS NULL AND day_of_month IS NULL AND month IS NULL) OR (kind IN ('diaria','semanal','mensual','anual') AND interval_value IS NULL AND interval_unit IS NULL AND local_time IS NOT NULL AND local_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$' AND ((kind='diaria' AND weekday IS NULL AND day_of_month IS NULL AND month IS NULL) OR (kind='semanal' AND weekday IS NOT NULL AND weekday BETWEEN 1 AND 7 AND day_of_month IS NULL AND month IS NULL) OR (kind='mensual' AND weekday IS NULL AND day_of_month IS NOT NULL AND day_of_month BETWEEN 1 AND 31 AND month IS NULL) OR (kind='anual' AND weekday IS NULL AND month IS NOT NULL AND day_of_month IS NOT NULL AND day_of_month BETWEEN 1 AND 31 AND month BETWEEN 1 AND 12)))"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = ref("notification_rule_version")
    kind: Mapped[str] = col(String(20))
    starts_at: Mapped[datetime] = col(DateTime(timezone=True))
    interval_value: Mapped[int | None] = col(Integer, nullable=True)
    interval_unit: Mapped[str | None] = col(String(10), nullable=True)
    local_time: Mapped[str | None] = col(String(5), nullable=True)
    weekday: Mapped[int | None] = col(Integer, nullable=True)
    day_of_month: Mapped[int | None] = col(Integer, nullable=True)
    month: Mapped[int | None] = col(Integer, nullable=True)
    timezone: Mapped[str] = col(String(100))


class Condition(Base):
    """Consumption/absence/system variants with exact Decimal thresholds and explicit categories."""

    __tablename__ = "notification_condition"
    __table_args__ = (
        Unique("version_id"),
        Check("kind IN ('consumo','ausencia_datos','evento_sistema')"),
        Check("category_id IS NULL OR category_id ~ '^CAT-0[1-7]$'"),
        Check(
            "threshold_kwh IS NULL OR (threshold_kwh>=0 AND threshold_kwh::text NOT IN ('NaN','Infinity','-Infinity'))"
        ),
        Check(
            "(kind='consumo' AND category_id IS NOT NULL AND unit IS NOT NULL AND unit='kWh' AND window_kind IS NOT NULL AND comparison IS NOT NULL AND window_kind IN ('intervalo','hora','dia','mes','anio') AND comparison IN ('gt','gte','lt','lte') AND threshold_kwh IS NOT NULL AND silence_minutes IS NULL AND event_type IS NULL AND ((window_kind='intervalo' AND measurement_interval_seconds IS NOT NULL AND measurement_interval_seconds>0) OR (window_kind!='intervalo' AND measurement_interval_seconds IS NULL))) OR (kind='ausencia_datos' AND category_id IS NOT NULL AND silence_minutes IS NOT NULL AND silence_minutes>=15 AND threshold_kwh IS NULL AND event_type IS NULL AND unit IS NULL AND window_kind IS NULL AND comparison IS NULL AND measurement_interval_seconds IS NULL) OR (kind='evento_sistema' AND event_type IS NOT NULL AND event_type IN ('recepcion_rechazada','calculo_fallido','pdf_fallido') AND category_id IS NULL AND threshold_kwh IS NULL AND silence_minutes IS NULL AND unit IS NULL AND window_kind IS NULL AND comparison IS NULL AND measurement_interval_seconds IS NULL)"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = ref("notification_rule_version")
    kind: Mapped[str] = col(String(30))
    category_id: Mapped[str | None] = col(String(6), nullable=True)
    unit: Mapped[str | None] = col(String(10), nullable=True)
    window_kind: Mapped[str | None] = col(String(10), nullable=True)
    measurement_interval_seconds: Mapped[int | None] = col(Integer, nullable=True)
    comparison: Mapped[str | None] = col(String(4), nullable=True)
    threshold_kwh: Mapped[object | None] = col(Numeric(), nullable=True)
    silence_minutes: Mapped[int | None] = col(Integer, nullable=True)
    event_type: Mapped[str | None] = col(String(40), nullable=True)


class Activation(Base):
    """An activation epoch owns future scheduling and evaluation; pause ends it permanently."""

    __tablename__ = "notification_activation"
    __table_args__ = (
        Index(
            "uq_notification_active_rule",
            "rule_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index(
            "ix_notification_next_due",
            "next_due_at",
            postgresql_where=text("ended_at IS NULL"),
        ),
        Check("ended_at IS NULL OR ended_at>=activated_at"),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = ref("notification_rule")
    version_id: Mapped[UUID] = ref("notification_rule_version")
    activated_at: Mapped[datetime] = col(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    next_due_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    next_slot: Mapped[dict | None] = col(JSONB, nullable=True)
    last_materialized_slot: Mapped[str | None] = col(String(200), nullable=True)
    tzdata_version: Mapped[str] = col(String(40))
    actor_id: Mapped[UUID | None] = col(PGUUID(as_uuid=True), nullable=True)
    revision: Mapped[int] = col(Integer, default=1)


class Evidence(Historical, Base):
    """Immutable functional capture preserves quality, provenance, nullable value and summary coverage."""

    __tablename__ = "notification_evidence"
    __table_args__ = (
        Check("jsonb_typeof(payload)='object'"),
        Check("origin IN ('medido','calculado','sin_fuente')"),
        Check(
            "value_kwh IS NULL OR (value_kwh>=0 AND value_kwh::text NOT IN ('NaN','Infinity','-Infinity'))"
        ),
        Check("value_kwh IS NOT NULL OR limitation_code IS NOT NULL"),
        Check(
            "(window_start IS NULL AND window_end IS NULL) OR window_start<window_end"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    payload: Mapped[dict] = col(JSONB)
    value_kwh: Mapped[object | None] = col(Numeric(), nullable=True)
    origin: Mapped[str] = col(String(20), default="sin_fuente")
    limitation_code: Mapped[str | None] = col(
        String(100).evaluates_none(), nullable=True, default="informacion_insuficiente"
    )
    category_id: Mapped[str | None] = col(String(6), nullable=True)
    window_start: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    cutoff_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    source_refs: Mapped[list] = col(JSONB, default=list)


class Episode(Historical, Base):
    """One open condition per activation/scope; missing evidence never normalizes it."""

    __tablename__ = "notification_episode"
    __table_args__ = (
        Index(
            "uq_notification_open_episode",
            "activation_id",
            "scope_key",
            unique=True,
            postgresql_where=text("status='abierto'"),
        ),
        Unique("activation_id", "source_event_id"),
        Check("status IN ('abierto','cerrado','finalizado_por_regla')"),
        Check(
            "scope_key ~ '^CAT-0[1-7]$' OR scope_key IN ('recepcion_rechazada','calculo_fallido','pdf_fallido')"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    activation_id: Mapped[UUID] = ref("notification_activation")
    scope_key: Mapped[str] = col(String(40))
    opened_at: Mapped[datetime] = col(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    opening_evidence_id: Mapped[UUID] = ref("notification_evidence")
    closing_evidence_id: Mapped[UUID | None] = ref(
        "notification_evidence", nullable=True
    )
    source_event_id: Mapped[UUID | None] = ref("functional_event", nullable=True)
    status: Mapped[str] = col(String(30), default="abierto")


class EvaluationState(Base):
    """Serialized durable cursor; only valid windows advance last_valid_window_end."""

    __tablename__ = "notification_evaluation_state"
    __table_args__ = (
        Check(
            "scope_key ~ '^CAT-0[1-7]$' OR scope_key IN ('recepcion_rechazada','calculo_fallido','pdf_fallido')"
        ),
    )
    activation_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("notification_activation.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    scope_key: Mapped[str] = col(String(40), primary_key=True)
    last_valid_window_end: Mapped[datetime | None] = col(
        DateTime(timezone=True), nullable=True
    )
    last_evaluated_window_end: Mapped[datetime | None] = col(
        DateTime(timezone=True), nullable=True
    )
    last_new_data_accepted_at: Mapped[datetime | None] = col(
        DateTime(timezone=True), nullable=True
    )
    last_result: Mapped[str | None] = col(String(30), nullable=True)
    open_episode_id: Mapped[UUID | None] = ref("notification_episode", nullable=True)
    event_cursor: Mapped[str | None] = col(String(500), nullable=True)
    source_cursor: Mapped[str | None] = col(String(2000), nullable=True)


class ConsumedEvent(Historical, Base):
    """Per-activation source-event acknowledgement; late commits cannot be skipped by a timestamp cursor."""

    __tablename__ = "notification_consumed_event"
    activation_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("notification_activation.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    source_event_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("functional_event.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class Evaluation(Historical, Base):
    """Immutable attempted evidence identity, including historical omissions and no-evaluable outcomes."""

    __tablename__ = "notification_evaluation"
    __table_args__ = (
        Unique("activation_id", "evidence_key"),
        Check("result IN ('cumple','no_cumple','no_evaluable','omitida_historica')"),
        Check(
            "(window_start IS NULL AND window_end IS NULL) OR window_start<window_end"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    activation_id: Mapped[UUID] = ref("notification_activation")
    source_event_id: Mapped[UUID | None] = ref("functional_event", nullable=True)
    evidence_key: Mapped[str] = col(String(200))
    window_start: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    cutoff_at: Mapped[datetime] = col(DateTime(timezone=True))
    evaluated_at: Mapped[datetime] = col(DateTime(timezone=True))
    result: Mapped[str] = col(String(30))
    reason_code: Mapped[str] = col(String(100))
    evidence_id: Mapped[UUID] = ref("notification_evidence")
    episode_id: Mapped[UUID | None] = ref("notification_episode", nullable=True)


class Occurrence(Historical, Base):
    """One logical slot/episode/recovery batch; scheduler retries cannot create another occurrence."""

    __tablename__ = "notification_occurrence"
    __table_args__ = (
        Unique("version_id", "logical_key"),
        Check("kind IN ('periodica','urgente','recuperacion')"),
        Check(
            "(window_start IS NULL AND window_end IS NULL AND NOT initial_window_empty) OR window_start<window_end OR (kind='periodica' AND initial_window_empty AND window_start=window_end)",
            name="window",
        ),
    )
    initial_window_empty: Mapped[bool] = col(Boolean, default=False)
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = ref("notification_rule_version")
    activation_id: Mapped[UUID] = ref("notification_activation")
    kind: Mapped[str] = col(String(20))
    logical_key: Mapped[str] = col(String(200))
    nominal_local_slot: Mapped[str | None] = col(String(200), nullable=True)
    scheduled_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    window_start: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    cutoff_at: Mapped[datetime] = col(DateTime(timezone=True))
    episode_id: Mapped[UUID | None] = ref("notification_episode", nullable=True)
    tzdata_version: Mapped[str] = col(String(40))
    is_late: Mapped[bool] = col(Boolean, default=False)


class Message(Historical, Base):
    """Immutable typed snapshot, hash and required grants; no attachments or technical diagnostics."""

    __tablename__ = "notification_message"
    __table_args__ = (
        Unique("occurrence_id"),
        Check("jsonb_typeof(functional_content)='object'"),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = ref("notification_occurrence")
    template_version: Mapped[str] = col(String(40), default="008-v1")
    functional_content: Mapped[dict] = col(JSONB)
    content_hash: Mapped[str] = col(String(64))
    required_permissions: Mapped[list] = col(JSONB)


class Delivery(Historical, Base):
    """Account-scoped queue entry; reserving/attempting SMTP never stores a pending fixed email."""

    __tablename__ = "notification_delivery"
    __table_args__ = (
        Unique("message_id", "account_id", "generation"),
        Check("generation>=0 AND attempt_count BETWEEN 0 AND 3"),
        Check(
            "state IN ('pendiente','en_intento','aceptada','fallida','cancelada','indeterminada')"
        ),
        Check("transport_kind IN ('local_prueba','smtp_produccion')"),
        Index(
            "ix_notification_queue",
            "next_attempt_at",
            "id",
            postgresql_where=text("state='pendiente'"),
        ),
        Index("ix_notification_history", "account_id", "created_at", "id"),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = ref("notification_message")
    account_id: Mapped[UUID] = ref("identity_account")
    generation: Mapped[int] = col(Integer, default=0)
    state: Mapped[str] = col(String(20), default="pendiente")
    next_attempt_at: Mapped[datetime] = col(DateTime(timezone=True))
    attempt_count: Mapped[int] = col(Integer, default=0)
    smtp_message_id: Mapped[str] = col(String(254))
    transport_kind: Mapped[str] = col(String(20))
    parent_delivery_id: Mapped[UUID | None] = ref(
        "notification_delivery", nullable=True
    )
    cancellation_reason: Mapped[str | None] = col(String(100), nullable=True)


class Attempt(Historical, Base):
    """Durable start precedes SMTP; lost confirmation is indeterminate, never silently retried."""

    __tablename__ = "notification_delivery_attempt"
    __table_args__ = (
        Unique("delivery_id", "attempt_number"),
        Check("attempt_number BETWEEN 1 AND 3"),
        Check(
            "outcome IS NULL OR outcome IN ('aceptada','no_aceptada_transitoria','no_aceptada_definitiva','indeterminada')"
        ),
        Check(
            "(finished_at IS NULL AND outcome IS NULL) OR (finished_at>=started_at AND outcome IS NOT NULL)"
        ),
        Index(
            "uq_notification_open_attempt",
            "delivery_id",
            unique=True,
            postgresql_where=text("finished_at IS NULL"),
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    delivery_id: Mapped[UUID] = ref("notification_delivery")
    attempt_number: Mapped[int] = col(Integer)
    effective_email: Mapped[str] = col(String(254))
    authorized_at: Mapped[datetime] = col(DateTime(timezone=True))
    started_at: Mapped[datetime] = col(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = col(DateTime(timezone=True), nullable=True)
    transport_kind: Mapped[str] = col(String(20))
    process_ref: Mapped[UUID] = col(PGUUID(as_uuid=True))
    outcome: Mapped[str | None] = col(String(40), nullable=True)
    functional_reason_code: Mapped[str | None] = col(String(100), nullable=True)
    acceptance_confirmed_at: Mapped[datetime | None] = col(
        DateTime(timezone=True), nullable=True
    )
    relay_reference: Mapped[str | None] = col(String(200), nullable=True)


class RecoveryMember(Base):
    """An original never-attempted slot may join exactly one recovery batch; preserve each period."""

    __tablename__ = "notification_recovery_member"
    original_delivery_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("notification_delivery.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    recovery_delivery_id: Mapped[UUID] = ref("notification_delivery")
    original_slot: Mapped[str] = col(String(200))
    original_window: Mapped[dict] = col(JSONB)
    created_at: Mapped[datetime] = col(DateTime(timezone=True))


class ResendDecision(Historical, Base):
    """Protected explicit acknowledgement authorizes a new generation; original result remains immutable."""

    __tablename__ = "notification_resend_decision"
    __table_args__ = (
        Unique("administrator_id", "idempotency_key"),
        Unique("new_delivery_id"),
        Check(
            "length(btrim(reason)) BETWEEN 1 AND 500 AND acknowledge_possible_duplicate"
        ),
    )
    id: Mapped[UUID] = col(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_delivery_id: Mapped[UUID] = ref("notification_delivery")
    new_delivery_id: Mapped[UUID] = ref("notification_delivery")
    administrator_id: Mapped[UUID] = ref("identity_account")
    decided_at: Mapped[datetime] = col(DateTime(timezone=True))
    reason: Mapped[str] = col(String(500))
    acknowledge_possible_duplicate: Mapped[bool] = col(Boolean)
    idempotency_key: Mapped[str] = col(String(100))
    request_hash: Mapped[str] = col(String(64))


class Idempotency(Historical, Base):
    """Authenticate first, resolve committed keys before If-Match, and retain reference-only receipts."""

    __tablename__ = "notification_api_idempotency"
    actor_id: Mapped[UUID] = col(
        PGUUID(as_uuid=True),
        ForeignKey("identity_account.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    operation: Mapped[str] = col(String(100), primary_key=True)
    idempotency_key: Mapped[str] = col(String(100), primary_key=True)
    request_hash: Mapped[str] = col(String(64))
    resource_id: Mapped[UUID] = col(PGUUID(as_uuid=True))
    http_status: Mapped[int] = col(Integer)
    resource_revision: Mapped[int] = col(Integer)
    resource_metadata: Mapped[dict] = col(JSONB)


class Preview(Base):
    """Private hashed preview token binds actor/configuration/recipient revisions/tzdata and expiry."""

    __tablename__ = "notification_preview"
    token_hash: Mapped[str] = col(String(64), primary_key=True)
    actor_id: Mapped[UUID] = ref("identity_account")
    config_hash: Mapped[str] = col(String(64))
    permissions_hash: Mapped[str] = col(String(64))
    tzdata_version: Mapped[str] = col(String(40))
    expires_at: Mapped[datetime] = col(DateTime(timezone=True))
    created_at: Mapped[datetime] = col(DateTime(timezone=True))
