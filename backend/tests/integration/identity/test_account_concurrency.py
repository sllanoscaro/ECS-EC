"""Independent PostgreSQL connections exercise last-admin, canonical uniqueness and original-session races."""

import asyncio

import pytest
from sqlalchemy import func, select, text

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account, Guard
from ecs_ec.identity.schemas import AccountCreate, AccountUpdate


async def wait_for_guard(database, minimum=1):
    """Observe an actual PostgreSQL lock wait, avoiding a timing-only sequential test."""
    for _ in range(200):
        async with database.engine.connect() as connection:
            count = await connection.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND query ILIKE '%identity_guard%'"))
        if count >= minimum:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Expected an independent connection waiting on the guard")


async def test_two_admins_retire_concurrently(identity, identity_db, account_factory, session_factory):
    """Two overlapping self-demotions leave exactly one active administrator after durable commits."""
    a, b = await account_factory(role="administrador_tecnico"), await account_factory(role="administrador_tecnico")
    _, pa = await session_factory(a)
    _, pb = await session_factory(b)
    results = await asyncio.gather(*(identity.update_account(principal, row.id,
        AccountUpdate(email=row.email, role="operador", status="active"), 1) for row, principal in ((a, pa), (b, pb))), return_exceptions=True)
    assert sum(isinstance(row, IdentityProblem) and row.code == "last_active_administrator" for row in results) == 1
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Account).where(Account.role == "administrador_tecnico", Account.status == "active")) == 1


async def test_canonical_creation_concurrently(identity, account_factory, session_factory):
    """Equivalent emails race through hashes/guard and PostgreSQL's unique index; one succeeds."""
    admin = await account_factory(role="administrador_tecnico")
    _, principal = await session_factory(admin)
    results = await asyncio.gather(*(identity.create_account(principal, AccountCreate(email=email, role="operador", status="active",
        initial_password="Synthetic initial password")) for email in ("new@example.test", " NEW@EXAMPLE.TEST ")), return_exceptions=True)
    assert sum(isinstance(row, Account) for row in results) == 1
    assert sum(isinstance(row, IdentityProblem) and row.code == "email_conflict" for row in results) == 1


@pytest.mark.parametrize("interruption", ["logout", "expiry"])
async def test_original_session_rechecked_after_guard(identity, identity_db, account_factory, session_factory, clock, interruption):
    """A real guard wait followed by logout/expiry cannot confirm a mutation using the original principal."""
    from ecs_ec.identity.sessions import logout
    admin = await account_factory(role="administrador_tecnico")
    target = await account_factory()
    _, principal = await session_factory(admin)
    async with UnitOfWork(identity_db.sessions) as holder:
        await holder.session.scalar(select(Guard).where(Guard.id == 1).with_for_update())
        task = asyncio.create_task(identity.update_account(principal, target.id,
            AccountUpdate(email=target.email, role=target.role, status="inactive"), 1))
        await wait_for_guard(identity_db)
        if interruption == "logout":
            await logout(identity, principal)
        else:
            clock.advance(1800)
        await holder.commit()
    with pytest.raises(IdentityProblem) as failure:
        await task
    assert failure.value.status == 401
    async with UnitOfWork(identity_db.sessions) as uow:
        row = await uow.session.get(Account, target.id)
        assert row.status == "active" and row.revision == 1


async def test_actor_loses_role_before_second_guard_acquisition(identity, identity_db, account_factory, session_factory):
    """Two queued real mutations revoke the second actor before it can authorize under locks."""
    a, b = await account_factory(role="administrador_tecnico"), await account_factory(role="administrador_tecnico")
    target = await account_factory()
    _, actor_a = await session_factory(a)
    _, actor_b = await session_factory(b)
    async with UnitOfWork(identity_db.sessions) as holder:
        await holder.session.scalar(select(Guard).where(Guard.id == 1).with_for_update())
        retire = asyncio.create_task(identity.update_account(actor_b, a.id, AccountUpdate(email=a.email, role="operador", status="active"), 1))
        await wait_for_guard(identity_db)
        edit = asyncio.create_task(identity.update_account(actor_a, target.id, AccountUpdate(email=target.email, role=target.role, status="inactive"), 1))
        await wait_for_guard(identity_db, 2)
        await holder.commit()
    assert (await retire).role == "operador"
    with pytest.raises(IdentityProblem) as failure:
        await edit
    assert failure.value.status == 401


@pytest.mark.parametrize("change", ["email", "role", "inactive", "reset", "reactivate"])
async def test_every_account_change_revokes_two_devices(identity, account_factory, session_factory, change):
    """Every effective account edit/reset invalidates both devices and recipient state reflects current revision."""
    admin = await account_factory(role="administrador_tecnico")
    target = await account_factory(status="inactive" if change == "reactivate" else "active")
    _, actor = await session_factory(admin)
    cookies = [(await session_factory(target))[0] for _ in range(2)]
    if change == "reset":
        row = await identity.reset_account(actor, target.id, "New synthetic password 006", 1)
    else:
        command = AccountUpdate(email="changed@example.test" if change == "email" else target.email,
            role="administrador_tecnico" if change == "role" else target.role,
            status="inactive" if change == "inactive" else "active")
        row = await identity.update_account(actor, target.id, command, 1)
    assert row.auth_version == 2 and row.revision == 2
    for cookie in cookies:
        with pytest.raises(IdentityProblem) as failure:
            await identity.resolve_session(cookie)
        assert failure.value.status == 401
    recipient = await identity.resolve_recipient(target.id, {"consumption.read"})
    assert recipient.auth_version == 2 and recipient.email == row.email
