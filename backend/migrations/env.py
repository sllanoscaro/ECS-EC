"""Alembic async PostgreSQL environment; configuration is supplied externally."""

import asyncio

from alembic import context
from ecs_ec.core.database import Base, Database
from ecs_ec.core.settings import Settings

from ecs_ec.audit import models  # noqa: F401 -- register only installed metadata owners.
from ecs_ec.identity import models as identity_models  # noqa: F401 -- identity owns its five tables.
from ecs_ec.consumption import catalog_storage  # noqa: F401 --001 installation metadata.
from ecs_ec.consumption import models as history_models  # noqa: F401 --002 history metadata.

target_metadata = Base.metadata


def configure(connection):
    """Run transactional DDL on the caller connection; compare typed column changes."""
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def online():
    """Migrate PostgreSQL and always close the migration engine."""
    database = Database(Settings().database_url.get_secret_value())
    try:
        async with database.engine.connect() as connection:
            await connection.run_sync(configure)
    finally:
        await database.close()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url.get_secret_value(), target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
