"""Internal002 E2E fixture publisher/maintenance command; never an installed application route.

Invoked from Playwright with an explicit test-only environment and protected clock.
Originals enter Reception.accept; withdrawal uses Retention's actual authorization,
locks, eligibility and audit. No direct inserts/deletes bypass business behavior.
"""
import argparse
import asyncio
import os
from uuid import UUID, uuid4
from sqlalchemy import select
from backend.tests.run_history_browser import checked_settings, HistoryBrowserClock
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.consumption.reception import Reception
from ecs_ec.consumption.retention import Retention
from ecs_ec.core.database import Database
from ecs_ec.core.unit_of_work import UnitOfWork


async def control(action):
    """Publish three quarters/the missing zero or withdraw all expired fixture detail; fail on rejection."""
    settings = checked_settings()
    database = Database(settings.database_url.get_secret_value())
    clock = HistoryBrowserClock(os.environ['HISTORY_E2E_CLOCK_FILE'])
    building_id, process = settings.identity_options().building_id, 'process:history_browser'
    try:
        if action == 'withdraw':
            async with UnitOfWork(database.sessions) as uow:
                ids = tuple((await uow.session.scalars(select(IncorporatedRecord.id).where(
                    IncorporatedRecord.building_id == building_id))).all())
            results = await Retention(database, clock, authorized_processes={process: {building_id}}).withdraw_detail(
                building_id=building_id, record_ids=ids, process=process, reason='expired_fixture')
            if any(r['status'] != 'withdrawn' for r in results):
                raise ValueError('fixture_withdrawal_rejected')
        else:
            minutes = ((0,15),(15,30),(30,45)) if action == 'base' else ((45,60),)
            rows = [dict(building_id=building_id, category_id='CAT-05', source_id=UUID(int=5),
                start=f'2026-02-01T00:{start:02}:00-03:00',
                end=f'2026-02-01T00:{end:02}:00-03:00' if end < 60 else '2026-02-01T01:00:00-03:00',
                value='1' if action == 'base' else '0', unit='kWh', source_evidence_ref='synthetic:history:browser',
                correlation_ref='synthetic:history:browser') for start, end in minutes]
            result = await Reception(database, clock, authorized_processes={process: {building_id}}).accept(
                uuid4(), building_id, 'history-browser', process, rows, 'synthetic:history:browser')
            if any(r.status not in {'accepted', 'duplicate'} for r in result.results):
                raise ValueError('fixture_publication_rejected')
    finally:
        await database.close()


def main():
    """Accept only closed fixture actions, with no arbitrary SQL, payload or operational destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('base', 'complete', 'withdraw'))
    asyncio.run(control(parser.parse_args().action))


if __name__ == '__main__':
    main()
