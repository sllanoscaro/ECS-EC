"""008 opt-in browser harness runs the actual compiled static export and monolith against exclusive PostgreSQL."""

import asyncio
import os
import socket
import subprocess
from pathlib import Path

import httpx
import pytest


async def test_actual_notification_rules_browser(
    account_factory,
    history_environment,
    test_url,
    identity_settings,
    tmp_path,
    monkeypatch,
):
    """Exercise rules and006 denial paths with real clients/queries; bootstrap is private, never a public endpoint."""
    web = os.environ.get("NOTIFICATION_BROWSER_WEB")
    if not web:
        pytest.skip("Explicit built008 export required for browser acceptance")
    assert (Path(web) / "index.html").is_file()
    await account_factory(
        role="administrador_tecnico", email="notification-admin@example.test"
    )
    await account_factory(role="operador", email="notification-operator@example.test")
    secret = tmp_path / "password"
    secret.write_text("Synthetic password 006")
    secret.chmod(0o600)
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "DATABASE_URL": test_url,
        "ENVIRONMENT": "test",
        "PUBLIC_URL": origin,
        "WEB_DIRECTORY": web,
        "IDENTITY_ENABLED": "true",
        "IDENTITY_DEVELOPMENT_HTTP": "true",
        "IDENTITY_BUILDING_ID": "00000000-0000-0000-0000-000000000063",
        "IDENTITY_CSRF_KEY": identity_settings.csrf_key.get_secret_value(),
        "IDENTITY_LOGIN_BUCKET_KEY": identity_settings.login_bucket_key.get_secret_value(),
        "OBS_ENABLED": "false",
        "PAS600_SFTP_ENABLED": "false",
        "NOTIFICATION_ENABLED": "false",
    }
    if os.environ.get("NOTIFICATION_TEST_SMTP") == "1":
        env.update(
            NOTIFICATION_ENABLED="true", SMTP_HOST="127.0.0.1", SMTP_PORT="11025"
        )
    log = tmp_path / "server.log"
    with log.open("wb") as output:
        process = subprocess.Popen(
            [
                ".venv/bin/uvicorn",
                "ecs_ec.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
                "--log-level",
                "critical",
            ],
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    try:
        async with httpx.AsyncClient(
            base_url=origin, trust_env=False, timeout=1
        ) as client:
            for _ in range(100):
                try:
                    if (await client.get("/api/v1/health/ready")).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if process.poll() is not None:
                    raise AssertionError("Private notification monolith did not start")
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("Private notification monolith readiness timeout")
        artifacts = Path(
            os.environ.get(
                "NOTIFICATION_BROWSER_ARTIFACTS", str(tmp_path / "screenshots")
            )
        )
        artifacts.mkdir(parents=True, exist_ok=True)
        runenv = {
            **env,
            "E2E_BASE_URL": origin,
            "IDENTITY_E2E_PASSWORD_FILE": str(secret),
            "NOTIFICATION_E2E_PASSWORD_FILE": str(secret),
            "NOTIFICATION_E2E_ARTIFACTS": str(artifacts),
        }
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "node",
                "--jitless",
                "node_modules/@playwright/test/cli.js",
                "test",
                "tests/e2e/notification-rules.spec.ts",
                "tests/e2e/notification-periodic.spec.ts",
                "--workers=1",
            ],
            cwd="frontend",
            env=runenv,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout[-7000:] + result.stderr[-1000:]
    finally:
        process.terminate()
        await asyncio.to_thread(process.wait, timeout=15)
