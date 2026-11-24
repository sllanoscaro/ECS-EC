"""The acquisition migration refuses rollback when retained evidence has been installed."""
import asyncio,os
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import text
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark=pytest.mark.integration


async def test_populated_migration_cannot_downgrade(acquisition_environment,test_url):
    """Even a binding is retained evidence: downgrade fails atomically and leaves the installed head unchanged."""
    expected=ScriptDirectory.from_config(Config('backend/alembic.ini')).get_current_head()
    async with UnitOfWork(acquisition_environment['database'].sessions) as uow:
        before=await uow.session.scalar(text('SELECT version_num FROM alembic_version'))
        assert before==expected
    process=await asyncio.create_subprocess_exec('.venv/bin/alembic','-c','backend/alembic.ini','downgrade','costs_004_bills',
        env={**os.environ,'DATABASE_URL':test_url,'ENVIRONMENT':'test'},stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    assert process.returncode!=0
    async with UnitOfWork(acquisition_environment['database'].sessions) as uow:
        assert await uow.session.scalar(text('SELECT version_num FROM alembic_version'))==before
        assert await uow.session.scalar(text('SELECT count(*) FROM acquisition_binding'))==1
