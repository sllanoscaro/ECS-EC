"""Opt-in stack isolation fixtures; business tests use existing owner fixtures/PostgreSQL."""

from uuid import uuid4
import pytest


@pytest.fixture
def technical_project(tmp_path):
    """Allocate unique test-only project, external resource directory and volume prefix.

    No containers start implicitly and no production volumes are selected or removed.
    Callers must tear down only the resources they explicitly created with this name.
    """
    return {"project": "ecs-obs-test-" + uuid4().hex, "root": tmp_path, "environment": "test"}


@pytest.fixture
def gateway_root():
    """Require explicit local test material; refuse local/vps/foreign roots before provisioning."""
    import os
    from pathlib import Path
    raw = os.environ.get("OBS_TEST_ROOT")
    if not raw:
        pytest.skip("OBS_TEST_ROOT required: real isolated007 stack is opt-in")
    root = Path(raw).resolve()
    if root.name != "test" or (root / "environment").read_text().strip() != "test":
        raise pytest.UsageError("Only explicitly prepared test environment is allowed")
    return root


@pytest.fixture
def gateway_provision(gateway_root):
    """Mutate only the selected test registry using a known synthetic fixture password."""
    from scripts.observability.manage_programmer import update
    def provision(action):
        """Enable/revoke only the dedicated opaque test subject, never a human credential."""
        return update(gateway_root.parent, "test", "prog-test-01", action,
                      b"Synthetic technical password 007" if action == "grant" else None)
    return provision


@pytest.fixture
async def gateway_client(gateway_root):
    """Connect through trusted local test TLS/Basic; never ignore certificate errors or use prod."""
    import os
    import ssl
    from urllib.parse import urlsplit
    import httpx
    url = os.environ.get("OBS_TEST_URL", "https://localhost:3444")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "localhost" or not parsed.port or parsed.port < 1024:
        raise pytest.UsageError("OBS_TEST_URL requires localhost HTTPS test listener")
    tls = ssl.create_default_context(cafile=str(gateway_root / "ca.crt"))
    async with httpx.AsyncClient(base_url=url, verify=tls, trust_env=False,
                                 auth=("prog-test-01", "Synthetic technical password 007"), timeout=35) as client:
        yield client
