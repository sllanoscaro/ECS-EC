"""Bounded technical cleanup and key rotation cannot destroy accounts/history or erase an active login wait."""

from pydantic import SecretStr
from datetime import timedelta
import pytest
from sqlalchemy import func, select

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.maintenance import maintain, validate_rotation
from ecs_ec.identity.models import Account, LoginBucket, Session
from ecs_ec.identity.security import preauth_context
from ecs_ec.identity.services import Identity
from ecs_ec.identity.sessions import bucket_key


async def test_expired_state_after_twenty_four_hours(identity, identity_db, account_factory, session_factory, clock):
    """Expiry works before cleanup; cleanup later removes technical rows but retains accounts and guard."""
    account = await account_factory()
    cookie, principal = await session_factory(account)
    await preauth_context(identity, None)
    clock.advance(1800)
    with pytest.raises(IdentityProblem):
        await identity.resolve_session(cookie)
    assert (await maintain(identity))["sessions"] == 0
    clock.advance(24*3600)
    result = await maintain(identity)
    assert result["sessions"] == 1 and result["preauth"] == 1
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.get(Account, account.id) is not None
        assert await uow.session.get(Session, principal.session_id) is None


async def test_rotation_preserves_active_wait(identity, identity_db, identity_settings, account_factory, clock):
    """A blocked request migrates old HMAC state without Argon2 or extending its fifteen-minute wait."""
    account = await account_factory()
    context = (await preauth_context(identity, None))[0]
    for _ in range(5):
        with pytest.raises(IdentityProblem):
            await identity.login(account.email, "Wrong synthetic password", context, "127.0.0.1")
    new_settings = identity_settings.model_copy(update={"login_bucket_key": SecretStr("c"*43), "login_bucket_key_id": "bucket-v2",
        "previous_login_bucket_key": identity_settings.login_bucket_key, "previous_login_bucket_key_id": identity_settings.login_bucket_key_id})
    rotated = Identity(identity_db, new_settings, clock, "UTC")
    with pytest.raises(IdentityProblem) as failure:
        await rotated.login(account.email, "Synthetic password 006", context, "127.0.0.1")
    assert failure.value.status == 429 and failure.value.retry_after == 900
    expected = bucket_key(new_settings.login_bucket_key, account.email_key, "127.0.0.1")
    async with UnitOfWork(identity_db.sessions) as uow:
        row = await uow.session.get(LoginBucket, expected)
        assert row is not None and row.blocked_until == clock.now()+timedelta(minutes=15)
        assert await uow.session.scalar(select(func.count()).select_from(LoginBucket)) == 1
    clock.advance(900)
    context = (await preauth_context(rotated, None))[0]
    assert (await rotated.login(account.email, "Synthetic password 006", context, "127.0.0.1"))


async def test_retired_csrf_key_requires_login(identity, identity_db, identity_settings, account_factory, session_factory, clock):
    """An old CSRF key ID cannot keep a session valid, independently of whether cleanup has run."""
    account = await account_factory()
    cookie, _ = await session_factory(account)
    rotated = Identity(identity_db, identity_settings.model_copy(update={"csrf_key": SecretStr("d"*43), "csrf_key_id": "csrf-v2"}), clock, "UTC")
    with pytest.raises(IdentityProblem) as failure:
        await rotated.resolve_session(cookie)
    assert failure.value.status == 401


async def test_bucket_key_cannot_be_retired_during_recent_wait(identity, identity_db, identity_settings, account_factory, clock):
    """Missing old key fails closed for active/recent bucket state, with at least a thirty-minute overlap."""
    account = await account_factory()
    context = (await preauth_context(identity, None))[0]
    for _ in range(5):
        with pytest.raises(IdentityProblem):
            await identity.login(account.email, "Wrong synthetic password", context, "127.0.0.1")
    replacement = Identity(identity_db, identity_settings.model_copy(update={"login_bucket_key": SecretStr("c"*43), "login_bucket_key_id": "bucket-v2"}), clock, "UTC")
    for advance in (0, 900):
        clock.advance(advance)
        with pytest.raises(IdentityProblem):
            await validate_rotation(replacement)
    clock.advance(900)
    await validate_rotation(replacement)
