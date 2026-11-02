"""Closed001 HTTP DTOs; exact strings preserve energy and local offset timestamps."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ecs_ec.consumption.models import (CategoryId, CategorySource, ConfigurationInput, DomainModel,
    InstallationRevision, Revision, Timezone)


class PeriodView(DomainModel):
    """Wire interval retaining the building offset, unlike normalized internal UTC periods."""

    start: str
    end: str
    timezone: Timezone


class CategoryView(DomainModel):
    """Fixed public category identity and scope without editable catalog fields."""

    id: CategoryId
    name: str
    scope: str


class CategoryStatus(CategoryView):
    """Current source semantics; absence never implies numeric zero."""

    has_meter: bool
    source_mode: Literal['measured', 'calculated', 'unavailable']
    base_categories: tuple[CategoryId, ...]
    category_revision: Revision | None


class Catalog(DomainModel):
    """Seven categories and one coherent global retained-history extent."""

    building_id: UUID
    timezone: Timezone
    cutoff_at: str
    default_period: PeriodView
    categories: tuple[CategoryStatus, ...]


class Configuration(DomainModel):
    """Administrative revision projection; actor metadata stays out of this wire view."""

    id: UUID
    building_id: UUID
    revision: Revision
    effective_from: str
    recorded_at: str
    timezone: Timezone
    categories: tuple[CategorySource, ...]


class SegmentView(DomainModel):
    """Historical source/base over a clipped interval, without internal verification-only fields."""

    start: str
    end: str
    configuration_revision: Revision
    category_revision: Revision
    source_mode: Literal['measured', 'calculated', 'unavailable']
    source_id: UUID | None
    base_categories: tuple[CategoryId, ...]
    basis_sources: tuple['BasisView', ...]


class BasisView(DomainModel):
    """Source UUID paired with a physical partial category."""

    category_id: CategoryId
    source_id: UUID


class ContributionView(DomainModel):
    """Original accepted contribution and its stable category revision."""

    measurement_id: UUID
    measurement_revision: Revision
    category_id: CategoryId
    source_id: UUID
    start: str
    end: str
    energy_kwh: str
    category_revision: Revision


class MeasuredOrigin(DomainModel):
    """Original measurement unit/text plus stable physical source."""

    kind: Literal['measured'] = 'measured'
    source_id: UUID
    original_value: str
    original_unit: Literal['Wh', 'kWh', 'MWh']


class CalculatedOrigin(DomainModel):
    """Captured contribution evidence; this view performs no recalculation."""

    kind: Literal['calculated'] = 'calculated'
    base_categories: tuple[CategoryId, ...]
    contributions: tuple[ContributionView, ...]


class DetailRow(DomainModel):
    """One incorporated numeric interval, shared verbatim by graph and table."""

    record_id: UUID
    revision: Revision
    start: str
    end: str
    energy_kwh: str
    first_incorporated_at: str
    configuration_revision: Revision
    category_revision: Revision
    origin: Annotated[MeasuredOrigin | CalculatedOrigin, Field(discriminator='kind')]


class Diagnostic(DomainModel):
    """Nonnumeric candidate with explicit reason; never a surrogate zero-energy row."""

    start: str
    end: str
    configuration_revision: Revision
    reason_code: Literal['missing_contributions', 'pending_incorporation', 'calculation_configuration_changed']
    missing_categories: tuple[CategoryId, ...]
    next_admissible_at: str | None
    category_revision: Revision | None
    configuration_segments: tuple[SegmentView, ...]

    @model_validator(mode='after')
    def coherent_reason(self):
        """Reject fictional missing categories/wait dates on a changed calculation configuration."""
        if self.reason_code == 'calculation_configuration_changed':
            if (self.category_revision is not None or self.missing_categories or self.next_admissible_at is not None
                    or len({s.category_revision for s in self.configuration_segments}) < 2):
                raise ValueError('invalid_configuration_diagnostic')
        elif self.category_revision is None:
            raise ValueError('diagnostic_revision_required')
        return self


class WarningView(DomainModel):
    """Bounded warning vocabulary with observed counts and a safe static explanation."""

    code: Literal['crossing_intervals_excluded', 'observed_gaps', 'no_calculation_basis',
        'partial_calculation_scope', 'source_unavailable_in_segment']
    count: Annotated[int, Field(ge=0)]
    message: str


class DetailResult(DomainModel):
    """Full selected detail without clipping, pagination, interpolation or reads with side effects."""

    request_ref: UUID
    building_id: UUID
    category: CategoryView
    period: PeriodView
    cutoff_at: str
    state: Literal['available', 'no_meter', 'no_data', 'incomplete']
    source_mode: Literal['measured', 'calculated', 'mixed', 'unavailable']
    configuration_segments: tuple[SegmentView, ...]
    rows: tuple[DetailRow, ...]
    diagnostics: tuple[Diagnostic, ...]
    warnings: tuple[WarningView, ...]


def configuration_view(revision: InstallationRevision):
    """Copy only declared administrative fields, with explicit IANA offsets."""
    from ecs_ec.consumption.periods import timestamp
    return Configuration(**revision.model_dump(exclude={'created_by', 'effective_from', 'recorded_at'}),
        effective_from=timestamp(revision.effective_from, revision.timezone),
        recorded_at=timestamp(revision.recorded_at, revision.timezone))


SegmentView.model_rebuild()
