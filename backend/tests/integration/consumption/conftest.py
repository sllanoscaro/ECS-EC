"""Opt-in synthetic history fixtures; all incorporated data enters the real Reception port."""

import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text

from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.models import BuildingContext, instant
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.unit.consumption.test_catalog import installation


@pytest.fixture
def history_scenarios():
    """Load independent expected values and scenario bounds; never write measurements directly."""
    return json.loads((Path(__file__).parents[2] / "fixtures/consumption/history_scenarios.json").read_text())


@pytest.fixture
async def history_environment(database, clock, history_scenarios):
    """Provision seven physical sources via001; yield002 reception with trusted process and isolated DB.

    TRUNCATE is test isolation only, never an application withdrawal operation. Cleanup
    runs before/after so001's existing protected-configuration tests remain independent.
    """
    from ecs_ec.consumption.reception import Reception
    async def clean():
        """Clear consumption/audit test tables as one explicit test-only isolation operation."""
        async with database.engine.begin() as connection:
            await connection.execute(text("TRUNCATE consumption_building CASCADE"))
            await connection.execute(text("DELETE FROM functional_event WHERE source_module='consumption'"))
    await clean()
    async with UnitOfWork(database.sessions) as uow:
        await bootstrap(uow, building=BuildingContext(id=UUID(int=99), name="Synthetic building",
            timezone=history_scenarios["timezone"], created_at=clock.now()),
            configuration=installation(tuple(range(1, 8))).model_copy(update={"effective_from": instant(history_scenarios["history_start"])}),
            clock=clock, actor_ref="process:history_test")
        await uow.commit()
    try:
        yield Reception(database, clock, authorized_processes={"process:history_test": {UUID(int=99)}})
    finally:
        await clean()


class ReceptionEnvironment:
    """Real002 adapter for001's preserved acceptance tests; no admission/storage double."""

    def __init__(self, reception, database, clock):
        """Keep explicit synthetic resources and001/002 service providers for the test lifetime."""
        self.reception, self.database, self.clock = reception, database, clock

    async def publish(self, records):
        """Create an explicit new attempt and return position-stable committed result DTOs."""
        from uuid import uuid4
        outcome = await self.reception.accept(uuid4(), UUID(int=99), 'synthetic-publication',
            'process:history_test', records, 'synthetic:publication:1')
        return outcome.results

    async def rows(self, category):
        """Read retained originals through002's real provider using a coherent read-only capture."""
        from ecs_ec.consumption.store import MeasurementStore
        async with UnitOfWork(self.database.sessions) as uow:
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            result = await MeasurementStore().read_detail(UUID(int=99), category, instant('2024-01-01T00:00:00Z'),
                instant('2030-01-01T00:00:00Z'), self.clock.now(), uow)
            return result.rows

    async def update_state(self, category):
        """Read002's durable per-category state without extending any deadline."""
        from ecs_ec.consumption.store import MeasurementStore
        async with UnitOfWork(self.database.sessions) as uow:
            return await MeasurementStore().read_update_state(UUID(int=99), category, self.clock.now(), uow)

    async def events(self):
        """Return only consumption functional events in stable ordering for idempotence checks."""
        from sqlalchemy import select
        from ecs_ec.audit.models import FunctionalEvent
        async with UnitOfWork(self.database.sessions) as uow:
            rows = (await uow.session.scalars(select(FunctionalEvent).where(FunctionalEvent.source_module == 'consumption')
                .order_by(FunctionalEvent.recorded_at, FunctionalEvent.id))).all()
            from types import SimpleNamespace
            return tuple(SimpleNamespace(id=r.id, event_type=r.event_type, accepted_new_data=r.accepted_new_data) for r in rows)

    def advance(self, seconds):
        """Advance only the internally injected test clock, never the host clock."""
        self.clock.advance(seconds)

    async def configure(self, category, *, effective_from):
        """Switch the requested physical source via001 and002 bounds at an explicit synthetic instant."""
        from uuid import uuid4
        from ecs_ec.consumption.catalog_storage import read_revisions
        from ecs_ec.consumption.configuration import ConfigurationService
        from ecs_ec.consumption.models import ConfigurationInput, SourceInput
        from ecs_ec.consumption.store import MeasurementStore
        target = instant(effective_from)
        if target < self.clock.now(): raise ValueError('test_clock_must_advance')
        self.clock.advance((target - self.clock.now()).total_seconds())
        async with UnitOfWork(self.database.sessions) as uow:
            previous = (await read_revisions(uow, UUID(int=99)))[-1]
            entries = tuple(SourceInput(**(e.model_dump(exclude={'category_revision'}) |
                ({'source_id': uuid4()} if e.category_id == category else {}))) for e in previous.categories)
            await ConfigurationService(self.clock, MeasurementStore()).apply(uow, building_id=UUID(int=99),
                request=ConfigurationInput(expected_revision=previous.revision, effective_from=target,
                    timezone=previous.timezone, categories=entries), actor_ref='process:history_test')
            await uow.commit()


@pytest.fixture
async def consumption_reception_environment(history_environment, database, clock):
    """Supply001's previously missing real provider with onlyCAT-03/05 physical sources."""
    from ecs_ec.consumption.configuration import ConfigurationService
    from ecs_ec.consumption.store import MeasurementStore
    async with UnitOfWork(database.sessions) as uow:
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=UUID(int=99),
            request=installation().model_copy(update={'expected_revision': 1, 'effective_from': None}),
            actor_ref='process:history_test')
        await uow.commit()
    return ReceptionEnvironment(history_environment, database, clock)


@pytest.fixture
def thirteen_month_records(history_scenarios):
    """Thirteen monthly interval batches across all seven physical categories, with independent values1..7kWh."""
    rows = []
    for offset in range(13):
        year, month = 2024 + offset // 12, offset % 12 + 1
        for i, category in enumerate(history_scenarios['categories'], 1):
            rows.append(dict(building_id=UUID(int=99), category_id=category, source_id=UUID(int=i), value=str(i), unit='kWh',
                start=f'{year}-{month:02}-01T03:00:00Z', end=f'{year}-{month:02}-01T04:00:00Z',
                source_evidence_ref=f'synthetic:month:{offset}:category:{i}', correlation_ref='synthetic:history'))
    return tuple(rows)
