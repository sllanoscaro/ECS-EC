"""Shared deterministic fixtures; integration tests refuse non-test databases."""

import os
import subprocess
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import make_url

pytest_plugins = ["backend.tests.identity_fixtures"]


def checked_test_url() -> str:
    """Return explicit, distinct PostgreSQL test URL or fail before any DB mutation."""
    raw = os.environ.get("TEST_DATABASE_URL", "")
    if not raw:
        raise pytest.UsageError("TEST_DATABASE_URL is required for integration tests")
    url = make_url(raw)
    from ecs_ec.core.settings import Settings
    # Read the same .env/env precedence as the application, not only the shell env.
    production = Settings().database_url.get_secret_value()
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise pytest.UsageError("Tests require PostgreSQL and a database ending in _test")
    if production:
        other = make_url(production)
        # Reject the same database name even through host aliases or other credentials.
        if url.database == other.database:
            raise pytest.UsageError("Test and application database must be distinct")
    return raw


@pytest.fixture(scope="session")
def test_url():
    """Migrate only the explicitly checked test database; fail on migration errors."""
    raw = checked_test_url()
    subprocess.run(
        [".venv/bin/alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": raw, "ENVIRONMENT": "test"}, check=True,
    )
    return raw


@pytest.fixture
async def database(test_url):
    """Yield an isolated engine/session factory and dispose connections after each test."""
    from ecs_ec.core.database import Database
    db = Database(test_url)
    yield db
    await db.close()


@pytest.fixture
def clock():
    """Provide an internally injected UTC/monotonic clock without a public control route."""
    from ecs_ec.core.clock import FrozenClock
    return FrozenClock(datetime(2026, 1, 1, tzinfo=UTC))

#002's opt-in real-port fixtures are also available to sibling contract tests.
from backend.tests.integration.consumption.conftest import consumption_reception_environment, history_environment, history_scenarios  # noqa: F401
#004's fixtures reuse the checked PostgreSQL factory and real001/002 ports.
from backend.tests.costs_fixtures import costs_environment  # noqa: F401
from backend.tests.costs_fixtures import costs_client  # noqa: F401
