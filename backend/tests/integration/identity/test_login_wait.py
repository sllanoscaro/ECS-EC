"""Durable rolling-window throttling is shared by known, inactive and unknown canonical addresses."""


async def test_five_failures_wait_and_exact_expiry(client, login, account_factory, clock):
    """Fifth failure starts fifteen minutes; blocked attempts cannot authenticate or extend the wait."""
    account = await account_factory()
    for expected in [401, 401, 401, 401, 429]:
        response = await login(account.email, "Incorrect synthetic password")
        assert response.status_code == expected, response.text
    assert response.headers["retry-after"] == "900"
    clock.advance(60)
    response = await login(account.email)
    assert response.status_code == 429 and response.headers["retry-after"] == "840"
    clock.advance(840)
    assert (await login(account.email)).status_code == 200


async def test_unknown_inactive_and_bad_password_equivalent(client, login, account_factory):
    """All credential rejection categories share the exact safe code/detail without account disclosure."""
    inactive = await account_factory(status="inactive")
    active = await account_factory()
    results = [await login(inactive.email), await login(active.email, "Incorrect synthetic password"),
               await login("unknown@example.test")]
    assert all(result.status_code == 401 for result in results)
    assert len({(result.json()["code"], result.json()["detail"]) for result in results}) == 1


async def test_parallel_failures_presession_and_hash_revalidation(identity, identity_db, account_factory, session_factory, identity_settings):
    """Concurrent failures share a durable bucket; password reset during Argon2 cannot authenticate an old hash."""
    import asyncio
    import pytest
    from ecs_ec.identity.security import preauth_context
    from ecs_ec.identity.errors import IdentityProblem

    admin = await account_factory(role="administrador_tecnico")
    target = await account_factory()
    _, actor = await session_factory(admin)
    contexts = [(await preauth_context(identity, None))[0] for _ in range(6)]
    results = await asyncio.gather(*(identity.login(target.email, "Incorrect synthetic password", token, "127.0.0.2") for token in contexts), return_exceptions=True)
    assert sum(isinstance(result, IdentityProblem) and result.status == 401 for result in results) == 4
    assert sum(isinstance(result, IdentityProblem) and result.status == 429 for result in results) == 2
    context = (await preauth_context(identity, None))[0]
    original = identity.credentials.verify
    started, release = asyncio.Event(), asyncio.Event()

    async def held_verify(password, encoded):
        """Pause a real Argon2 verification after the private snapshot, without holding a DB transaction."""
        started.set()
        await release.wait()
        return await original(password, encoded)

    identity.credentials.verify = held_verify
    task = asyncio.create_task(identity.login(target.email, "Synthetic password 006", context, "127.0.0.1"))
    await started.wait()
    await identity.reset_account(actor, target.id, "Reset synthetic password 006", 1)
    release.set()
    with pytest.raises(IdentityProblem) as failure:
        await task
    assert failure.value.code == "invalid_credentials"
    identity.credentials.verify = original


async def test_one_preauth_consumed_once(identity, account_factory):
    """Two valid concurrent logins cannot turn the same preauth into two independent sessions."""
    import asyncio
    from ecs_ec.identity.security import preauth_context
    from ecs_ec.identity.errors import IdentityProblem
    target = await account_factory()
    context = (await preauth_context(identity, None))[0]
    results = await asyncio.gather(*(identity.login(target.email, "Synthetic password 006", context, "127.0.0.1") for _ in range(2)), return_exceptions=True)
    assert sum(isinstance(result, tuple) for result in results) == 1
    assert sum(isinstance(result, IdentityProblem) and result.code == "csrf_invalid" for result in results) == 1
