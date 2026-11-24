"""006:T069/T077: real technical publication never grants functional identity or vice versa.

The003 listener and independent simulator use their actual credential paths.007's
existing external provisioning creates the Programador verifier; this suite checks
denial by006, not acceptance of007's gateway or a new functional role.
"""

from uuid import UUID

import asyncssh
import bcrypt
import pytest
from sqlalchemy import func, select

from backend.tests.integration.acquisition.conftest import acquisition_environment  # noqa: F401
from backend.tests.integration.acquisition.conftest import sftp_environment as _sftp_environment

sftp_environment = _sftp_environment
from backend.tests.integration.acquisition.test_recovery import service
from backend.tests.support.source_sftp import evaluations, generated_publication, publish_generated
from ecs_ec.acquisition.models import SftpSessionAttempt
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.models import Account, Session
from scripts.observability.manage_programmer import update

pytestmark = pytest.mark.integration


@pytest.fixture
def identity_settings(identity_settings):
    """Select the real consumption fixture's building; preserve the shared safe identity test configuration."""
    return identity_settings.model_copy(update={"building_id": UUID(int=99)})


@pytest.fixture(autouse=True)
def isolated_listeners(monkeypatch):
    """Keep the composed HTTP app from opening deployment SSH resources; the dedicated real fixture owns SSH."""
    monkeypatch.setenv("PAS600_SFTP_ENABLED", "false")


async def count_rows(database, model):
    """Count durable rows in a fresh readonly transaction without provisioning any account/session."""
    async with UnitOfWork(database.sessions) as uow:
        return await uow.session.scalar(select(func.count()).select_from(model))


async def test_authorized_publisher_needs_no_functional_account(client, sftp_environment, tmp_path):
    """The actual standalone publisher ingests8kWh with zero006 accounts/sessions and no HTTP cookie."""
    env = sftp_environment
    assert await count_rows(env["database"], Account) == 0
    assert await count_rows(env["database"], Session) == 0
    assert (await client.get("/api/v1/consumption/catalog")).status_code == 401
    run = await generated_publication(env, tmp_path)
    await publish_generated(env, tmp_path, run)
    await service(env).recover()
    evaluation, = await evaluations(env)
    assert [row["status"] for row in evaluation.outcome["results"]] == ["accepted", "accepted"]
    assert evaluation.outcome["updates"][0]["accepted_count"] == 2
    assert await count_rows(env["database"], Account) == 0
    assert await count_rows(env["database"], Session) == 0
    assert (await client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.parametrize("role", ["operador", "administrador_tecnico"])
@pytest.mark.parametrize("credential", ["password", "session_cookie"])
async def test_functional_session_does_not_authenticate_sftp(
    client, account_factory, login, sftp_environment, role, credential,
):
    """A genuine web session/password cannot authenticate the003 binding, even when claiming its technical username."""
    env = sftp_environment
    account = await account_factory(role=role)
    assert (await login(account.email)).status_code == 200
    assert (await client.get("/api/v1/consumption/catalog")).status_code == 200
    password = "Synthetic password 006" if credential == "password" else client.cookies.get("ecs_ec_session")
    for username in (account.email, "pas600"):
        with pytest.raises(asyncssh.PermissionDenied):
            async with asyncssh.connect(
                "127.0.0.1", env["port"], username=username, password=password,
                client_keys=[], known_hosts=str(env["known"]),
            ):
                pytest.fail("functional_identity_granted_sftp")
    assert await count_rows(env["database"], SftpSessionAttempt) == 0
    assert (await client.get("/api/v1/auth/session")).status_code == 200


@pytest.mark.parametrize("kind", ["sftp", "programador"])
async def test_technical_credentials_do_not_grant_functional_access(
    client, sftp_environment, tmp_path, kind,
):
    """Actual003 credentials or a007-provisioned verifier cannot authorize real006/001/004 reads or create a session."""
    env = sftp_environment
    if kind == "programador":
        subject, password = "prog-separation-01", "Synthetic programmer password 007"
        root = tmp_path / "technical"
        directory = root / "test"
        directory.mkdir(parents=True, mode=0o700)
        directory.chmod(0o700)
        (directory / "environment").write_text("test")
        assert update(root, "test", subject, "grant", password.encode()) == 1
        name, verifier = (directory / "credentials/authorized").read_text().strip().split(":", 1)
        assert name == subject and bcrypt.checkpw(password.encode(), verifier.encode())
    else:
        subject, password = "pas600", "Synthetic password003"
        async with asyncssh.connect(
            "127.0.0.1", env["port"], username=subject, password=password,
            client_keys=[], known_hosts=str(env["known"]),
        ):
            pass  # Successful real SSH authentication without opening a publication subsystem.
    for path in (
        "/api/v1/auth/session", "/api/v1/consumption/catalog", "/api/v1/costs/cycles",
        "/api/v1/identity/accounts", "/api/v1/identity/administration-history",
    ):
        response = await client.get(path, auth=(subject, password), headers={
            "X-Role": "administrador_tecnico", "X-WEBAUTH-USER": subject,
        })
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
        assert "ecs_ec_session" not in response.cookies
    assert await count_rows(env["database"], Account) == 0
    assert await count_rows(env["database"], Session) == 0
