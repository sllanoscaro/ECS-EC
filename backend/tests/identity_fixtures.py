"""Isolated PostgreSQL identity fixtures; synthetic credentials never enter public routes."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.fixture
async def identity_db(database):
    """Reset only the dedicated checked _test database; tests own all synthetic evidence here."""
    async with database.engine.begin() as connection:
        await connection.execute(text("TRUNCATE identity_session, identity_preauth, identity_login_bucket, identity_account, functional_audit, functional_event, functional_coverage"))
    yield database


@pytest.fixture
def identity_settings():
    """Fixed distinct synthetic HMAC keys for internal tests, not deployable defaults."""
    from ecs_ec.identity.settings import IdentitySettings
    return IdentitySettings(_env_file=None, csrf_key="a" * 43, login_bucket_key="b" * 43,
                            environment="test", public_url="http://localhost:8000", development_http=True)


@pytest.fixture(scope="session")
def reference_hash():
    """Hash a synthetic reference password with real production Argon2 parameters once."""
    from argon2 import PasswordHasher
    return PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, salt_len=16, hash_len=32).hash("Synthetic password 006")


@pytest.fixture
def account_factory(identity_db, reference_hash, clock):
    """Create synthetic states/roles with permanent UUIDs through explicit fixture-only DB access."""
    from ecs_ec.identity.models import Account
    from ecs_ec.core.unit_of_work import UnitOfWork

    async def create(*, role="operador", status="active", renewal=False, email=None):
        """Persist one known account; no public endpoint can bypass first-password renewal."""
        if role != "administrador_tecnico" or status != "active":
            from sqlalchemy import func, select
            async with UnitOfWork(identity_db.sessions) as uow:
                admins = await uow.session.scalar(select(func.count()).select_from(Account).where(
                    Account.role == "administrador_tecnico", Account.status == "active"))
            if not admins:
                await create(role="administrador_tecnico")
        identifier = uuid4()
        email = email or f"person-{identifier.hex}@example.test"
        row = Account(id=identifier, email=email, email_key=email.casefold(), role=role, status=status,
                      password_hash=reference_hash, must_change_password=renewal, auth_version=1, revision=1,
                      created_at=clock.now(), updated_at=clock.now(), password_changed_at=clock.now(),
                      created_by="process:fixture", updated_by="process:fixture")
        async with UnitOfWork(identity_db.sessions) as uow:
            uow.session.add(row)
            await uow.commit()
        return row

    return create


@pytest.fixture
async def client(identity, identity_settings, test_url, tmp_path, clock):
    """Serve the actual composed API in-process with real PostgreSQL and internal-only injection."""
    import httpx
    from pydantic import SecretStr
    from ecs_ec.core.settings import Settings
    from ecs_ec.main import create_app
    (tmp_path / "index.html").write_text("<h1>Synthetic test export</h1>")
    options = Settings(_env_file=None, database_url=SecretStr(test_url), public_url=identity_settings.origin,
                       environment="test", web_directory=tmp_path, identity_enabled=True)
    app = create_app(options, clock=clock, identity_service=identity)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=identity_settings.origin) as transport:
            yield transport


@pytest.fixture
def login(client, identity_settings):
    """Authenticate through the real presession/CSRF API, with no test-only authentication route."""
    async def enter(email, password="Synthetic password 006"):
        """Obtain a fresh/reused preauth and submit ordinary credentials; return the HTTP response."""
        context = await client.get("/api/v1/auth/csrf")
        assert context.status_code == 200
        return await client.post("/api/v1/auth/login", json={"email": email, "password": password},
            headers={"Origin": identity_settings.origin, "X-CSRF-Token": context.json()["csrf_token"]})
    return enter


@pytest.fixture
def identity(identity_db, identity_settings, clock):
    """Compose the real identity service with only internal clock/config injection."""
    from ecs_ec.identity.services import Identity
    return Identity(identity_db, identity_settings, clock, "America/Santiago")


@pytest.fixture
def session_factory(identity_db, identity_settings, clock):
    """Persist independently generated sessions, never an exposed clock/session fixture API."""
    from ecs_ec.identity.models import Session
    from secrets import token_urlsafe
    from hashlib import sha256
    from ecs_ec.core.unit_of_work import UnitOfWork

    async def create(account, mode=None):
        """Return the opaque cookie and trusted principal from a newly committed test session."""
        from ecs_ec.identity.schemas import Principal
        bearer = token_urlsafe(32)
        row = Session(id=uuid4(), token_digest=sha256(bearer.encode()).digest(), account_id=account.id, auth_version=account.auth_version,
                      mode=mode or ("password_change_required" if account.must_change_password else "normal"),
                      created_at=clock.now(), last_activity_at=clock.now(),
                      idle_expires_at=clock.now()+timedelta(minutes=30), absolute_expires_at=clock.now()+timedelta(hours=8),
                      revoked_at=None, revocation_code=None, csrf_key_id=identity_settings.csrf_key_id)
        async with UnitOfWork(identity_db.sessions) as uow:
            uow.session.add(row)
            await uow.commit()
        return bearer, Principal.from_rows(account, row, identity_settings.building_id)

    return create
