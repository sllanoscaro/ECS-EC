"""Real DB bootstrap: readiness, schema gating, static assets, restart and clean shutdown."""

from contextlib import asynccontextmanager

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import text

from ecs_ec.core.errors import SchemaNotReady
from ecs_ec.core.lifecycle import Module, require_schema
from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app

pytestmark = pytest.mark.integration


async def test_bootstrap_restart_shutdown(test_url, tmp_path, clock):
    """Start twice against migrated PostgreSQL and verify module teardown and static/API responses."""
    (tmp_path / "index.html").write_text("<h1>ECS-EC synthetic export</h1>")
    settings = Settings(database_url=SecretStr(test_url), web_directory=tmp_path, environment="test")
    calls = []

    @asynccontextmanager
    async def service(app):
        """Synthetic extension records startup/teardown without domain code."""
        calls.append("start")
        yield
        calls.append("stop")

    for _ in range(2):
        app = create_app(settings, (Module("synthetic", lifespan=service),), clock)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/v1/health/ready")).json() == {"status": "ready"}
                assert (await client.get("/api/v1/health/live")).status_code == 200
                assert "synthetic export" in (await client.get("/")).text
                assert (await client.get("/api/v1/absent")).status_code == 404
        assert app.state.database.engine.pool.checkedout() == 0
    assert calls == ["start", "stop", "start", "stop"]


async def test_refuse_wrong_schema(database):
    """A temporary schema with no migrations cannot become ready; no shared revision is mutated."""
    from ecs_ec.core.database import Database
    from uuid import uuid4
    schema = "unmigrated_" + uuid4().hex
    async with database.engine.begin() as connection:
        await connection.execute(text(f"CREATE SCHEMA {schema}"))
    other = Database(database.engine.url)
    # Limit search_path on this engine only; the actual test schema is untouched.
    await other.close()
    from sqlalchemy.ext.asyncio import create_async_engine
    other.engine = create_async_engine(database.engine.url, connect_args={"options": f"-c search_path={schema}"})
    try:
        with pytest.raises(SchemaNotReady):
            await require_schema(other)
    finally:
        await other.close()
        async with database.engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {schema}"))
