"""008 read/write boundaries: consume identity/energy/audit providers in the monolith, never implement their domains."""

from typing import Protocol


class ConsumptionPort(Protocol):
    """Quality/provenance-preserving read source; absent values and windows remain explicit."""

    async def source_status(self, category_id, *, cutoff_at=None, unit_of_work=None):
        """Return installed source/new-data state without interpreting900seconds as an arrival SLA."""
        ...

    async def latest_admissible_window(self, **selection):
        """Return a real complete owner window at a fixed cutoff; no energy recomputation or estimates."""
        ...

    async def read_functional_summary(
        self, content_types, start, end, *, cutoff_at, permissions, unit_of_work
    ):
        """Read owner's functional event count and integrity at the caller's fixed capture."""
        ...


class IdentityPort(Protocol):
    """Current006 recipient resolution; durable delivery IDs do not cache a grant."""

    async def resolve_recipient(self, account_id, required_permissions):
        """Return current status/address/content eligibility or explicit absence."""
        ...


class AuditPort(Protocol):
    """009 functional append participates in the caller's transaction, never commits or sends mail."""

    async def append(self, unit_of_work, evidence):
        """Persist producer-approved functional evidence in the existing shared ledger."""
        ...
