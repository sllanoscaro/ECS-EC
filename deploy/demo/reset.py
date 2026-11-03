"""Explicit local-only synthetic consumption reset; requires a preexisting complete PostgreSQL backup."""
import argparse
import asyncio
from datetime import timedelta
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, text
from demo_profile import channels
from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.catalog_storage import BuildingRow, read_revisions, MeasurementSourceRow
from ecs_ec.consumption.models import BuildingContext, ConfigurationInput
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.settings import Settings
from ecs_ec.core.database import Database
from ecs_ec.core.unit_of_work import UnitOfWork


async def reset(backup):
    """Refuse real contexts/costs; preserve accounts/audit and reprovision the selected synthetic source modes."""
    with backup.open('rb') as stream:
        signature = stream.read(5)
    if signature != b'PGDMP':
        raise ValueError('complete_postgresql_backup_required')
    settings = Settings()
    if settings.environment != 'local':
        raise ValueError('local_only')
    database, clock = Database(settings.database_url.get_secret_value()), SystemClock()
    try:
        async with UnitOfWork(database.sessions) as uow:
            building = await uow.session.scalar(select(BuildingRow).with_for_update())
            if building is None or building.name != 'Edificio de demostración sintético':
                raise ValueError('synthetic_context_required')
            if await uow.session.scalar(text('SELECT count(*) FROM cost_supply')):
                raise ValueError('refuses_existing_cost_configuration')
            previous = (await read_revisions(uow, building.id))[-1]
            entries = [c.model_dump(exclude={'category_revision'}) for c in previous.categories]
            ids = {c['source_id'] for c in channels()}
            if any(c['source_id'] is not None and str(c['source_id']) not in ids for c in entries):
                raise ValueError('refuses_non_demo_sources')
            context = BuildingContext(id=building.id, name=building.name, timezone=building.timezone, created_at=clock.now())
            await uow.session.execute(text('TRUNCATE consumption_building CASCADE'))
            uow.session.expunge_all()
            await bootstrap(uow, building=context, configuration=ConfigurationInput(expected_revision=0,
                effective_from=clock.now()-timedelta(days=2), timezone=context.timezone, categories=entries),
                clock=clock, actor_ref='process:consumption_bootstrap')
            for descriptor in channels():
                source_id = UUID(descriptor['source_id'])
                if await uow.session.get(MeasurementSourceRow, source_id) is None:
                    uow.session.add(MeasurementSourceRow(id=source_id, building_id=context.id,
                        label=f"Demo {descriptor['category_id']}", created_at=clock.now()))
            await uow.commit()
        print('Consumo sintético reiniciado; cuentas y auditoría conservadas.', flush=True)
    finally:
        await database.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup-file', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(reset(args.backup_file))
