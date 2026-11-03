"""Opt-in real browser harness over existing006/PostgreSQL and the built monolith export.

No public provisioning/injection routes; test-only accounts use real owner fixtures.
Requires both explicit007 test stack and its locally built validation image/browser CA.
"""

import os
from pathlib import Path
import socket
import subprocess
import time
import httpx


async def test_real_functional_and_technical_browser(account_factory, test_url, identity_settings, tmp_path, gateway_root):
    """Seed real006 accounts privately, run real monolith/export, and execute isolation E2E with CA trust."""
    await account_factory(role="administrador_tecnico", email="obs-admin@example.test")
    await account_factory(role="operador", email="obs-operator@example.test")
    protected = tmp_path / "functional-password"
    protected.write_text("Synthetic password 006")
    protected.chmod(0o600)
    technical = tmp_path / "technical-password"
    technical.write_text("Synthetic technical password 007")
    technical.chmod(0o600)
    container = subprocess.check_output(["docker", "create", "ecs007-validation-app:local"], text=True).strip()
    try:
        subprocess.run(["docker", "cp", f"{container}:/app/backend/src/ecs_ec/web", str(tmp_path / "web")], check=True, capture_output=True)
    finally:
        subprocess.run(["docker", "rm", container], check=True, capture_output=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {**os.environ, "DATABASE_URL": test_url, "ENVIRONMENT": "test", "PUBLIC_URL": origin,
           "WEB_DIRECTORY": str(tmp_path / "web"), "IDENTITY_ENABLED": "true", "OBS_ENABLED": "false",
           "IDENTITY_DEVELOPMENT_HTTP": "true", "IDENTITY_CSRF_KEY": identity_settings.csrf_key.get_secret_value(),
           "IDENTITY_LOGIN_BUCKET_KEY": identity_settings.login_bucket_key.get_secret_value()}
    server = subprocess.Popen(["uv", "run", "uvicorn", "ecs_ec.main:create_app", "--factory", "--host", "127.0.0.1",
                               "--port", str(port), "--no-access-log", "--log-level", "critical"], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(trust_env=False, timeout=1) as client:
            for _ in range(100):
                try:
                    if client.get(origin + "/api/v1/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if server.poll() is not None:
                    raise AssertionError("Real browser monolith startup failed")
                time.sleep(0.1)
            else:
                raise AssertionError("Real browser monolith readiness timeout")
        browser_env = {**os.environ, "OBS_E2E_PASSWORD_FILE": str(technical), "OBS_FUNCTIONAL_PASSWORD_FILE": str(protected),
                       "OBS_FUNCTIONAL_BASE_URL": origin, "OBS_E2E_URL": os.environ.get("OBS_TEST_URL", "https://localhost:3444"),
                       "NODE_EXTRA_CA_CERTS": str(gateway_root / "ca.crt")}
        result = subprocess.run(["npm", "--prefix", "frontend", "run", "test:e2e", "--", "tests/e2e/observability-isolation.spec.ts"],
                                env=browser_env, capture_output=True, text=True, timeout=180)
        # Only test output from fixed synthetic fixtures; no credentials are put into args.
        assert result.returncode == 0, result.stdout[-5000:]
    finally:
        server.terminate()
        server.wait(timeout=10)
