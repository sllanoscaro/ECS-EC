"""Local-only, idempotent preparation using the owners' configuration APIs."""
import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import asyncssh
from sqlalchemy import select
from demo_profile import BINDING_ID, channels
from ecs_ec.acquisition.schemas import BindingInput
from ecs_ec.acquisition.config import AcquisitionSettings, current_binding, install_binding
from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.catalog_storage import BuildingRow, MeasurementSourceRow, read_revisions
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.consumption.models import BuildingContext, ConfigurationInput
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork


async def main():
    """Provision only a local demo context, then preserve its SSH identity across starts."""
    settings = Settings()
    if settings.environment != 'local':
        raise RuntimeError('demo_requires_local_environment')
    database = Database(settings.database_url.get_secret_value())
    clock = SystemClock()
    building_id = UUID(os.environ['IDENTITY_BUILDING_ID'])
    descriptors = channels()
    try:
        async with UnitOfWork(database.sessions) as uow:
            existing = await uow.session.scalar(select(BuildingRow))
            if existing is None:
                await bootstrap(uow, building=BuildingContext(id=building_id,
                    name='Edificio de demostración sintético', timezone=settings.building_timezone,
                    created_at=clock.now()), configuration=ConfigurationInput(expected_revision=0,
                    effective_from=clock.now()-timedelta(days=2), timezone=settings.building_timezone,
                    categories=[dict(category_id=c['category_id'], has_meter=c['category_id']!='CAT-01',
                        source_id=c['source_id'] if c['category_id']!='CAT-01' else None,
                        source_label=f"Demo {c['category_id']}" if c['category_id']!='CAT-01' else None) for c in descriptors]),
                    clock=clock, actor_ref='process:consumption_bootstrap')
                await uow.commit()
            elif existing.id != building_id or existing.name != 'Edificio de demostración sintético' or existing.timezone != settings.building_timezone:
                raise RuntimeError('demo_refuses_existing_installation')
        async with UnitOfWork(database.sessions) as uow:
            total = descriptors[0]
            if await uow.session.get(MeasurementSourceRow, UUID(total['source_id'])) is None:
                uow.session.add(MeasurementSourceRow(id=UUID(total['source_id']), building_id=building_id,
                    label='Demo CAT-01', created_at=clock.now()))
            # Adopt the requested default once; later administrator choices survive restarts.
            marker = Path('/demo/calculated-default-v1')
            if not marker.exists():
                previous_revision = (await read_revisions(uow, building_id))[-1]
                entries = [c.model_dump(exclude={'category_revision'}) for c in previous_revision.categories]
                entries[0].update(has_meter=False, source_id=None, source_label=None)
                await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=building_id,
                    request=ConfigurationInput(expected_revision=previous_revision.revision,
                        effective_from=None, timezone=settings.building_timezone, categories=entries),
                    actor_ref='process:consumption_bootstrap')
            await uow.commit()
            marker.touch(mode=0o600)
        binding = dict(id=BINDING_ID, revision=1, building_id=str(building_id), username='demo',
            directory='/', timezone=settings.building_timezone, publisher_serial='SYNTHETIC-PAS600',
            publisher_remote_id='synthetic-pas600', channels=descriptors)
        previous = await current_binding(database, 'demo')
        if previous is None:
            await install_binding(database, clock, AcquisitionSettings(), 'process:pas600-demo', binding)
        elif previous.model_dump(mode='json') != BindingInput.model_validate(binding).model_dump(mode='json'):
            raise RuntimeError('demo_binding_changed')
        root = Path('/demo')
        for folder in ('server', 'client', 'bytes', 'state', 'runs'):
            (root/folder).mkdir(mode=0o700, exist_ok=True)
        for filename in ('server/host_key', 'client/key'):
            path = root/filename
            if not path.exists():
                asyncssh.generate_private_key('ssh-ed25519').write_private_key(path)
                path.chmod(0o600)
        host = asyncssh.read_private_key(root/'server/host_key')
        client = asyncssh.read_private_key(root/'client/key')
        auth = root/'server/auth.json'
        auth.write_text(json.dumps({'demo': {'public_keys': [client.export_public_key().decode()]}}))
        auth.chmod(0o600)
        (root/'client/known_hosts').write_bytes(b'[app]:2222 '+host.export_public_key())
        (root/'client/transport.json').write_text(json.dumps(dict(destination_alias='local-demo',
            host='app', port=2222, directory='/', username='demo',
            known_hosts_file='/demo/client/known_hosts', auth={'private_key_file':'/demo/client/key'},
            publication_gap_seconds=900, local_calendar=True, max_attempts=3)))
        for path in [root, *root.rglob('*')]:
            os.chown(path, 10001, 10001)
        print('Demostración local preparada.', flush=True)
    finally:
        await database.close()


if __name__ == '__main__':
    asyncio.run(main())
