"""Private001 browser scenarios using real001 configuration and002 reception, never HTTP seed routes."""
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4
from backend.tests.run_history_browser import checked_settings, HistoryBrowserClock
from ecs_ec.core.database import Database
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.catalog_storage import read_revisions
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.models import ConfigurationInput, SourceInput
from ecs_ec.consumption.reception import Reception
from ecs_ec.consumption.store import MeasurementStore
import os


async def control(action):
    """Advance the private clock and publish deterministic partial/late/maximum/change evidence.

    Requires an isolated physical fixture with all seven known sources. Returns only the
    selection to inspect; malformed actions and rejected publications fail the command.
    """
    if action not in {'partial', 'late', 'maximum', 'changed', 'own'}:
        raise ValueError('unknown_fixture_action')
    settings = checked_settings()
    clock = HistoryBrowserClock(os.environ['HISTORY_E2E_CLOCK_FILE'])
    database = Database(settings.database_url.get_secret_value())
    building = settings.identity_options().building_id
    state_path = Path(os.environ['HISTORY_E2E_CLOCK_FILE'] + '.selection')
    def advance(seconds):
        """Move only the protected fixture clock; never modify the host clock."""
        Path(os.environ['HISTORY_E2E_CLOCK_FILE']).write_text((clock.now() + timedelta(seconds=seconds)).isoformat())
    try:
        advance(901)
        async with UnitOfWork(database.sessions) as uow:
            previous = (await read_revisions(uow, building))[-1]
            if action != 'late':
                present = (3, 5) if action == 'partial' else tuple(range(2, 8)) if action == 'maximum' else (3, 4, 5, 6, 7)
                entries = tuple(SourceInput(**(e.model_dump(exclude={'category_revision'}) | dict(
                    has_meter=i in present, source_id=UUID(int=2 if action == 'own' and i == 5 else i) if i in present else None,
                    source_label=f'Synthetic meter{i}' if i in present else None))) for i, e in enumerate(previous.categories, 1))
                await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=building,
                    request=ConfigurationInput(expected_revision=previous.revision, effective_from=None,
                        timezone=previous.timezone, categories=entries), actor_ref='process:consumption_browser')
                await uow.commit()
        if action == 'late':
            selection = json.loads(state_path.read_text())
        else:
            start = clock.now() + timedelta(seconds=-30 if action == 'changed' else 60)
            end = clock.now() + timedelta(seconds=120)
            from zoneinfo import ZoneInfo
            selection = dict(start=start.astimezone(ZoneInfo('America/Santiago')).isoformat(),
                end=end.astimezone(ZoneInfo('America/Santiago')).isoformat(), timezone='America/Santiago')
            state_path.write_text(json.dumps(selection))
        values = [(5, '12')] if action in ('partial','changed','own') else [(3,'8')] if action == 'late' else [
            (i,'999999999999999999999999999999.999999999999999') for i in range(2,8)]
        records = [dict(building_id=building, category_id=f'CAT-{i:02}', source_id=UUID(int=i),
            value=value, unit='kWh', start=selection['start'], end=selection['end'],
            source_evidence_ref='synthetic:browser:advanced', correlation_ref='synthetic:browser') for i,value in values]
        reception = Reception(database, clock, authorized_processes={'process:consumption_browser': {building}})
        result = await reception.accept(uuid4(), building, 'synthetic:advanced', 'process:consumption_browser', records, 'synthetic:advanced')
        expected = 'rejected' if action == 'own' else 'accepted'
        if any(r.status != expected for r in result.results):
            raise ValueError('fixture_reception_rejected')
        print(json.dumps(selection))
    finally:
        await database.close()


if __name__ == '__main__':
    asyncio.run(control(sys.argv[1]))
