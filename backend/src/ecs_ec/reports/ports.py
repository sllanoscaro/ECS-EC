"""005 consumer contracts matching the installed001/002/004/006/009 providers.

Callers resolve the current006 session before capture and share one REPEATABLE READ
unit of work across both data ports. No port creates comparisons or measurements.
The007 telemetry provider is still absent and is not replaced with a no-op here.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.costs.schemas import CostsSnapshot
from ecs_ec.identity.schemas import Principal


class IdentityPort(Protocol):
    """006 access policy; the caller must first resolve a current durable session."""

    def require_report_access(self, principal: Principal, building_id: UUID) -> None:
        """Reject a foreign building or a principal without current reports.read permission."""
        ...

    def authorize(self, principal: Principal, action: str, building_id: UUID) -> None:
        """Apply the installed006 action policy, including reports.generate on admission."""
        ...


class ConsumptionPort(Protocol):
    """002 report reader: seven category/detail/grouped outputs, not final PDF rows."""

    async def read_report_snapshot(self, building_id: UUID, start: datetime, end: datetime,
                                   scale: str, cutoff_at: datetime, principal: Principal,
                                   *, unit_of_work: UnitOfWork) -> dict:
        """Copy producer evidence using hour/day/month/year granularity in the caller's UoW.

        Do not pass diario/mensual/anual: those are005 selections, not002 granularities.
        The projection adapter must preserve valid retained totals separately from
        chart detail; this port does not supply preassembled energy_rows.
        """
        ...


class CostsPort(Protocol):
    """004 financial provider; consumes the same snapshot transaction as energy."""

    async def read_snapshot(self, building_id: UUID, start: datetime, end: datetime,
                            cutoff_at: datetime, principal: Principal,
                            *, unit_of_work: UnitOfWork) -> CostsSnapshot:
        """Return effective closed cycles and exact revision pairs without recomputing BT4.3."""
        ...
