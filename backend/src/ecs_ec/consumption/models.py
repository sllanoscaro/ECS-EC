"""Immutable consumption001 objects and002 port DTOs, with explicit historical provenance."""

import re
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from ecs_ec.consumption.energy import decimal_value, exact_context, supported_energy, to_kwh
from ecs_ec.core.clock import utc

CategoryId = Literal["CAT-01", "CAT-02", "CAT-03", "CAT-04", "CAT-05", "CAT-06", "CAT-07"]
Revision = Annotated[int, Field(gt=0, strict=True)]


def instant(value: object) -> datetime:
    """Parse a complete offset timestamp at exactly representable microsecond precision; return UTC."""
    if isinstance(value, str):
        match = re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d+))?(?:Z|[+-]\d{2}:\d{2})", value)
        if not match or (match[1] and any(c != "0" for c in match[1][6:])):
            raise ValueError("invalid_instant")
        try: value = datetime.fromisoformat(value)
        except (ValueError, OverflowError): raise ValueError("invalid_instant") from None
    if not isinstance(value, datetime): raise ValueError("invalid_instant")
    try: return utc(value)
    except (ValueError, OverflowError): raise ValueError("invalid_instant") from None


def iana(value: str) -> str:
    """Require an explicitly named installed IANA zone; browser/system timezones are irrelevant."""
    try: ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError): raise ValueError("invalid_timezone") from None
    return value


Instant = Annotated[datetime, BeforeValidator(instant)]
Timezone = Annotated[str, AfterValidator(iana)]
Energy = Annotated[Decimal, BeforeValidator(decimal_value), AfterValidator(supported_energy)]


class DomainModel(BaseModel):
    """Forbid unknown input fields and freeze typed snapshots; tuple containers avoid later mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class Period(DomainModel):
    """UTC half-open interval with positive duration and microsecond resolution."""

    start: Instant
    end: Instant

    @model_validator(mode="after")
    def ordered(self):
        """Reject empty/reversed intervals instead of clipping, splitting or normalizing them."""
        if self.start >= self.end: raise ValueError("invalid_period")
        return self


class BuildingContext(DomainModel):
    """One installation context; UUID/name/zone must be explicitly provisioned before data receipt."""

    id: UUID
    name: Annotated[str, Field(min_length=1, max_length=200)]
    timezone: Timezone
    created_at: Instant


class ConsumptionCategory(DomainModel):
    """One of seven non-editable ordered categories, including the electrical sanitary scope."""

    id: CategoryId
    name: str
    scope: str
    display_order: Annotated[int, Field(ge=1, le=7)]


class SourceInput(DomainModel):
    """Physical source choice; a missing meter has neither UUID nor label."""

    category_id: CategoryId
    has_meter: Annotated[bool, Field(strict=True)]
    source_id: UUID | None
    source_label: Annotated[str, Field(min_length=1, max_length=200)] | None

    @model_validator(mode="after")
    def source_presence(self):
        """Require both source fields iff a physical meter exists, with a meaningful label."""
        if self.has_meter:
            if self.source_id is None or self.source_label is None or not self.source_label.strip():
                raise ValueError("source_required")
        elif self.source_id is not None or self.source_label is not None:
            raise ValueError("absent_meter_has_source")
        return self


class CategorySource(SourceInput):
    """Historical source snapshot with a server-derived monotonic category revision."""

    category_revision: Revision


class ConfigurationInput(DomainModel):
    """Full administration command; derived category revisions cannot be supplied by a caller."""

    expected_revision: Annotated[int, Field(ge=0, strict=True)]
    effective_from: Instant | None
    timezone: Timezone
    categories: tuple[SourceInput, ...]

    @model_validator(mode="after")
    def complete(self):
        """Require exactly seven unique categories and no physical source shared across categories."""
        if len(self.categories) != 7 or len({s.category_id for s in self.categories}) != 7:
            raise ValueError("seven_unique_categories_required")
        sources = [s.source_id for s in self.categories if s.has_meter]
        if len(set(sources)) != len(sources): raise ValueError("source_reused")
        return self


class BasisSource(DomainModel):
    """Historical partial category/source pair; CAT-01 is never in its own calculation basis."""

    category_id: CategoryId
    source_id: UUID

    @model_validator(mode="after")
    def partial(self):
        """Reject a total used recursively as its own contribution."""
        if self.category_id == "CAT-01": raise ValueError("total_cannot_contribute")
        return self


class ConfigurationSegment(Period):
    """Clipped historical configuration of one category; global splits may preserve its revision."""

    configuration_revision: Revision
    category_revision: Revision
    source_mode: Literal["measured", "calculated", "unavailable"]
    source_id: UUID | None
    base_categories: tuple[CategoryId, ...] = ()
    basis_sources: tuple[BasisSource, ...] = ()
    # Internal accepted-contribution verification; the HTTP pair remains category/source only.
    basis_category_revisions: tuple[Revision, ...] = Field(default=(), exclude=True)

    @model_validator(mode="after")
    def provenance(self):
        """Require a physical source or a complete ordered calculation basis, never both."""
        if self.source_mode == "measured":
            valid = self.source_id is not None and not self.base_categories and not self.basis_sources
        elif self.source_mode == "calculated":
            valid = (self.source_id is None and bool(self.base_categories)
                and self.base_categories == tuple(b.category_id for b in self.basis_sources)
                and self.base_categories == tuple(sorted(set(self.base_categories))))
        else: valid = self.source_id is None and not self.base_categories and not self.basis_sources
        if not valid: raise ValueError("invalid_segment_provenance")
        if self.basis_category_revisions and len(self.basis_category_revisions) != len(self.basis_sources):
            raise ValueError("invalid_basis_revisions")
        return self


class InstallationRevision(DomainModel):
    """Append-only global audit revision; its end is derived from the next revision, never stored."""

    id: UUID
    building_id: UUID
    revision: Revision
    effective_from: Instant
    recorded_at: Instant
    created_by: str
    timezone: Timezone
    categories: tuple[CategorySource, ...]

    @model_validator(mode="after")
    def complete(self):
        """Reject corrupt/unsorted history snapshots using the same seven-source constraints as commands."""
        ConfigurationInput(expected_revision=self.revision, effective_from=self.effective_from, timezone=self.timezone,
            categories=tuple(SourceInput(**c.model_dump(exclude={"category_revision"})) for c in self.categories))
        if tuple(c.category_id for c in self.categories) != tuple(sorted(c.category_id for c in self.categories)):
            raise ValueError("unordered_category_snapshot")
        return self

    def entry(self, category_id: CategoryId) -> CategorySource:
        """Return one configured category or raise KeyError for a category outside the fixed catalog."""
        for category in self.categories:
            if category.category_id == category_id: return category
        raise KeyError(category_id)

    def segment(self, category_id: CategoryId, start: datetime, end: datetime) -> ConfigurationSegment:
        """Project one category's historical mode/base/source over an already resolved interval."""
        entry = self.entry(category_id)
        basis = tuple(BasisSource(category_id=s.category_id, source_id=s.source_id)
            for s in self.categories if s.category_id != "CAT-01" and s.has_meter)
        mode = "measured" if entry.has_meter else "calculated" if category_id == "CAT-01" and basis else "unavailable"
        return ConfigurationSegment(start=start, end=end, configuration_revision=self.revision,
            category_revision=entry.category_revision, source_mode=mode, source_id=entry.source_id,
            base_categories=tuple(b.category_id for b in basis) if mode == "calculated" else (),
            basis_sources=basis if mode == "calculated" else (),
            basis_category_revisions=tuple(self.entry(b.category_id).category_revision for b in basis) if mode == "calculated" else ())


class ValidatedMeasurement(Period):
    """Normalized physical reading; accepting/persisting/assigning a record ID remains002's duty."""

    building_id: UUID
    category_id: CategoryId
    source_id: UUID
    original_value: Annotated[Decimal, BeforeValidator(decimal_value)]
    original_unit: Literal["Wh", "kWh", "MWh"]
    original_value_text: str
    energy_kwh: Energy
    configuration_revision: Revision
    category_revision: Revision
    source_evidence_ref: str
    correlation_ref: str

    @model_validator(mode="after")
    def consistent_energy(self):
        """Prevent inconsistent originals/normalized energy from crossing the shared validated DTO boundary."""
        if decimal_value(self.original_value_text) != self.original_value or to_kwh(self.original_value, self.original_unit) != self.energy_kwh:
            raise ValueError("inconsistent_energy_evidence")
        return self


class Contribution(Period):
    """One already accepted physical partial and its exact interval/source/revisions."""

    measurement_id: UUID
    measurement_revision: Revision
    category_id: CategoryId
    source_id: UUID
    category_revision: Revision
    energy_kwh: Energy

    @model_validator(mode="after")
    def partial(self):
        """Prevent recursive totals from becoming calculation inputs."""
        if self.category_id == "CAT-01": raise ValueError("total_cannot_contribute")
        return self


class TotalCandidate(Period):
    """Pure candidate, never an incorporated row; diagnostics carry no numeric surrogate."""

    building_id: UUID
    category_id: Literal["CAT-01"] = "CAT-01"
    configuration_revision: Revision
    category_revision: Revision | None
    base_categories: tuple[CategoryId, ...]
    contributions: tuple[Contribution, ...]
    energy_kwh: Annotated[Decimal, BeforeValidator(decimal_value)] | None
    status: Literal["complete", "incomplete", "no_basis"]
    missing_categories: tuple[CategoryId, ...] = ()
    reason_code: Literal["missing_contributions", "calculation_configuration_changed", "no_calculation_basis", "measured_total"] | None
    configuration_segments: tuple[ConfigurationSegment, ...]

    @model_validator(mode="after")
    def consistent(self):
        """Complete candidates require energy; diagnostics never assert a value or artificial revision."""
        if self.status == "complete":
            if self.energy_kwh is None or not self.base_categories or self.missing_categories or self.reason_code:
                raise ValueError("invalid_complete_total")
            supported_energy(self.energy_kwh, calculated=True)
            if tuple(c.category_id for c in self.contributions) != self.base_categories or len(set(self.base_categories)) != len(self.base_categories):
                raise ValueError("invalid_total_contributions")
            if any(c.start != self.start or c.end != self.end for c in self.contributions):
                raise ValueError("unaligned_total_contributions")
            with localcontext(exact_context()):
                if sum((c.energy_kwh for c in self.contributions), Decimal(0)) != self.energy_kwh:
                    raise ValueError("inconsistent_total_energy")
        elif self.energy_kwh is not None: raise ValueError("diagnostic_has_energy")
        if self.reason_code == "calculation_configuration_changed":
            if self.category_revision is not None or self.base_categories or self.contributions or self.missing_categories:
                raise ValueError("invalid_changed_configuration")
            if len({s.category_revision for s in self.configuration_segments}) < 2:
                raise ValueError("changed_configuration_needs_segments")
        elif self.category_revision is None: raise ValueError("category_revision_required")
        return self


class ReconfigurationBounds(DomainModel):
    """002-preserved history, independent from retained detail; every requested category must be present."""

    has_accepted_history: Annotated[bool, Field(strict=True)]
    latest_interval_end_by_category: dict[CategoryId, Instant | None]

    @model_validator(mode="after")
    def history_consistency(self):
        """A concrete maximum implies global accepted history; missing detail cannot erase it."""
        if not self.has_accepted_history and any(v is not None for v in self.latest_interval_end_by_category.values()):
            raise ValueError("inconsistent_history_bounds")
        return self

    def require_categories(self, category_ids):
        """Reject missing or unsolicited keys rather than treating absent provider data as null."""
        if set(category_ids) != set(self.latest_interval_end_by_category): raise ValueError("incomplete_history_bounds")


class ReceptionResult(DomainModel):
    """Per-record002 result; first acceptance references survive duplicates and no writes occur here."""

    position: Annotated[int, Field(ge=0, strict=True)]
    status: Literal["accepted", "duplicate", "rejected"]
    reason_code: str | None = None
    measurement_id: UUID | None = None
    measurement_revision: Revision | None = None
    category_revision: Revision | None = None
    category_id: CategoryId | None = None
    next_admissible_at: Instant | None = None
    correlation_ref: str
    first_incorporated_at: Instant | None = None

    @model_validator(mode="after")
    def reference(self):
        """Require durable accepted/duplicate references; rejection requires a reason and no record ID."""
        if self.status in ("accepted", "duplicate"):
            if any(v is None for v in (self.measurement_id, self.measurement_revision, self.category_revision, self.category_id)):
                raise ValueError("accepted_reference_required")
        elif not self.reason_code or self.measurement_id is not None:
            raise ValueError("invalid_rejection")
        return self

#002 owns the following PostgreSQL metadata.001 DTOs above do not import reception/storage.
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ecs_ec.core.database import Base


class RetainedRow:
    """Persist a minimum deadline; services only extend it on substantive incorporation/revision."""

    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RevisionRow:
    """Positive application-assigned revision; concrete tables add their database check."""

    revision: Mapped[int] = mapped_column(Integer, default=1)


class ReceptionAttempt(RetainedRow, Base):
    """Fixed complete input before category commits; adapter UUID differs from publication identity."""

    __tablename__ = 'reception_attempt'
    __table_args__ = (
        CheckConstraint("status IN ('processing','completed','partial_failure')", name='state'),
        CheckConstraint('input_schema_version > 0', name='schema_version'),
        CheckConstraint("jsonb_typeof(input_manifest) = 'object'", name='manifest_object'),
        CheckConstraint("length(input_digest) = 64", name='digest'),
        CheckConstraint("(status = 'completed') = (completed_at IS NOT NULL)", name='completed_time'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    publication_ref: Mapped[str] = mapped_column(String(200))
    correlation_ref: Mapped[str] = mapped_column(String(200))
    process_ref: Mapped[str] = mapped_column(String(200))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    input_schema_version: Mapped[int] = mapped_column(Integer)
    input_manifest: Mapped[dict] = mapped_column(JSONB)
    input_digest: Mapped[str] = mapped_column(String(64))


class CategoryUpdate(RetainedRow, RevisionRow, Base):
    """One category transaction with counts; calculated updates have no physical attempt."""

    __tablename__ = 'category_update'
    __table_args__ = (UniqueConstraint('attempt_id', 'category_id'),
        CheckConstraint("kind IN ('physical','calculated')", name='kind'),
        CheckConstraint('revision > 0 AND accepted_count >= 0 AND duplicate_count >= 0 AND rejected_count >= 0', name='counts_revision'),
        CheckConstraint('(accepted_count > 0) = (new_data_at IS NOT NULL)', name='new_data'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    attempt_id: Mapped[UUID | None] = mapped_column(ForeignKey('reception_attempt.id', ondelete='RESTRICT'))
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    category_id: Mapped[str] = mapped_column(ForeignKey('consumption_category.id', ondelete='RESTRICT'))
    kind: Mapped[str] = mapped_column(String(20))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    new_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_new_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_admissible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_count: Mapped[int] = mapped_column(Integer)
    duplicate_count: Mapped[int] = mapped_column(Integer)
    rejected_count: Mapped[int] = mapped_column(Integer)


class ReceptionRecordResult(RetainedRow, Base):
    """Position-stable committed classification; invalid categories have no update/category FK."""

    __tablename__ = 'reception_record_result'
    __table_args__ = (UniqueConstraint('attempt_id', 'input_position'),
        CheckConstraint("status IN ('accepted','duplicate','rejected')", name='status'),
        CheckConstraint('input_position >= 0', name='position'),
        CheckConstraint("(status = 'rejected' AND reason_code IS NOT NULL AND record_id IS NULL) OR (status IN ('accepted','duplicate') AND record_id IS NOT NULL)", name='reference'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey('reception_attempt.id', ondelete='RESTRICT'))
    category_update_id: Mapped[UUID | None] = mapped_column(ForeignKey('category_update.id', ondelete='RESTRICT'))
    input_position: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[str | None] = mapped_column(ForeignKey('consumption_category.id', ondelete='RESTRICT'))
    record_id: Mapped[UUID | None] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'))
    status: Mapped[str] = mapped_column(String(20))
    reason_code: Mapped[str | None] = mapped_column(String(100))
    next_admissible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BuildingReceptionState(Base):
    """Permanent global history flag; retiring payload never resets it."""

    __tablename__ = 'building_reception_state'
    __table_args__ = (CheckConstraint('has_accepted_history = (first_new_data_at IS NOT NULL)', name='history'),)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'), primary_key=True)
    has_accepted_history: Mapped[bool] = mapped_column(Boolean, default=False)
    first_new_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CategoryReceptionState(RevisionRow, Base):
    """Durable900s admission and all-time maximum independent from retained payloads."""

    __tablename__ = 'category_reception_state'
    __table_args__ = (CheckConstraint('revision > 0', name='revision'),
        CheckConstraint("(last_new_data_at IS NULL AND next_admissible_at IS NULL AND latest_interval_end IS NULL) OR (last_new_data_at IS NOT NULL AND next_admissible_at = last_new_data_at + interval '900 seconds' AND latest_interval_end IS NOT NULL)", name='admission'))
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'), primary_key=True)
    category_id: Mapped[str] = mapped_column(ForeignKey('consumption_category.id', ondelete='RESTRICT'), primary_key=True)
    last_new_data_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_admissible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_interval_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncorporatedRecord(RetainedRow, RevisionRow, Base):
    """Permanent immutable normalized ledger; identity/exclusion survive allowed detail withdrawal."""

    __tablename__ = 'incorporated_record'
    __table_args__ = (
        ForeignKeyConstraint(['building_id', 'configuration_revision'], ['consumption_installation.building_id', 'consumption_installation.revision'], ondelete='RESTRICT', name='fk_record_configuration'),
        UniqueConstraint('building_id', 'source_id', 'category_id', 'start', 'end', name='uq_record_physical'),
        UniqueConstraint('building_id', 'logical_source_key', 'category_revision', 'start', 'end', name='uq_record_calculated'),
        ExcludeConstraint(('building_id', '='), ('category_id', '='), (func.tstzrange(text('start'), text('"end"'), '[)'), '&&'), using='gist', name='ex_record_overlap'),
        CheckConstraint('start < "end"', name='interval'),
        CheckConstraint('revision > 0 AND configuration_revision > 0 AND category_revision > 0', name='revisions'),
        CheckConstraint("(kind='measured' AND source_id IS NOT NULL AND logical_source_key IS NULL AND energy_quanta < power(10::numeric,45)) OR (kind='calculated' AND category_id='CAT-01' AND source_id IS NULL AND logical_source_key IS NOT NULL AND energy_quanta <= 6*(power(10::numeric,45)-1))", name='source_energy'),
        CheckConstraint('energy_quanta >= 0 AND energy_quanta = trunc(energy_quanta) AND energy_kwh * 1000000000000000::numeric = energy_quanta', name='exact_energy'),
        CheckConstraint("(detail_state='retained' AND detail_withdrawn_at IS NULL) OR (detail_state='withdrawn' AND detail_withdrawn_at IS NOT NULL)", name='detail'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'), index=True)
    category_id: Mapped[str] = mapped_column(ForeignKey('consumption_category.id', ondelete='RESTRICT'))
    kind: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey('consumption_source.id', ondelete='RESTRICT'))
    logical_source_key: Mapped[str | None] = mapped_column(String(100))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric)
    energy_quanta: Mapped[Decimal] = mapped_column(Numeric)
    configuration_revision: Mapped[int] = mapped_column(Integer)
    category_revision: Mapped[int] = mapped_column(Integer)
    first_incorporated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    update_id: Mapped[UUID] = mapped_column(ForeignKey('category_update.id', ondelete='RESTRICT'))
    source_evidence_ref: Mapped[str] = mapped_column(String(200))
    correlation_ref: Mapped[str] = mapped_column(String(200))
    provenance_snapshot: Mapped[dict] = mapped_column(JSONB)
    detail_state: Mapped[str] = mapped_column(String(20))
    detail_withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_timezone: Mapped[str] = mapped_column(String(100))
    tzdata_version: Mapped[str] = mapped_column(String(40))


class AcceptedMeasurement(RetainedRow, Base):
    """Retained first physical original; equivalent re-sends cannot replace representation/unit."""

    __tablename__ = 'accepted_measurement'
    __table_args__ = (CheckConstraint("original_unit IN ('Wh','kWh','MWh')", name='unit'),
        CheckConstraint('original_value >= 0', name='nonnegative'))
    record_id: Mapped[UUID] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'), primary_key=True)
    original_value: Mapped[Decimal] = mapped_column(Numeric)
    original_unit: Mapped[str] = mapped_column(String(3))
    original_value_text: Mapped[str] = mapped_column(String)
    first_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncorporatedTotal(RetainedRow, Base):
    """Retained calculated payload with exact immutable basis and accepted-contribution snapshots."""

    __tablename__ = 'incorporated_total'
    __table_args__ = (CheckConstraint('jsonb_array_length(base_categories) > 0', name='basis'),)
    record_id: Mapped[UUID] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'), primary_key=True)
    first_incorporated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    base_categories: Mapped[list] = mapped_column(JSONB)
    basis_sources: Mapped[list] = mapped_column(JSONB)
    contributions: Mapped[list] = mapped_column(JSONB)


class TotalEvaluationRequest(RetainedRow, RevisionRow, Base):
    """Durable work recorded atomically with partials, including before any candidate exists."""

    __tablename__ = 'total_evaluation_request'
    __table_args__ = (UniqueConstraint('building_id', 'start', 'end'),
        CheckConstraint('start < "end" AND revision > 0', name='interval_revision'),
        CheckConstraint("(status='pending' AND processed_at IS NULL) OR (status='processed' AND processed_at IS NOT NULL)", name='status'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger_update_id: Mapped[UUID] = mapped_column(ForeignKey('category_update.id', ondelete='RESTRICT'))
    correlation_ref: Mapped[str] = mapped_column(String(200))


class TotalCalculationState(RetainedRow, RevisionRow, Base):
    """Persisted diagnosis/pending candidate, never a numeric published measurement before incorporation."""

    __tablename__ = 'total_calculation_state'
    __table_args__ = (UniqueConstraint('building_id', 'start', 'end'),
        CheckConstraint('start < "end" AND revision > 0', name='interval_revision'),
        CheckConstraint("status IN ('incomplete','no_basis','pending','incorporated')", name='status'),
        CheckConstraint("(status='incorporated') = (incorporated_record_id IS NOT NULL)", name='incorporation'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), index=True)
    reason_code: Mapped[str | None] = mapped_column(String(100))
    configuration_segments: Mapped[list] = mapped_column(JSONB)
    base_categories: Mapped[list] = mapped_column(JSONB)
    contribution_refs: Mapped[list] = mapped_column(JSONB)
    missing_categories: Mapped[list] = mapped_column(JSONB)
    next_admissible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    incorporated_record_id: Mapped[UUID | None] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsumptionAggregate(RetainedRow, RevisionRow, Base):
    """Exact integer sum/real duration, updated directly from immutable records at each calendar level."""

    __tablename__ = 'consumption_aggregate'
    __table_args__ = (UniqueConstraint('building_id', 'category_id', 'granularity', 'timezone', 'start', 'end'),
        CheckConstraint("granularity IN ('hour','day','month','year')", name='granularity'),
        CheckConstraint('start < "end" AND revision > 0 AND contribution_count > 0 AND covered_duration_us > 0', name='interval_counts'),
        CheckConstraint("energy_quanta >= 0 AND energy_quanta < 'Infinity'::numeric AND energy_quanta=trunc(energy_quanta)", name='quanta'),
        CheckConstraint('covered_duration_us=trunc(covered_duration_us) AND covered_duration_us <= extract(epoch FROM ("end"-start))*1000000', name='coverage'))
    id: Mapped[UUID] = mapped_column(primary_key=True)
    building_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_building.id', ondelete='RESTRICT'))
    category_id: Mapped[str] = mapped_column(ForeignKey('consumption_category.id', ondelete='RESTRICT'))
    granularity: Mapped[str] = mapped_column(String(10))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100))
    start_offset: Mapped[str] = mapped_column(String(20))
    end_offset: Mapped[str] = mapped_column(String(20))
    tzdata_version: Mapped[str] = mapped_column(String(40))
    energy_quanta: Mapped[Decimal] = mapped_column(Numeric)
    covered_duration_us: Mapped[Decimal] = mapped_column(Numeric)
    contribution_count: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_new_data_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AggregateContribution(Base):
    """Unique retained ledger reference/snapshot; withdrawal never subtracts this contribution."""

    __tablename__ = 'aggregate_contribution'
    __table_args__ = (CheckConstraint('record_revision > 0', name='revision'),)
    aggregate_id: Mapped[UUID] = mapped_column(ForeignKey('consumption_aggregate.id', ondelete='RESTRICT'), primary_key=True)
    record_id: Mapped[UUID] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'), primary_key=True)
    record_revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    incorporated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CalculationContributionReference(Base):
    """Relational protection for candidate/total JSON snapshots; referenced ledger evidence cannot vanish."""

    __tablename__ = 'calculation_contribution_reference'
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey('total_calculation_state.id', ondelete='RESTRICT'), primary_key=True)
    record_id: Mapped[UUID] = mapped_column(ForeignKey('incorporated_record.id', ondelete='RESTRICT'), primary_key=True)
