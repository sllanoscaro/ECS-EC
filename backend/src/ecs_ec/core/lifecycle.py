"""Extensible internal lifecycle and migration readiness, without domain dependencies."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, FastAPI
from sqlalchemy import inspect, text

from ecs_ec.core.database import Database
from ecs_ec.core.errors import PlatformError, SchemaNotReady


@dataclass(frozen=True)
class Module:
    """Installed module registration: optional router and context-managed internal services.

    Context managers must supervise their tasks, propagate unexpected startup failures,
    and stop/join them on exit. Registration does not import absent module owners.
    """

    name: str
    router: APIRouter | None = None
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager] | None = None


async def require_schema(database: Database) -> None:
    """Require reachable PostgreSQL 18+ at the exact installed Alembic heads; hide DB errors."""
    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    try:
        async with database.engine.connect() as connection:
            version = int(await connection.scalar(text("SHOW server_version_num")))
            actual = await connection.run_sync(current_heads)
        if version < 180000 or actual != expected:
            raise SchemaNotReady()
    except SchemaNotReady:
        raise
    except Exception:
        raise PlatformError() from None


def current_heads(connection) -> set[str]:
    """Read schema revision on an existing connection without modifying the database."""
    if not inspect(connection).has_table("alembic_version"):
        raise SchemaNotReady()
    return set(MigrationContext.configure(connection).get_current_heads())


def application_lifespan(database: Database, modules: tuple[Module, ...]):
    """Build a context manager that validates dependencies and closes services in reverse order."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Acquire core resources before modules; dispose DB even on partial startup failure."""
        try:
            await require_schema(database)
            if not (app.state.settings.web_directory / "index.html").is_file():
                raise PlatformError()
            async with AsyncExitStack() as stack:
                for module in modules:
                    if module.lifespan:
                        await stack.enter_async_context(module.lifespan(app))
                yield
        finally:
            await database.close()

    return lifespan
