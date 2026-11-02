"""Strict standalone scenario schema: explicit synthetic topology and exact energy."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pas600_simulator.calendar import interval_count, quantum_bounds, representable


class StrictModel(BaseModel):
    """Reject unknown fields at every nesting level and disallow nonfinite numbers."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    @model_validator(mode='before')
    @classmethod
    def reject_float(cls, value):
        """Require exact decimal strings/integers rather than binary floating input."""
        if isinstance(value, dict) and any(isinstance(v, float) for v in value.values()):
            raise ValueError('decimal inputs must use strings or integers')
        return value


class Provenance(StrictModel):
    """Descriptor provenance; noninitial capabilities require evidence and checksum."""
    kind: Literal['synthetic', 'documented'] = 'synthetic'
    revision: str = 'DOCA0172EN-19'
    evidence: str | None = None
    sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class SimulatedPublisher(StrictModel):
    """One PAS600 concentrates channels; its identity is distinct from every meter."""
    name: str = 'PAS600 synthetic'
    publisher_serial: str = 'SYNTHETIC-PAS600'
    publisher_remote_id: str = 'synthetic-pas600'
    ip: str = '192.0.2.1'
    mac: str = '02:00:00:00:00:01'


class SimulatedMeterChannel(StrictModel):
    """Native iEM3150 identity and one energy channel, without inferred category."""
    device_local_id: str = Field(min_length=1)
    reduced_id: str = Field(min_length=1)
    device_name: str = Field(min_length=1)
    device_type_id: str = 'synthetic-iem3150'
    device_type_name: Literal['iEM3150'] = 'iEM3150'
    csv_topic_id: str
    csv_measurement_name: str = 'Active Energy'
    json_value_item_id: str
    unit: Literal['Wh', 'kWh', 'MWh'] = 'kWh'
    semantics: Literal['cumulative', 'interval'] = 'cumulative'
    timestamp_role: Literal['reading_instant', 'interval_start', 'interval_end'] = 'reading_instant'
    sampling_minutes: int = Field(default=15, gt=0, strict=True)
    initial_counter: Decimal = Decimal('100')
    quantum: Decimal = Decimal('0.001')
    provenance: Provenance = Field(default_factory=Provenance)

    @model_validator(mode='after')
    def compatible(self):
        """Require representable initial counter and evidence for noninitial features."""
        if self.initial_counter < 0 or not representable(self.initial_counter, self.quantum):
            raise ValueError('initial_counter must be nonnegative and representable')
        if (self.semantics == 'cumulative') != (self.timestamp_role == 'reading_instant'):
            raise ValueError('timestamp_role incompatible with semantics')
        if (self.sampling_minutes != 15 or self.semantics == 'interval') and not (self.provenance.evidence and self.provenance.sha256):
            raise ValueError('noninitial capability requires evidence and checksum')
        return self


class EnergyRange(StrictModel):
    """Expected interval energy, with its own explicit unit and duration."""
    min: Decimal = Decimal('0')
    max: Decimal = Decimal('10')
    unit: Literal['Wh', 'kWh', 'MWh'] = 'kWh'
    duration_minutes: int = Field(default=15, gt=0, strict=True)


class AnomalyRates(StrictModel):
    """Disjoint per-sample percentages; the denominator excludes initial references."""
    missing: Decimal = Field(default=Decimal(0), ge=0, le=100)
    format: Decimal = Field(default=Decimal(0), ge=0, le=100)
    out_of_range: Decimal = Field(default=Decimal(0), ge=0, le=100)

    positions: dict[Literal['missing', 'format', 'out_of_range'], list[int]] = Field(default_factory=dict)
    format_mode: Literal['type', 'date'] = 'type'
    out_of_range_direction: Literal['above', 'below'] = 'above'

    @model_validator(mode='after')
    def bounded(self):
        """Reject percentages whose disjoint assignment would exceed all samples."""
        if self.missing + self.format + self.out_of_range > 100:
            raise ValueError('anomaly rates sum exceeds 100')
        return self


class CategoryState(StrictModel):
    """A category without a meter carries no channel, range or anomaly rates."""
    category_id: str = Field(pattern=r'^CAT-0[1-7]$')
    has_meter: bool = Field(strict=True)
    meter: SimulatedMeterChannel | None = None
    expected_range: EnergyRange | None = None
    rates: AnomalyRates | None = None

    @model_validator(mode='after')
    def presence(self):
        """Enforce a complete measured state or a truly absent state."""
        fields = (self.meter, self.expected_range, self.rates)
        if not self.has_meter:
            if any(v is not None for v in fields):
                raise ValueError('absent category cannot have channel/range/rates')
        else:
            if self.meter is None or self.expected_range is None:
                raise ValueError('measured category requires meter and range')
            if self.rates is None:
                self.rates = AnomalyRates()
            r, m = self.expected_range, self.meter
            if r.unit != m.unit or r.duration_minutes != m.sampling_minutes:
                raise ValueError('range unit/duration must match channel; no implicit scaling')
            quantum_bounds(r.min, r.max, m.quantum)
        return self


def default_categories() -> list[CategoryState]:
    """Construct seven distinct synthetic meters; total remains independently measured."""
    return [CategoryState(category_id=f'CAT-0{i}', has_meter=True,
        meter=SimulatedMeterChannel(device_local_id=str(i), reduced_id=f'{i}_mb',
            device_name=f'iEM3150 CAT0{i}', csv_topic_id=f'SYNTHETIC.{i}.energy',
            json_value_item_id=f'synthetic/{i}/energy'), expected_range=EnergyRange()) for i in range(1, 8)]


class StructuralCorruption(StrictModel):
    """One exact native filename and supported final byte alteration."""
    filename: str = Field(min_length=1)
    operation: Literal['truncate', 'remove_header']


class SimulationScenario(StrictModel):
    """Versioned scenario with siete estados de categoría and uno por escenario publisher.

    Identidad local/ReducedID únicos por PAS600, categoría medida única.
    Sin origen ficticio para CAT-01 calculada: absent means no generated channel.
    """
    schema_version: Literal[1] = 1
    algorithm_version: Literal['sha256-v1'] = 'sha256-v1'
    profile_id: Literal['pas600-doca0172en19-energy-v1'] = 'pas600-doca0172en19-energy-v1'
    seed: str = 'ecs-ec-example'
    publisher: SimulatedPublisher = Field(default_factory=SimulatedPublisher)
    timezone: str = 'Etc/UTC'
    start: datetime = datetime.fromisoformat('2026-01-01T00:00:00Z')
    end: datetime = datetime.fromisoformat('2026-01-02T00:00:00Z')
    publication_time: datetime = datetime.fromisoformat('2026-01-02T00:00:00Z')
    sampling_minutes: int = Field(default=15, gt=0, strict=True)
    samples_per_publication: int = Field(default=96, ge=1, strict=True)
    format: Literal['csv', 'json'] = 'csv'
    categories: list[CategoryState] = Field(default_factory=default_categories)
    structural_corruptions: list[StructuralCorruption] = Field(default_factory=list)

    @model_validator(mode='after')
    def consistent(self):
        """Validate complete calendar/topology before allowing any filesystem effects."""
        interval_count(self.start, self.end, self.timezone, self.sampling_minutes)
        if self.start.microsecond or self.end.microsecond or self.publication_time.microsecond % 1000:
            raise ValueError('reading timestamps require seconds; publication requires milliseconds')
        if self.publication_time.utcoffset() is None:
            raise ValueError('publication_time requires explicit offset')
        if {c.category_id for c in self.categories} != {f'CAT-0{i}' for i in range(1, 8)} or len(self.categories) != 7:
            raise ValueError('exactly seven unique category states required')
        meters = [c.meter for c in self.categories if c.has_meter]
        for field in ('device_local_id', 'reduced_id', 'json_value_item_id'):
            if len({getattr(m, field) for m in meters}) != len(meters):
                raise ValueError(f'duplicate {field}')
        if any(m.sampling_minutes != self.sampling_minutes for m in meters):
            raise ValueError('channel sampling must match scenario')
        return self
