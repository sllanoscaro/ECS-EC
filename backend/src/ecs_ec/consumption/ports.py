"""In-process boundaries;002 implements reception/storage without a dependency on001 acceptance."""

from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID

from ecs_ec.consumption.models import CategoryId, ConfigurationSegment, Contribution, ReceptionResult, ReconfigurationBounds, TotalCandidate, ValidatedMeasurement
from ecs_ec.core.unit_of_work import UnitOfWork


class MeasurementValidator(Protocol):
    """001 pure normalization port; invalid entries raise a safe per-record domain error."""

    def normalize(self, record: Mapping[str, Any], segments: Sequence[ConfigurationSegment]) -> ValidatedMeasurement:
        """Validate all historical category segments, preserve evidence and return exact kWh without writes."""
        ...


class TotalCalculator(Protocol):
    """001 pure evaluation port; a complete candidate still requires002's timed incorporation."""

    def evaluate(self, *, building_id: UUID, start: datetime, end: datetime,
                 segments: Sequence[ConfigurationSegment], contributions: Sequence[Contribution]) -> TotalCandidate:
        """Return a candidate or explicit nonnumeric diagnosis; do not read clocks, write or accept."""
        ...


class Reception(Protocol):
    """002-owned publication admission; duplicates/rejections never advance incorporation time."""

    async def accept(self, attempt_id: UUID, building_id: UUID, publication_ref: str,
                     process: str, records: Sequence[Mapping[str, Any]], correlation_ref: str) -> 'ReceptionOutcome':
        """Return002 ReceptionOutcome;002 owns per-category UoWs and recovers immutable attempt results.

        Match002's attempt-aware contract: an identical attempt resumes only missing
        durable results, while a new re-send has a fresh UUID. No provider is installed here.
        """
        ...

    async def read_attempt(self, attempt_id: UUID, building_id: UUID, process: str) -> 'AttemptLookup':
        """Return002 AttemptLookup without creating/resuming an attempt or modifying incorporation time."""
        ...


class MeasurementStore(Protocol):
    """002-owned read boundary; detail reads share REPEATABLE READ/cutoff and have no business writes."""

    async def read_detail(self, building_id: UUID, category_id: CategoryId, start: datetime, end: datetime,
                          cutoff_at: datetime, unit_of_work: UnitOfWork):
        """Return incorporated rows/diagnostics including boundary crossings; never recalculate totals."""
        ...

    async def read_extent(self, building_id: UUID, cutoff_at: datetime, unit_of_work: UnitOfWork):
        """Return global retained detail extent or explicit absence, never per-category inferred zero."""
        ...

    async def read_update_state(self, building_id: UUID, category_id: CategoryId,
                                cutoff_at: datetime, unit_of_work: UnitOfWork):
        """Return last new incorporation and next admissible instant, including calculatedCAT-01."""
        ...

    async def read_reconfiguration_bounds(self, building_id: UUID, category_ids: Sequence[CategoryId],
                                         unit_of_work: UnitOfWork) -> ReconfigurationBounds:
        """Read complete durable maxima after shared locks in READ COMMITTED, including retired detail."""
        ...

# Typed002 snapshots share001's immutable, exact UTC domain primitives.
from pydantic import model_validator
from ecs_ec.consumption.models import DomainModel, Instant, Revision, Period
from typing import Literal
from decimal import Decimal


class CategoryUpdateResult(DomainModel):
    """Durable category transaction summary; no new_data_at for duplicate/rejected-only input."""

    id: UUID
    category_id: CategoryId
    kind: Literal['physical', 'calculated']
    evaluated_at: Instant
    new_data_at: Instant | None
    previous_new_data_at: Instant | None
    next_admissible_at: Instant | None
    accepted_count: int
    duplicate_count: int
    rejected_count: int
    revision: Revision


class ReceptionOutcome(DomainModel):
    """One immutable-attempt capture; missing positions are explicit until all results commit."""

    attempt_id: UUID
    building_id: UUID
    correlation_ref: str
    received_at: Instant
    completed_at: Instant | None = None
    state: Literal['processing', 'completed', 'partial_failure']
    results: tuple[ReceptionResult, ...]
    updates: tuple[CategoryUpdateResult, ...]
    pending_positions: tuple[int, ...] = ()

    @model_validator(mode='after')
    def completion(self):
        """Do not claim completion when input positions are still missing."""
        if self.state == 'completed' and (self.pending_positions or self.completed_at is None):
            raise ValueError('incomplete_outcome')
        return self


class AttemptLookup(DomainModel):
    """Authorized read result; database/authentication errors are never represented as not_found."""

    attempt_id: UUID
    building_id: UUID
    state: Literal['not_found', 'processing', 'completed', 'partial_failure']
    outcome: ReceptionOutcome | None

    @model_validator(mode='after')
    def presence(self):
        """Require a matching coherent outcome for every persisted state."""
        if (self.state == 'not_found') != (self.outcome is None): raise ValueError('invalid_attempt_lookup')
        if self.outcome and (self.outcome.attempt_id != self.attempt_id or self.outcome.building_id != self.building_id
                or self.outcome.state != self.state): raise ValueError('mismatched_attempt_lookup')
        return self


class StoredDetail(Period):
    """Retained original or calculated payload with immutable identity/provenance; no retired reconstruction."""

    record_id: UUID
    revision: Revision
    category_id: CategoryId
    kind: Literal['measured', 'calculated']
    energy_kwh: Decimal
    original_value_text: str | None
    original_unit: Literal['Wh', 'kWh', 'MWh'] | None
    first_incorporated_at: Instant
    retain_until: Instant
    provenance_snapshot: dict


class DetailRead(DomainModel):
    """Contained retained detail and explicit crossings/withdrawal evidence in the caller's capture."""

    rows: tuple[StoredDetail, ...]
    crossing_record_ids: tuple[UUID, ...]
    withdrawn_record_ids: tuple[UUID, ...]
    diagnostics: tuple['CalculationDiagnostic', ...] = ()
    crossing_diagnostic_ids: tuple[UUID, ...] = ()


class HistoryExtent(DomainModel):
    """Global retained extent; both bounds are null when no payload remains."""

    start: Instant | None
    end: Instant | None


class UpdateState(DomainModel):
    """Per-category durable limits, independent from retained detail and source timestamps."""

    last_new_data_at: Instant | None
    next_admissible_at: Instant | None
    latest_interval_end: Instant | None
    revision: Revision

from typing import Annotated
from pydantic import Field
from ecs_ec.consumption.models import ConfigurationSegment, Timezone

Granularity = Literal['hour', 'day', 'month', 'year']
DurationText = Annotated[str, Field(pattern=r'^(0|[1-9][0-9]*)$')]
PositiveDurationText = Annotated[str, Field(pattern=r'^[1-9][0-9]*$')]
DecimalText = Annotated[str, Field(pattern=r'^(0|[1-9][0-9]*)(\.[0-9]+)?$')]


class ZonedPeriod(Period):
    """UTC interval with explicit IANA display/calendar zone; never use the browser's zone."""

    timezone: Timezone


class AggregateSelection(ZonedPeriod):
    """Complete002 grouped selection; authorization and offset correspondence belong to its adapters."""

    building_id: UUID
    category_id: CategoryId
    granularity: Granularity


class HistoryWarning(DomainModel):
    """Sane projection warning with optional exact intervals/record references, never exception bodies."""

    code: Literal['measurement_crosses_block', 'filter_excludes_block', 'partial_calculation_basis',
        'no_calculation_basis', 'before_operation', 'detail_withdrawn', 'unconfigured_period', 'missing_coverage']
    start: Instant | None = None
    end: Instant | None = None
    record_refs: tuple[UUID, ...] = ()
    detail: str


class CalculationDiagnostic(Period):
    """Nonnumeric persistedCAT-01 diagnosis; pending incorporation never masquerades as missing evidence."""

    id: UUID
    revision: Revision
    status: Literal['incomplete', 'no_basis', 'pending']
    reason_code: str
    category_revision: Revision | None
    configuration_segments: tuple[ConfigurationSegment, ...]
    base_categories: tuple[CategoryId, ...]
    contributions: tuple[Contribution, ...]
    missing_categories: tuple[CategoryId, ...]
    next_admissible_at: Instant | None


class AggregateBlock(ZonedPeriod):
    """Exact grouped output contract; numeric strings preserve arbitrary energy/duration precision over HTTP."""

    aggregate_id: UUID | None
    revision: Revision | None
    duration_us: PositiveDurationText
    covered_duration_us: DurationText
    energy_kwh: DecimalText | None
    coverage_percent: Annotated[str, Field(pattern=r'^(0|[1-9][0-9]{0,2})(\.[0-9]{1,6})?$')]
    coverage_state: Literal['complete', 'incomplete', 'no_data']
    temporal_state: Literal['not_started', 'ongoing', 'finished']
    contribution_count: Annotated[int, Field(ge=0, strict=True)]
    source_mode: Literal['measured', 'calculated', 'mixed', 'unavailable']
    provenance_segments: tuple[ConfigurationSegment, ...]
    created_at: Instant | None
    last_new_data_at: Instant | None
    retain_until: Instant | None
    warnings: tuple[HistoryWarning, ...]

    @model_validator(mode='after')
    def consistent(self):
        """Classify exact coverage before rounding and forbid fabricated energy/identity in empty blocks."""
        total, covered = int(self.duration_us), int(self.covered_duration_us)
        if covered > total or Decimal(self.coverage_percent) > 100: raise ValueError('invalid_coverage')
        state = 'no_data' if covered == 0 else 'complete' if covered == total else 'incomplete'
        if state != self.coverage_state: raise ValueError('inconsistent_coverage_state')
        if self.contribution_count == 0:
            if covered or any(v is not None for v in (self.aggregate_id, self.revision, self.energy_kwh,
                    self.created_at, self.last_new_data_at, self.retain_until)): raise ValueError('fabricated_empty_block')
        elif not covered or any(v is None for v in (self.aggregate_id, self.revision, self.energy_kwh,
                self.created_at, self.last_new_data_at, self.retain_until)): raise ValueError('incomplete_aggregate_evidence')
        return self


class ExcludedBlock(Period):
    """Unclipped calendar block omitted because an exact filter contains only part of it."""

    reason_code: Literal['filter_start', 'filter_end', 'filter_both']


class AggregateQueryResult(DomainModel):
    """002 grouped capture contract, shared unchanged by table/chart; no read-side persistence implied."""

    request_ref: UUID
    building_id: UUID
    category_id: CategoryId
    period: ZonedPeriod
    granularity: Granularity
    unit: Literal['kWh'] = 'kWh'
    cutoff_at: Instant
    state: Literal['available', 'incomplete', 'no_data', 'no_meter']
    source_mode: Literal['measured', 'calculated', 'mixed', 'unavailable']
    configuration_segments: tuple[ConfigurationSegment, ...]
    blocks: tuple[AggregateBlock, ...]
    excluded_blocks: tuple[ExcludedBlock, ...]
    diagnostics: tuple[CalculationDiagnostic, ...]
    warnings: tuple[HistoryWarning, ...]
    reason_code: str | None


class AdmissibleWindow(DomainModel):
    """002 consumer contract: a finished complete physical/logical window or an explicit non-evaluable reason."""

    status: Literal['available', 'not_evaluable']
    building_id: UUID
    category_id: CategoryId
    resolution: Literal['intervalo', 'hour', 'day', 'month', 'year']
    timezone: Timezone
    cutoff_at: Instant
    period: Period | None
    energy_kwh: DecimalText | None
    duration_us: DurationText
    covered_duration_us: DurationText
    source_mode: Literal['measured', 'calculated', 'mixed', 'unavailable']
    configuration_segments: tuple[ConfigurationSegment, ...]
    record_refs: tuple[UUID, ...]
    evidence_revision: str | None
    cursor: str | None
    reason_code: Literal['no_source', 'no_complete_window', 'insufficient_resolution', 'insufficient_evidence'] | None

    @model_validator(mode='after')
    def available_evidence(self):
        """Availability requires an ended window with real exact coverage and stable evidence."""
        if self.status == 'available' and (self.period is None or self.period.end > self.cutoff_at
                or self.energy_kwh is None or not self.record_refs or not self.evidence_revision or not self.cursor
                or self.reason_code is not None or int(self.duration_us) == 0
                or self.duration_us != self.covered_duration_us or self.source_mode == 'unavailable'):
            raise ValueError('unavailable_window_evidence')
        if self.status == 'not_evaluable' and (self.energy_kwh is not None or self.reason_code is None):
            raise ValueError('invalid_not_evaluable_window')
        return self


class PhysicalHistorySnapshot(DomainModel):
    """002 evidence contract for004; limitations never replace a general physical meter with calculatedCAT-01."""

    building_id: UUID
    category_id: Literal['CAT-01'] = 'CAT-01'
    period: ZonedPeriod
    cutoff_at: Instant
    rows: tuple[StoredDetail, ...]
    configuration_segments: tuple[ConfigurationSegment, ...]
    evidence_revision: str | None
    reason_code: Literal['calculated_general', 'no_source', 'insufficient_resolution', 'insufficient_evidence'] | None


class HistoryQueries(Protocol):
    """002 grouped/consumer boundary; implementation is separate from001's pure domain/configuration."""

    async def query_aggregates(self, selection: AggregateSelection, principal, unit_of_work: UnitOfWork | None = None) -> AggregateQueryResult:
        """Authorize and copy one coherent grouped capture; GET must not incorporate or extend retention."""
        ...

    async def latest_admissible_window(self, *, building_id: UUID, category_id: CategoryId, resolution: str,
                                      timezone: str, activation_at: datetime, cursor: str | None,
                                      cutoff_at: datetime, unit_of_work: UnitOfWork) -> AdmissibleWindow:
        """Select from actual evidence/resolution, projecting another zone without persisting buckets."""
        ...

    async def read_general_snapshot(self, building_id: UUID, start: datetime, end: datetime,
                                    cutoff_at: datetime, unit_of_work: UnitOfWork) -> PhysicalHistorySnapshot:
        """Copy physicalCAT-01 intervals with explicit limitations for004, without applying tariff rules."""
        ...

    async def read_demand_history(self, building_id: UUID, start: datetime, end: datetime,
                                  cutoff_at: datetime, unit_of_work: UnitOfWork) -> PhysicalHistorySnapshot:
        """Expose only source-proven physical resolution; do not reconstruct fifteen minutes from hourly energy."""
        ...


# DetailRead refers to the diagnostic defined later to preserve the existing001/002 DTO order.
DetailRead.model_rebuild()
