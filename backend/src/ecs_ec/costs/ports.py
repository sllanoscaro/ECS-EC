"""004 resource ports: use the existing common UoW and event writer without importing consumers."""

from typing import Protocol

from ecs_ec.audit.events import EventInput, EventWriter
from ecs_ec.core.unit_of_work import UnitOfWork


class ConsumptionEvidence(Protocol):
    """Existing001/002 physical-supply evidence boundary, sharing the producer's read capture."""

    async def read_general_snapshot(self, building_id, start, end, cutoff_at, unit_of_work):
        """Return actual physicalCAT-01 rows/provenance and limitations; never synthesize the total."""
        ...

    async def read_demand_history(self, building_id, start, end, cutoff_at, unit_of_work):
        """Return original physical resolution; hourly readings do not prove quarter-hour peaks."""
        ...
