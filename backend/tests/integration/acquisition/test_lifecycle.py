"""Optional003 startup aborts orphan writes under exclusive leadership and releases resources on exit."""
from types import SimpleNamespace
from contextlib import AsyncExitStack
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.lifecycle import acquisition_module
from ecs_ec.acquisition.staging import Staging
from ecs_ec.acquisition.models import SftpSessionAttempt
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark=pytest.mark.integration


async def test_disabled_and_exclusive_restart(sftp_environment):
    """Disabled mode needs no resources; only the elected listener may abort an old incomplete session."""
    env=sftp_environment
    async with acquisition_module(env['clock'],env['settings']).lifespan(SimpleNamespace()):pass
    env['listener'].close();await env['listener'].wait_closed()
    stage=Staging(env['database'],env['clock'],env['settings'],env['binding']);await stage.start()
    # The fixture listener's actual key/auth settings are retained on its validated server configuration.
    settings=env['settings'].model_copy(update={'sftp_enabled':True,'host_key_file':env['private'].parent/'host','auth_file':env['private'].parent/'auth'})
    app=SimpleNamespace(state=SimpleNamespace(database=env['database']))
    module=acquisition_module(env['clock'],settings)
    async with module.lifespan(app):
        async with UnitOfWork(env['database'].sessions) as uow:
            row=(await uow.session.scalars(select(SftpSessionAttempt))).one()
            assert row.state=='aborted' and row.reason=='process_interrupted'
        with pytest.raises(ValueError,match='already_active'):
            async with module.lifespan(app):pass
    async with module.lifespan(app):pass
