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
                     process: str, records: Sequence[Mapping[str, Any]], correlation_ref: str):
        """Return002 ReceptionOutcome;002 owns per-category UoWs and recovers immutable attempt results.

        Match002's attempt-aware contract: an identical attempt resumes only missing
        durable results, while a new re-send has a fresh UUID. No provider is installed here.
        """
        ...

    async def read_attempt(self, attempt_id: UUID, building_id: UUID, process: str):
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
