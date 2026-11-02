"""Real PostgreSQL transactions prove commit, rollback and connection release."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_commit_rollback_and_close(database):
    """Use a temporary synthetic table; explicit commit persists, normal exit rolls back."""
    name = "probe_" + uuid4().hex
    async with database.engine.begin() as connection:
        assert int(await connection.scalar(text("SHOW server_version_num"))) >= 180000
        await connection.execute(text(f"CREATE TABLE {name} (id integer PRIMARY KEY)"))
    try:
        async with UnitOfWork(database.sessions) as uow:
            await uow.session.execute(text(f"INSERT INTO {name} VALUES (1)"))
            await uow.commit()
        async with UnitOfWork(database.sessions) as uow:
            await uow.session.execute(text(f"INSERT INTO {name} VALUES (2)"))
        with pytest.raises(RuntimeError):
            async with UnitOfWork(database.sessions) as uow:
                await uow.session.execute(text(f"INSERT INTO {name} VALUES (3)"))
                raise RuntimeError("synthetic failure")
        async with database.engine.connect() as connection:
            assert list((await connection.execute(text(f"SELECT id FROM {name}"))).scalars()) == [1]
        assert database.engine.pool.checkedout() == 0
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE {name}"))
