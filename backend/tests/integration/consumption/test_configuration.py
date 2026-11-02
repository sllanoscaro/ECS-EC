"""Real PostgreSQL installation transactions; storage bounds are explicitly isolated doubles."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from ecs_ec.audit.models import AuditRecord, FunctionalEvent
from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.catalog_storage import BuildingRow, CategorySourceRow, InstallationRow, MeasurementSourceRow, read_revisions
from ecs_ec.consumption.configuration import ConfigurationError, ConfigurationService
from ecs_ec.consumption.models import BuildingContext, ReconfigurationBounds
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.unit.consumption.test_catalog import installation

pytestmark = pytest.mark.integration
BUILDING = UUID(int=99)


class BoundsStore:
    """Only the bounds port is doubled; configuration, locks, evidence and DB remain real."""

    def __init__(self, *, history=False, ends=None, fail=False, incomplete=False):
        """Set explicit preserved history, failure or invalid-response behavior."""
        self.history, self.ends, self.fail, self.incomplete = history, ends or {}, fail, incomplete
        self.called = False

    async def read_reconfiguration_bounds(self, building_id, category_ids, unit_of_work):
        """Verify current transaction isolation and return synthetic002 state without committing."""
        assert building_id == BUILDING
        assert await unit_of_work.session.scalar(text("SHOW transaction_isolation")) == "read committed"
        self.called = True
        if self.fail: raise RuntimeError("synthetic-provider-failure")
        return ReconfigurationBounds(has_accepted_history=self.history,
            latest_interval_end_by_category={} if self.incomplete else {c: self.ends.get(c) for c in category_ids})


@pytest.fixture(autouse=True)
async def clean_installation(database):
    """Isolate real consumption history/configuration on the dedicated test DB; CASCADE is fixture cleanup only."""
    async with database.engine.begin() as conn:
        await conn.execute(text("TRUNCATE consumption_building CASCADE"))
        await conn.execute(delete(FunctionalEvent).where(FunctionalEvent.source_module == "consumption"))
        await conn.execute(delete(AuditRecord).where(AuditRecord.entity_type == "consumption_configuration"))


async def initial(database, clock, config=None):
    """Create singleton context and first historical revision via the production bootstrap service."""
    async with UnitOfWork(database.sessions) as uow:
        result = await bootstrap(uow, building=BuildingContext(id=BUILDING, name="Synthetic building",
            timezone="America/Santiago", created_at=clock.now()), configuration=config or installation(),
            clock=clock, actor_ref="process:consumption_test")
        await uow.commit()
        return result


async def apply(database, clock, request, store=None, *, commit=True):
    """Run one isolated administration transaction and optionally leave it for automatic rollback."""
    async with UnitOfWork(database.sessions) as uow:
        result = await ConfigurationService(clock, store).apply(uow, building_id=BUILDING,
            request=request, actor_ref="process:consumption_test")
        if commit: await uow.commit()
        return result


async def test_bootstrap_history_noop_and_evidence(database, clock):
    """First config predates002; a no-op creates neither revision nor event and ignores absent bounds."""
    first = await initial(database, clock)
    assert first.revision == 1 and first.effective_from == datetime(2025, 1, 1, tzinfo=UTC)
    same = installation().model_copy(update={"expected_revision": 1, "effective_from": None})
    result = await apply(database, clock, same)
    assert result.id == first.id
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(InstallationRow)) == 1
        assert await uow.session.scalar(select(func.count()).select_from(CategorySourceRow)) == 7
        assert await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(AuditRecord.entity_id == first.id)) == 1
        assert set((await uow.session.scalars(select(FunctionalEvent.event_type).where(FunctionalEvent.source_entity_id == first.id))).all()) == {"source.changed", "administration.changed"}


@pytest.mark.parametrize("store", [None, BoundsStore(fail=True), BoundsStore(incomplete=True)])
async def test_unavailable_bounds_fails_closed(database, clock, store):
    """Missing/failing/incomplete history cannot be interpreted as empty or persist a partial source."""
    await initial(database, clock)
    changed = installation(**{"3": UUID(int=30)}).model_copy(update={"expected_revision": 1, "effective_from": None})
    with pytest.raises(ConfigurationError, match="reconfiguration_bounds_unavailable"):
        await apply(database, clock, changed, store)
    async with UnitOfWork(database.sessions) as uow:
        assert len(await read_revisions(uow, BUILDING)) == 1
        assert await uow.session.get(MeasurementSourceRow, UUID(int=30)) is None


async def test_bounds_and_zone_survive_retired_detail(database, clock):
    """Preserved calculated/physical maxima protect changes even with no retained measurement rows."""
    await initial(database, clock)
    store = BoundsStore(history=True, ends={"CAT-01": clock.now() + timedelta(seconds=1)})
    changed = installation(**{"3": UUID(int=30)}).model_copy(update={"expected_revision": 1, "effective_from": None})
    with pytest.raises(ConfigurationError, match="accepted_interval_conflict"): await apply(database, clock, changed, store)
    timezone = installation(timezone="UTC").model_copy(update={"expected_revision": 1, "effective_from": None})
    with pytest.raises(ConfigurationError, match="timezone_has_history"): await apply(database, clock, timezone, store)
    store.ends = {"CAT-01": clock.now()}
    result = await apply(database, clock, changed, store)
    assert result.entry("CAT-01").category_revision == 2
    assert result.entry("CAT-05").category_revision == 1


async def test_effective_time_and_immutable_snapshots(database, clock):
    """Changed configuration uses application time; previous labels, sources and timestamps survive."""
    first = await initial(database, clock)
    request = installation(label="Changed label").model_copy(update={"expected_revision": 1})
    with pytest.raises(ConfigurationError, match="effective_time_mismatch"): await apply(database, clock, request, BoundsStore())
    second = await apply(database, clock, request.model_copy(update={"effective_from": None}), BoundsStore())
    assert second.effective_from == clock.now()
    assert [c.category_revision for c in second.categories] == [1] * 7
    async with UnitOfWork(database.sessions) as uow:
        revisions = await read_revisions(uow, BUILDING)
        assert revisions[0] == first
        assert revisions[0].entry("CAT-03").source_label == "Synthetic meter"
        assert revisions[1].entry("CAT-03").source_label == "Changed label"


async def test_concurrent_revision_and_transaction_rollback(database, clock):
    """Same expected revision has one winner; rolling back removes config and shared audit/events."""
    await initial(database, clock)
    request = installation(**{"3": UUID(int=30)}).model_copy(update={"expected_revision": 1, "effective_from": None})
    results = await asyncio.gather(apply(database, clock, request, BoundsStore()),
        apply(database, clock, request, BoundsStore()), return_exceptions=True)
    assert sum(not isinstance(r, Exception) for r in results) == 1
    assert [r.code for r in results if isinstance(r, ConfigurationError)] == ["revision_conflict"]
    clock.advance(1)
    changed = installation(**{"5": UUID(int=50)}).model_copy(update={"expected_revision": 2, "effective_from": None})
    rolled = await apply(database, clock, changed, BoundsStore(), commit=False)
    async with UnitOfWork(database.sessions) as uow:
        assert len(await read_revisions(uow, BUILDING)) == 2
        assert await uow.session.get(InstallationRow, rolled.id) is None
        assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(FunctionalEvent.source_entity_id == rolled.id)) == 0


async def test_mid_evidence_failure_rolls_back_everything(database, clock, monkeypatch):
    """An event failure after audit flush cannot leave a source/revision/audit durable."""
    from ecs_ec.audit.events import EventWriter
    original = EventWriter.append
    async def fail(self, uow, event):
        """Fail the second event after the first event and audit have flushed, before caller commit."""
        if event.event_type == "administration.changed": raise RuntimeError("synthetic-event-failure")
        return await original(self, uow, event)
    monkeypatch.setattr(EventWriter, "append", fail)
    with pytest.raises(RuntimeError, match="synthetic-event-failure"): await initial(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(InstallationRow)) == 0
        assert await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(AuditRecord.entity_type == "consumption_configuration")) == 0


async def test_history_foreign_keys_restrict_destructive_removal(database, clock):
    """Sources/revisions/context referenced by historical snapshots cannot disappear through cascades."""
    first = await initial(database, clock)
    for table, key in ((MeasurementSourceRow, UUID(int=3)), (InstallationRow, first.id), (BuildingRow, BUILDING)):
        with pytest.raises(IntegrityError):
            async with UnitOfWork(database.sessions) as uow:
                await uow.session.execute(delete(table).where(table.id == key))
                await uow.commit()


async def test_zone_without_history_real_null_bounds_and_stale_noop(database, clock):
    """A successful empty-history response permits timezone change; stale expected revisions still conflict."""
    await initial(database, clock)
    store = BoundsStore()
    changed = installation(timezone="UTC").model_copy(update={"expected_revision": 1, "effective_from": None})
    result = await apply(database, clock, changed, store)
    assert result.timezone == "UTC" and store.called
    assert all(c.category_revision == 1 for c in result.categories)
    with pytest.raises(ConfigurationError, match="revision_conflict"): await apply(database, clock, changed, store)


async def test_write_coordinator_refuses_historical_snapshot(database, clock):
    """Reconfiguration must read bounds after locks in READ COMMITTED, never in a stale repeatable snapshot."""
    await initial(database, clock)
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        with pytest.raises(ValueError, match="configuration_requires_read_committed"):
            await ConfigurationService(clock, BoundsStore()).apply(uow, building_id=BUILDING,
                request=installation().model_copy(update={"expected_revision": 1}), actor_ref="process:test")
