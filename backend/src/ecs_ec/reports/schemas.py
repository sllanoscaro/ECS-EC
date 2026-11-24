"""Strict005 selections and immutable producer-copy schema; decimals retain their original textual precision."""

from datetime import date as CalendarDate, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ecs_ec.consumption.models import ConfigurationSegment
from ecs_ec.consumption.ports import AggregateBlock
from ecs_ec.costs.schemas import CostsSnapshot


class Strict(BaseModel):
    """Forbid unknown fields and freeze confirmed report projections."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Selection(Strict):
    """Exactly one calendar selection; a date, year/month or year, never client timezone/building."""

    scale: Literal["diario", "mensual", "anual"]
    date: CalendarDate | None = None
    year: int | None = Field(default=None, ge=1, le=9998, strict=True)
    month: int | None = Field(default=None, ge=1, le=12, strict=True)

    @model_validator(mode="after")
    def applicable(self):
        """Reject both missing and explicitly supplied nonapplicable fields, including nulls."""
        expected = {
            "diario": {"scale", "date"},
            "mensual": {"scale", "year", "month"},
            "anual": {"scale", "year"},
        }[self.scale]
        if self.model_fields_set != expected or any(
            getattr(self, k) is None for k in expected
        ):
            raise ValueError("invalid_selection")
        return self


class EnergyRow(Strict):
    """A seven-category summary derived only from the producer's retained aggregate blocks."""

    category_id: str = Field(pattern=r"^CAT-0[1-7]$")
    name: str
    energy_kwh: str | None
    unit: Literal["kWh"] = "kWh"
    coverage_percent: str
    state: str
    source_mode: Literal["measured", "calculated", "mixed", "unavailable"]
    provenance_segments: tuple[ConfigurationSegment, ...]
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def numeric(self):
        """Nullable energy is explicit; finite textual values and bounded coverage cannot invent zero."""
        if self.energy_kwh is not None and (
            not Decimal(self.energy_kwh).is_finite() or Decimal(self.energy_kwh) < 0
        ):
            raise ValueError("invalid_energy")
        if (
            not Decimal(self.coverage_percent).is_finite()
            or not 0 <= Decimal(self.coverage_percent) <= 100
        ):
            raise ValueError("invalid_coverage")
        return self


class Snapshot(Strict):
    """Confirmed005 projection, retaining exact002 provenance and typed004 pairs at a single cutoff."""

    schema_version: Literal[1] = 1
    building_id: UUID
    building_name: str
    scale: Literal["diario", "mensual", "anual"]
    start: datetime
    end: datetime
    timezone: str
    cutoff_at: datetime
    provisional: bool
    energy_rows: tuple[EnergyRow, ...]
    chart_blocks: tuple[AggregateBlock, ...]
    financial_snapshot: CostsSnapshot
    source_revisions: dict[str, str]
    source_refs: tuple[str, ...]
    quality_notes: tuple[str, ...]
    provenance: tuple[str, ...]

    @model_validator(mode="after")
    def consistent(self):
        """Require seven unique canonical categories and one consistent producer cutoff/window."""
        if (
            tuple(r.category_id for r in self.energy_rows)
            != tuple(f"CAT-{i:02}" for i in range(1, 8))
            or self.start >= self.end
        ):
            raise ValueError("invalid_snapshot")
        if self.financial_snapshot.cutoff_at != self.cutoff_at:
            raise ValueError("inconsistent_cutoff")
        return self
