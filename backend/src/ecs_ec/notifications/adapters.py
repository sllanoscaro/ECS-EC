"""008 adapters preserve installed001/002/006/009 results; no arithmetic, accounts or event producers live here."""


class ConsumptionAdapter:
    """Translate008 calendar names and preserve native owner evidence and availability."""

    def __init__(self, consumption):
        """Receive the actual001 facade with002 storage, not an independent notification dataset."""
        self.consumption = consumption

    async def source_status(self, category_id, **options):
        """Forward the fixed category/cutoff to its owner; leave absent arrival timestamps null."""
        return await self.consumption.source_status(category_id, **options)

    async def latest_admissible_window(self, **selection):
        """Map calendar vocabulary only; an interval retains the measurement owner's exact resolution."""
        selection = dict(selection)
        selection["resolution"] = {
            "hora": "hour",
            "dia": "day",
            "mes": "month",
            "anio": "year",
        }.get(selection["resolution"], selection["resolution"])
        return await self.consumption.latest_admissible_window(**selection)

    async def read_functional_summary(self, *args, **options):
        """Forward the actual owner's integrity/known-gap proof without inventing coverage from logs."""
        return await self.consumption.read_functional_summary(*args, **options)


class IdentityAdapter:
    """Resolve one current registered006 account, never a free email or a technical identity."""

    def __init__(self, identity):
        """Reuse the installed006 service; no cache of durable permission decisions."""
        self.identity = identity

    async def resolve_recipient(self, account_id, required_permissions):
        """Return006's current projection, preserving account identity across email revisions."""
        return await self.identity.resolve_recipient(account_id, required_permissions)
