"""Closed004 commands and immutable evidence DTOs; HTTP decimals are finite textual values."""

import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, Field, model_validator

from ecs_ec.consumption.models import DomainModel, Instant, Period, Timezone
from ecs_ec.costs.money import decimal_text, number

Code = Annotated[str, Field(pattern=r'^[a-z][a-z0-9_.:-]{0,99}$', max_length=100)]
Reference = Annotated[str, Field(min_length=1, max_length=300)]
Revision = Annotated[int, Field(gt=0, strict=True)]
Money = Annotated[str, AfterValidator(lambda value: decimal_text(number(value)))]


def nonnegative(value):
    """Require a finite nonnegative textual quantity or price without inventing a missing value."""
    if number(value) < 0:
        raise ValueError('negative_quantity')
    return value


Quantity = Annotated[Money, AfterValidator(nonnegative)]
Kind = Literal['energia', 'transmision', 'servicio_publico', 'fijo', 'demanda_punta', 'potencia_suministrada', 'impuesto', 'otro_documentado']
TaxBasis = Literal['neto', 'impuesto_incluido', 'impuesto_separado']


class RoundingPolicy(DomainModel):
    """Captured precision, actual quantum multiple, rounding mode and stage; no implicit financial defaults."""

    precision: Annotated[int, Field(ge=50, le=128, strict=True)]
    quantum: Quantity
    mode: Literal['ROUND_HALF_UP', 'ROUND_HALF_EVEN', 'ROUND_DOWN', 'ROUND_UP']
    stage: Literal['component', 'total']

    @model_validator(mode='after')
    def positive_quantum(self):
        """Reject a zero quantum instead of allowing division by zero during calculation."""
        if not number(self.quantum):
            raise ValueError('positive_quantum_required')
        return self


class PeakCalendar(DomainModel):
    """Versioned local peak season, weekdays, wall-hour window and explicit excluded dates."""

    version: Code
    months: tuple[Annotated[int, Field(ge=1, le=12)], ...]
    weekdays: tuple[Annotated[int, Field(ge=0, le=6)], ...]
    start_time: Annotated[str, Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    end_time: Annotated[str, Field(pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    excluded_dates: tuple[date, ...]

    @model_validator(mode='after')
    def distinct(self):
        """Require unique seasons/days and a nonempty same-day window; unsupported overnight rules stay explicit."""
        if len(set(self.months)) != len(self.months) or len(set(self.weekdays)) != len(self.weekdays) or self.start_time >= self.end_time:
            raise ValueError('invalid_peak_calendar')
        return self


class MonthPolicy(DomainModel):
    """Closed monthly rule identifier or explicit document evidence; unknown rules yield limitations, never eval."""

    version: Code
    mode: Literal['explicit_evidence', 'documented_rule']
    source_refs: tuple[Reference, ...]
    rule_id: Code | None


class Charge(DomainModel):
    """One documented charge: explicit unit, price, applicability, strategy and tax dependencies."""

    code: Code
    kind: Kind
    quantity_unit: Literal['kWh', 'kW', 'cycle', 'CLP']
    unit_price: Quantity | None
    tax_basis: TaxBasis
    applicability: Code
    vigency_strategy: Code
    source_refs: tuple[Reference, ...]
    tax_codes: tuple[Code, ...]

    @model_validator(mode='after')
    def unique_tax_dependencies(self):
        """Reject repeated/self-referencing taxable bases rather than charging the same component twice."""
        if len(set(self.tax_codes)) != len(self.tax_codes) or self.code in self.tax_codes:
            raise ValueError('invalid_tax_dependencies')
        return self


class ProfileSegment(DomainModel):
    """One half-open tariff validity segment with full captured policies and uniquely coded charges."""

    valid_from: Instant
    valid_to: Instant | None
    source_refs: tuple[Reference, ...]
    peak_calendar: PeakCalendar
    historical_rule: Code
    billing_month_policy: MonthPolicy
    rounding_policy: RoundingPolicy
    charges: tuple[Charge, ...]

    @model_validator(mode='after')
    def ordered(self):
        """Reject empty/reversed validity or duplicate charge codes before publication."""
        if self.valid_to is not None and self.valid_from >= self.valid_to:
            raise ValueError('invalid_validity')
        if len({c.code for c in self.charges}) != len(self.charges):
            raise ValueError('duplicate_charge')
        return self


class ProfileInput(DomainModel):
    """A full append-only calendar revision; drafts do not replace the selected published revision."""

    supply_id: UUID
    expected_previous_version_id: UUID | None
    tariff: Literal['BT4.3']
    currency: Literal['CLP']
    publication_state: Literal['draft', 'published']
    timezone: Timezone
    source_refs: tuple[Reference, ...]
    territory_conditions: Reference
    required_kinds: tuple[Kind, ...]
    segments: tuple[ProfileSegment, ...]

    @model_validator(mode='after')
    def no_overlap(self):
        """Reject internal overlap; historical revisions may legitimately cover identical dates."""
        if not self.segments:
            raise ValueError('calendar_required')
        segments = sorted(self.segments, key=lambda s: s.valid_from)
        for left, right in zip(segments, segments[1:]):
            if left.valid_to is None or left.valid_to > right.valid_from:
                raise ValueError('overlapping_segments')
        if len(set(self.required_kinds)) != len(self.required_kinds):
            raise ValueError('duplicate_required_kind')
        return self


class SupplyInput(DomainModel):
    """Administrative supply association; the server verifies the physicalCAT-01 source at calculation time."""

    general_board_ref: Reference
    category_id: Literal['CAT-01']
    general_source_id: UUID
    distributor: Reference | None
    location: Reference | None
    connection_conditions: Reference | None
    document_refs: tuple[Reference, ...]
    measurement_point_differences: tuple[Reference, ...]


class MonthEvidence(Period):
    """Administrator-declared documentary metadata; consistency is validated without OCR or file uploads."""

    @model_validator(mode='before')
    @classmethod
    def wire_boundaries(cls, value):
        """Normalize documentary start_at/end_at fields without accepting duplicated boundary declarations."""
        if isinstance(value, dict):
            value = dict(value)
            for external, internal in (('start_at', 'start'), ('end_at', 'end')):
                if external in value:
                    if internal in value:
                        raise ValueError('duplicate_boundary')
                    value[internal] = value.pop(external)
        return value

    document_reference: Reference
    supply_id: UUID
    billing_month_ref: Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class CalculateRequest(Period):
    """Explicit calculation command; only an administrative operation creates a new immutable revision."""

    supply_id: UUID
    timezone: Timezone
    boundary_criterion: Reference
    boundary_limited: bool = False
    declared_start: Reference | None = None
    declared_end: Reference | None = None
    reason: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    billing_month_ref: Annotated[str, Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')] | None = None
    billing_month_source_ref: MonthEvidence | None = None

    @model_validator(mode='before')
    @classmethod
    def wire_dates(cls, value):
        """Accept documented start_at/end_at wire names, retaining internal Period's UTC validation."""
        if isinstance(value, dict):
            value = dict(value)
            for external, internal in (('start_at', 'start'), ('end_at', 'end')):
                if external in value:
                    if internal in value:
                        raise ValueError('duplicate_boundary')
                    value[internal] = value.pop(external)
        return value

    @model_validator(mode='after')
    def evidence_pair(self):
        """Require both well-formed explicit-month fields; contradiction remains an expected calculation limitation."""
        if (self.billing_month_ref is None) != (self.billing_month_source_ref is None):
            raise ValueError('month_evidence_pair_required')
        return self


class PhysicalBlock(Period):
    """Copied physical evidence survives source withdrawal, including original unit, IDs and configuration revisions."""

    record_id: UUID
    revision: Revision
    category_revision: Revision
    configuration_revision: Revision
    source_id: UUID
    energy_kwh: Quantity
    original_value: str
    original_unit: Literal['Wh', 'kWh', 'MWh']


class InputEvidence(DomainModel):
    """Versioned complete calculation inputs; hash and engine version are stored outside this immutable value."""

    schema_version: Literal[1] = 1
    request: CalculateRequest
    cutoff_at: Instant
    supply_id: UUID
    supply_revision: Revision
    supply: SupplyInput
    profile_id: UUID | None
    profile_revision: Revision | None
    profile: ProfileInput | None
    measurements: tuple[PhysicalBlock, ...]
    general_reason: Code | None
    history: tuple[PhysicalBlock, ...]
    history_reason: Code | None
    billing_month_ref: str | None
    billing_month_source_ref: MonthEvidence | None
    billing_month_policy_version: str | None


class AppliedPrice(DomainModel):
    """Per-segment price evidence; multiple energy prices never collapse into an invented common tariff."""

    segment_start: Instant
    price: Quantity | None


class ComponentDetail(DomainModel):
    """Exact typed charge projection, preserving nullable limitations and reconciliation with displayed totals."""

    code: Code
    kind: Kind
    basis_value: Money | None
    unit: Literal['kWh', 'kW', 'cycle', 'CLP']
    rule_id: Code
    unit_price: Quantity | None
    tax_basis: TaxBasis
    unrounded_amount: Money | None
    presented_amount: Money | None
    state: Literal['available', 'limited']
    limitation_codes: tuple[Code, ...]
    rounding_policy: RoundingPolicy
    profile_version_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    applied_prices: tuple[AppliedPrice, ...]


class MonthlyMaximum(DomainModel):
    """Distinct-month demand evidence: incomplete coverage never has a numeric surrogate maximum."""

    month: str
    maximum_kw: Quantity | None
    coverage: Literal['complete', 'incomplete']
    kind: Literal['supplied', 'peak']


class CalculationDetail(DomainModel):
    """Persisted004 resource; GET uses captured values and never evaluates today's tariff."""

    id: UUID
    revision: Revision
    created_at: Instant
    retain_until: Instant
    cycle_id: UUID
    snapshot_id: UUID
    previous_id: UUID | None
    cutoff_at: Instant
    engine_version: Code
    input_hash: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
    snapshot: InputEvidence
    execution_state: Literal['completado', 'fallido']
    temporal_state: Literal['en_curso', 'cerrado']
    sufficiency: Literal['completo', 'parcial', 'no_calculable']
    available_subtotal: Money
    complete_total: Money | None
    net_total: Money | None
    tax_total: Money | None
    currency: Literal['CLP']
    reason_codes: tuple[Code, ...]
    components: tuple[ComponentDetail, ...]
    monthly_maxima: tuple[MonthlyMaximum, ...]


class SupplyDetail(SupplyInput):
    """Administrative current supply plus immutable identity/revision metadata and no account/session fields."""

    id: UUID
    revision: Revision
    created_at: Instant
    retain_until: Instant


class BillLine(DomainModel):
    """Manual document line: signed amounts, explicit comparable-cycle relation and nullable unknown quantities."""

    code: Code
    description: Reference
    quantity: Quantity | None
    unit: Literal['kWh', 'kW', 'cycle', 'CLP']
    amount: Money
    tax_basis: TaxBasis
    tax_amount: Money | None
    cycle_relation: Literal['current_cycle', 'outside_cycle', 'unknown']
    document_reference: Reference


class BillInput(Period):
    """Versioned manual invoice evidence; measured quantities remain separate from billed demand bases."""

    supply_id: UUID
    external_identifier: Reference
    issued_at: Instant
    timezone: Timezone
    declared_start: Reference | None
    declared_end: Reference | None
    boundary_criterion: Reference
    boundary_limited: bool
    document_reference: Reference
    currency: Literal['CLP']
    energy_read: Quantity | None
    demand_read: Quantity | None
    demand_billed: Quantity | None
    declared_tax: Money | None
    total_payable: Money
    lines: tuple[BillLine, ...]

    @model_validator(mode='before')
    @classmethod
    def wire_dates(cls, value):
        """Accept the documented effective start_at/end_at boundaries without silently inferring issue-month cycles."""
        return CalculateRequest.wire_dates(value)

    @model_validator(mode='after')
    def unique_lines(self):
        """Reject ambiguous duplicate concept codes; unknown quantities remain explicitly null."""
        if len({line.code for line in self.lines}) != len(self.lines):
            raise ValueError('duplicate_bill_code')
        return self


class ComparisonRequest(DomainModel):
    """Explicit immutable pair references; saving or reading a bill never creates a comparison implicitly."""

    calculation_id: UUID
    bill_revision_id: UUID


class BillDetail(BillInput):
    """A stable logical document ID plus an explicit immutable bill-revision identity."""

    id: UUID
    bill_revision_id: UUID
    revision: Revision
    previous_id: UUID | None
    cycle_id: UUID
    created_at: Instant
    retain_until: Instant


class AlignedPair(DomainModel):
    """Both quantities/amounts and original billed sign under an explicit shared unit/tax basis."""

    code: Code
    unit: Literal['kWh', 'kW', 'cycle', 'CLP']
    tax_basis: TaxBasis
    calculated_quantity: Money | None
    billed_quantity: Money | None
    calculated_amount: Money
    billed_amount: Money
    original_billed_amount: Money
    delta_amount: Money


class ExcludedLine(DomainModel):
    """Signed original amount excluded for a functional alignment reason, not discarded or silently zeroed."""

    code: Code
    amount: Money
    reason_code: Code


class ComparisonDetail(DomainModel):
    """Explicit persisted comparison for a specific immutable pair; no read recalculates or selects an older pair."""

    id: UUID
    revision: Revision
    created_at: Instant
    retain_until: Instant
    calculation_id: UUID
    bill_revision_id: UUID
    cutoff_at: Instant
    currency: Literal['CLP']
    comparable_calculated: Money | None
    comparable_billed: Money | None
    delta_amount: Money | None
    delta_percent: Money | None
    total_payable: Money
    pairs: tuple[AlignedPair, ...]
    excluded_lines: tuple[ExcludedLine, ...]
    unmatched_calculated_codes: tuple[Code, ...]
    limitation_codes: tuple[Code, ...]
    percentage_rule: Code


class ProfileDetail(ProfileInput):
    """An immutable full calendar with server-assigned chain metadata, distinct from the selected publication."""

    id: UUID
    revision: Revision
    previous_version_id: UUID | None
    created_at: Instant
    retain_until: Instant


class ComparisonReference(DomainModel):
    """Historical comparison identity; never a substitute for the currently selected exact pair."""

    id: UUID
    calculation_id: UUID
    bill_revision_id: UUID
    revision: Revision


class CycleDetail(DomainModel):
    """Coherent current-at-cutoff selection, with explicit pending status and nullable differences."""

    id: UUID
    supply_id: UUID
    start_at: Instant
    end_at: Instant
    timezone: Timezone
    calculation: CalculationDetail | None
    bill: BillDetail | None
    comparison: ComparisonDetail | None
    comparison_status: Literal['available', 'missing_for_selected_revisions', 'no_calculation', 'no_bill']
    delta_amount: Money | None
    delta_percent: Money | None
    historical_comparisons: tuple[ComparisonReference, ...] = ()


class AvailableTotal(DomainModel):
    """Available values grouped by compatible currency/concept/tax basis; never a complete BT4.3 aggregate claim."""

    currency: Literal['CLP']
    code: Code
    tax_basis: TaxBasis
    amount: Money


class ComparisonTotal(DomainModel):
    """A comparable aggregate uses precisely the same cycle pairs on both sides and retains their basis."""

    currency: Literal['CLP']
    code: Code
    tax_basis: TaxBasis
    calculated: Money
    billed: Money
    delta_amount: Money
    delta_percent: Money | None
    cycle_count: Annotated[int, Field(ge=1)]


class CostsSnapshot(DomainModel):
    """Immutable005 financial producer DTO; closed effective cycles are selected once, without proration or writes."""

    schema_version: Literal[1] = 1
    building_id: UUID
    supply_id: UUID | None
    start: Instant
    end: Instant
    timezone: Timezone
    cutoff_at: Instant
    cycles: tuple[CycleDetail, ...]
    available_totals: tuple[AvailableTotal, ...]
    comparison_totals: tuple[ComparisonTotal, ...]
    complete_cycle_count: Annotated[int, Field(ge=0)]
    partial_cycle_count: Annotated[int, Field(ge=0)]
    uncalculable_cycle_count: Annotated[int, Field(ge=0)]
    failed_cycle_count: Annotated[int, Field(ge=0)]
    reason_codes: tuple[Code, ...]


class CyclePage(DomainModel):
    """Bounded immutable cycle page with a stable signed continuation and original read cutoff."""

    items: tuple[CycleDetail, ...]
    next_cursor: str | None
    cutoff_at: Instant


class BillPage(DomainModel):
    """Bounded immutable invoice-revision page, including explicit historical revision IDs."""

    items: tuple[BillDetail, ...]
    next_cursor: str | None
    cutoff_at: Instant


class ProfilePage(DomainModel):
    """Administrative calendar page with saved/published selection metadata repeated at the same cutoff."""

    items: tuple[ProfileDetail, ...]
    next_cursor: str | None
    cutoff_at: Instant
    latest_version_id: UUID | None
    selected_published_version_id: UUID | None
    latest_version: ProfileDetail | None
    selected_published_version: ProfileDetail | None
