"""Exact idle/absolute boundaries, background polling, independent logout and trusted activity."""

import pytest

from ecs_ec.identity.errors import IdentityProblem


async def test_interactive_activity_and_absolute_limit(identity, account_factory, session_factory, clock):
    """Minute29 interactive reaches59, polling does not renew, and absolute eight hours never move."""
    account = await account_factory()
    cookie, principal = await session_factory(account)
    clock.advance(29 * 60)
    current = await identity.resolve_session(cookie, activity="interactive", action="consumption.read")
    assert (current.idle_expires_at - clock.now()).total_seconds() == 1800
    clock.advance(30 * 60)
    with pytest.raises(IdentityProblem) as failure:
        await identity.resolve_session(cookie, activity="interactive", action="consumption.read")
    assert failure.value.status == 401


async def test_introspection_never_renews(client, login, account_factory, clock):
    """Repeated session introspection, even marked interactive, expires exactly at minute30."""
    account = await account_factory()
    assert (await login(account.email)).status_code == 200
    clock.advance(29 * 60)
    assert (await client.get("/api/v1/auth/session", headers={"X-Session-Activity": "interactive"})).status_code == 200
    clock.advance(60)
    assert (await client.get("/api/v1/auth/session")).status_code == 401


async def test_continuous_activity_never_passes_eight_hours(identity, account_factory, session_factory, clock):
    """Repeated authorized activity moves idle deadlines but never the immutable absolute boundary."""
    account = await account_factory()
    cookie, first = await session_factory(account)
    for _ in range(16):
        clock.advance(29*60)
        current = await identity.resolve_session(cookie, activity="interactive", action="consumption.read")
        assert current.absolute_expires_at == first.absolute_expires_at
    clock.advance(16*60)
    with pytest.raises(IdentityProblem):
        await identity.resolve_session(cookie, activity="interactive", action="consumption.read")
