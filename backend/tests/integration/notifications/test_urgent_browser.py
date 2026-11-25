"""Controlled-clock urgent UI uses the actual monolith and002 producer, with only private filesystem test coordination."""

import asyncio
import os
import socket
import subprocess
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
import uvicorn
from ecs_ec.core.clock import SystemClock
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.episodes import Evaluator
from ecs_ec.notifications.settings import NotificationSettings
from starlette.staticfiles import StaticFiles

from backend.tests.unit.consumption.test_validation import record


async def test_actual_urgent_ui_with_real_calculated_total(
    notification_context,
    consumption_reception_environment,
    account_factory,
    tmp_path,
    identity_settings,
):
    """Only the source fixture advances time; no product route can generate data or alter time."""
    web = os.environ.get("NOTIFICATION_BROWSER_WEB")
    if not web or os.environ.get("NOTIFICATION_TEST_SMTP") != "1":
        pytest.skip("Built export and exclusive local Mailpit required")
    ctx = notification_context
    ctx["clock"].advance((SystemClock().now() - ctx["clock"].now()).total_seconds())
    await account_factory(
        role="administrador_tecnico", email="urgent-admin@example.test"
    )
    await account_factory(role="operador", email="urgent-operator@example.test")
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    app = ctx["client"]._transport.app
    # A real ASGI application already lives in the fixture lifespan; change only
    # injected environment/frontend paths before exposing it on the ephemeral socket.
    app.state.settings.web_directory = Path(web)
    for route in app.routes:
        if getattr(route, "name", None) == "web":
            route.app = StaticFiles(directory=web, html=True)
    app.state.identity.settings = identity_settings.model_copy(
        update={"public_url": origin}
    )
    ctx["service"].settings = NotificationSettings(
        _env_file=None,
        environment="test",
        smtp_host="127.0.0.1",
        smtp_port=11025,
        app_public_base_url=origin,
    )
    secret = tmp_path / "password"
    secret.write_text("Synthetic password 006")
    secret.chmod(0o600)
    command, done = tmp_path / "command", tmp_path / "done"
    artifacts = Path(os.environ["NOTIFICATION_BROWSER_ARTIFACTS"])
    artifacts.mkdir(exist_ok=True, parents=True)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            access_log=False,
            log_level="critical",
        )
    )
    server_task = asyncio.create_task(server.serve())

    async def produce():
        """React only to the private synthetic fixture signal, then run002 incorporation/evaluation/local dispatch."""
        while not command.exists():
            await asyncio.sleep(0.05)
        assert command.read_text() == "publish_total"
        start = ctx["clock"].now()
        end = start + timedelta(hours=1)
        await consumption_reception_environment.publish(
            [
                record(start=start, end=end, value="12"),
                record(
                    start=start,
                    end=end,
                    value="8",
                    category_id="CAT-03",
                    source_id=UUID(int=3),
                ),
            ]
        )
        ctx["clock"].advance(3600)
        await Evaluator(ctx["service"]).tick()
        dispatcher = Dispatcher(ctx["service"])

        async def lose_recorded_result(claim, result):
            """Lose only functional persistence after actual local DATA acceptance; source/transport remain real."""
            assert result.outcome == "aceptada"
            raise OSError("synthetic result persistence loss")

        dispatcher.finish = lose_recorded_result
        try:
            with pytest.raises(OSError):
                await dispatcher.dispatch_once()
        finally:
            await dispatcher.close()
        from ecs_ec.notifications.recovery import reconcile_attempts

        assert await reconcile_attempts(ctx["service"]) == 1
        done.write_text("complete")

    producer = asyncio.create_task(produce())
    try:
        async with asyncio.timeout(10):
            while not server.started:
                await asyncio.sleep(0.05)
        env = {
            **os.environ,
            "E2E_BASE_URL": origin,
            "IDENTITY_E2E_PASSWORD_FILE": str(secret),
            "NOTIFICATION_E2E_PASSWORD_FILE": str(secret),
            "NOTIFICATION_URGENT_COMMAND": str(command),
            "NOTIFICATION_URGENT_DONE": str(done),
            "NOTIFICATION_E2E_ARTIFACTS": str(artifacts),
        }
        for scenario in [
            "tests/e2e/notification-urgent.spec.ts",
            "tests/e2e/notification-history.spec.ts",
        ]:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    "node",
                    "--jitless",
                    "node_modules/@playwright/test/cli.js",
                    "test",
                    scenario,
                    "--workers=1",
                ],
                cwd="frontend",
                env=env,
                capture_output=True,
                text=True,
                timeout=110,
            )
            assert result.returncode == 0, result.stdout[-7000:] + result.stderr[-1000:]
        await producer
    finally:
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)
        server.should_exit = True
        await asyncio.wait_for(server_task, 15)
