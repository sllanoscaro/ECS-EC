"""Prepare004 browser evidence in an empty, separate *_test database using actual006/001/002 services.

Run uv run --locked python scripts/seed_costs_reference.py --password-file /protected/file.
The existing006 fixture tool validates the password file mode0600 and creates accounts
requiring ordinary renewal. Only synthetic tariff references are created; no real prices.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.engine import make_url
from sqlalchemy import select, func

# These reference factories are explicit test fixtures, never shipped in the runtime image.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.tests.costs_fixtures import seed_supply
from backend.tests.unit.consumption.test_catalog import installation
from seed_identity_reference import seed as seed_identity
from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.models import BuildingContext, instant
from ecs_ec.consumption.catalog_storage import BuildingRow
from ecs_ec.consumption.reception import Reception
from ecs_ec.core.database import Database
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork


async def seed(password_file, *, without_costs=False):
    """Reject application/production destinations, then create controlled supply/profile and1000 physical kWh."""
    settings = Settings()
    target = make_url(os.environ.get('TEST_DATABASE_URL', ''))
    source = make_url(settings.database_url.get_secret_value())
    if settings.environment == 'production' or target.drivername != 'postgresql+psycopg' or not (target.database or '').endswith('_test') or target.database == source.database:
        raise ValueError('A separate synthetic test database is required')
    database, clock = Database(target), SystemClock()
    try:
        async with UnitOfWork(database.sessions) as uow:
            if await uow.session.scalar(select(func.count()).select_from(BuildingRow)):
                raise ValueError('An empty consumption/costs context is required')
        await seed_identity(password_file)
        async with UnitOfWork(database.sessions) as uow:
            await bootstrap(uow, building=BuildingContext(id=UUID(int=99), name='Synthetic004 building',
                timezone='America/Santiago', created_at=clock.now()),
                configuration=installation((1,)).model_copy(update={'effective_from': instant('2025-01-01T00:00:00Z')}),
                clock=clock, actor_ref='process:costs_fixture')
            await uow.commit()
        if not without_costs:
            await seed_supply(database, clock)
        receiver = Reception(database, clock, authorized_processes={'process:costs_fixture': {UUID(int=99)}})
        result = await receiver.accept(uuid4(), UUID(int=99), 'synthetic004', 'process:costs_fixture', [dict(
            building_id=UUID(int=99), category_id='CAT-01', source_id=UUID(int=1), value='1000', unit='kWh',
            start='2026-01-01T00:00:00Z', end='2026-01-01T01:00:00Z', source_evidence_ref='synthetic:004:measurement',
            correlation_ref='synthetic:004:publication')], 'synthetic:004:publication')
        if result.results[0].status != 'accepted':
            raise ValueError('Fixture reception failed')
        print('Synthetic004 fixture ready: physical1000kWh; costs configuration ' + ('absent for initial web setup.' if without_costs else 'documented100CLP/kWh energy-only test profile.'))
    finally:
        await database.close()


def main():
    """Accept only a protected synthetic credential-file path; no public seed route is exposed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--password-file', required=True)
    parser.add_argument('--without-costs', action='store_true', help='Leave004 configuration absent for initial web administration tests')
    args = parser.parse_args()
    asyncio.run(seed(args.password_file, without_costs=args.without_costs))


if __name__ == '__main__':
    main()
