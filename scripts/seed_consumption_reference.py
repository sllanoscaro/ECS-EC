"""Seed001 browser references through actual001 configuration and002 reception in a separate empty *_test DB.

Usage: TEST_DATABASE_URL=... uv run python scripts/seed_consumption_reference.py
    --password-file /protected/file --mode physical|calculated
The password file must be mode0600. Identity references are created by the existing006
fixture script and require ordinary first-password renewal. No public seed route exists.
"""

import argparse
import asyncio
import os
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.catalog_storage import BuildingRow
from ecs_ec.consumption.models import BuildingContext, ConfigurationInput
from ecs_ec.consumption.reception import Reception
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork
from seed_identity_reference import seed as seed_identity


async def seed(password_file, mode):
    """Reject application/production destinations, provision synthetic sources and publish21 or6 original intervals."""
    settings = Settings()
    target = make_url(os.environ.get('TEST_DATABASE_URL', ''))
    source = make_url(settings.database_url.get_secret_value())
    if (settings.environment == 'production' or target.drivername != 'postgresql+psycopg'
            or not (target.database or '').endswith('_test') or target.database == source.database):
        raise ValueError('Separate test database required')
    database, clock, building_id = Database(target), SystemClock(), UUID(int=99)
    try:
        async with UnitOfWork(database.sessions) as uow:
            if await uow.session.scalar(select(func.count()).select_from(BuildingRow)):
                raise ValueError('Empty consumption fixture destination required')
        await seed_identity(password_file)
        present = range(1, 8) if mode == 'physical' else (3, 5)
        request = ConfigurationInput(expected_revision=0, effective_from='2025-01-01T00:00:00Z', timezone='America/Santiago',
            categories=tuple(dict(category_id=f'CAT-{i:02}', has_meter=i in present,
                source_id=UUID(int=i) if i in present else None, source_label=f'Synthetic meter{i}' if i in present else None)
                for i in range(1, 8)))
        async with UnitOfWork(database.sessions) as uow:
            await bootstrap(uow, building=BuildingContext(id=building_id, name='Synthetic browser building',
                timezone='America/Santiago', created_at=clock.now()), configuration=request, clock=clock,
                actor_ref='process:consumption_browser')
            await uow.commit()
        records = []
        for i in present:
            for index, (start, end) in enumerate(((0, 1), (1, 2), (3, 4))):
                value = ('100' if i == 1 else '10') if mode == 'physical' else ('12' if i == 3 else '8')
                if index == 1:
                    value = '0'
                if index == 2:
                    value = '0.000000000000001'
                records.append(dict(building_id=building_id, category_id=f'CAT-{i:02}', source_id=UUID(int=i), value=value,
                    unit='kWh', start=f'2026-01-01T{start:02}:00:00-03:00', end=f'2026-01-01T{end:02}:00:00-03:00',
                    source_evidence_ref=f'synthetic:browser:{i}:{index}', correlation_ref='synthetic:browser'))
        reception = Reception(database, clock, authorized_processes={'process:consumption_browser': {building_id}})
        outcome = await reception.accept(uuid4(), building_id, 'synthetic-browser', 'process:consumption_browser', records, 'synthetic:browser')
        if outcome.state != 'completed' or any(r.status != 'accepted' for r in outcome.results):
            raise ValueError('Fixture publication incomplete')
        print(f'Synthetic {mode} fixture: {len(records)} physical intervals accepted through002.')
    finally:
        await database.close()


def main():
    """Read only a protected password file path and closed fixture mode; report no credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--password-file', required=True)
    parser.add_argument('--mode', choices=('physical', 'calculated'), required=True)
    args = parser.parse_args()
    asyncio.run(seed(args.password_file, args.mode))


if __name__ == '__main__':
    main()
