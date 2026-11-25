"""008 real participant tests: pre-attempt account mutations cancel only pending work and retain begun attempts."""

import pytest
from ecs_ec.identity.coordination import ParticipantRegistry
from ecs_ec.notifications.identity_coordination import NotificationParticipant


def test_participant_protocol_is_complete():
    """006 accepts008's actual asynchronous participant and freezes its disjoint lock ranges."""
    registry = ParticipantRegistry()
    participant = NotificationParticipant()
    registry.register(participant)
    assert registry.freeze() == (participant,)
    with pytest.raises(ValueError):
        registry.register(NotificationParticipant())


@pytest.mark.parametrize("started", [False, True])
async def test_real_account_revocation_on_both_sides_of_durable_start(
    notification_context, started
):
    """Actual006 commits cancel two pending rules; attempts committed first retain their original effective address/history."""
    from uuid import uuid4

    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.models import Attempt, Delivery
    from ecs_ec.notifications.repository import prepare_attempt

    env = notification_context
    service = env["service"]
    recipient = env["recipient"]
    identifiers = []
    for _ in range(2):
        identifiers.append(await env["pending"](await env["make_rule"]()))
    before = []
    if started:
        for identifier in identifiers:
            before.append(await prepare_attempt(service, identifier, uuid4()))
        assert all(before)
    await service.identity.update_account(
        env["principal"],
        recipient.id,
        AccountUpdate(email=recipient.email, role="operador", status="inactive"),
        recipient.revision,
    )
    async with service.database.sessions() as session:
        for identifier in identifiers:
            delivery = await session.get(Delivery, identifier)
            assert delivery.state == ("en_intento" if started else "cancelada")
        for capture in before:
            attempt = await session.get(Attempt, capture["attempt_id"])
            assert (
                attempt.effective_email == recipient.email
                and attempt.finished_at is None
            )
    if not started:
        assert all(
            result is None
            for result in [
                await prepare_attempt(service, identifier, uuid4())
                for identifier in identifiers
            ]
        )


async def test_email_changes_are_resolved_at_each_actual_start(notification_context):
    """Account UUID stays stable; pending delivery stores no address and a begun attempt preserves the previous one."""
    from uuid import uuid4

    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.repository import prepare_attempt

    env = notification_context
    service = env["service"]
    recipient = env["recipient"]
    first = await env["pending"](await env["make_rule"]())
    second = await env["pending"](await env["make_rule"]())
    old = await prepare_attempt(service, first, uuid4())
    await service.identity.update_account(
        env["principal"],
        recipient.id,
        AccountUpdate(
            email="changed008@example.test", role="operador", status="active"
        ),
        recipient.revision,
    )
    new = await prepare_attempt(service, second, uuid4())
    assert (
        old["effective_email"] == recipient.email
        and new["effective_email"] == "changed008@example.test"
    )


async def test_role_downgrade_cancels_audit_content_across_rules(
    notification_context, account_factory
):
    """006 role mutation atomically cancels administrative content while retaining begun effective-address history."""
    from uuid import uuid4

    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.models import Delivery
    from ecs_ec.notifications.repository import prepare_attempt

    ctx = notification_context
    recipient = await account_factory(role="administrador_tecnico")
    ids = [
        await ctx["pending"](
            await ctx["make_rule"](
                contents=["cambios_administrativos"], recipient_id=recipient.id
            )
        )
        for _ in range(2)
    ]
    assert await prepare_attempt(ctx["service"], ids[0], uuid4())
    await ctx["service"].identity.update_account(
        ctx["principal"],
        recipient.id,
        AccountUpdate(email=recipient.email, role="operador", status="active"),
        recipient.revision,
    )
    async with ctx["service"].database.sessions() as session:
        assert (await session.get(Delivery, ids[0])).state == "en_intento"
        assert (await session.get(Delivery, ids[1])).state == "cancelada"


async def test_new_rule_between_discovery_and_account_lock_forces_redetection(
    notification_context, monkeypatch
):
    """A real new recipient reference commits during006 discovery; its transaction retries before touching accounts/deliveries."""
    import asyncio

    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.models import Delivery

    env = notification_context
    service = env["service"]
    recipient = env["recipient"]
    await env["pending"](await env["make_rule"]())
    participant = next(
        p
        for p in service.identity.participants.freeze()
        if p.name == "notifications008"
    )
    original = participant.discover
    discovered = asyncio.Event()
    resume = asyncio.Event()
    calls = 0

    async def paused_discovery(mutation, uow):
        """Pause only the first internal discovery while another real API request commits its new reference."""
        nonlocal calls
        result = await original(mutation, uow)
        calls += 1
        if calls == 1:
            discovered.set()
            await resume.wait()
        return result

    monkeypatch.setattr(participant, "discover", paused_discovery)
    mutation = asyncio.create_task(
        service.identity.update_account(
            env["principal"],
            recipient.id,
            AccountUpdate(email=recipient.email, role="operador", status="inactive"),
            recipient.revision,
        )
    )
    try:
        await asyncio.wait_for(discovered.wait(), 5)
        new = await env["pending"](await env["make_rule"]())
    finally:
        resume.set()
    await asyncio.wait_for(mutation, 5)
    async with service.database.sessions() as session:
        assert (await session.get(Delivery, new)).state == "cancelada"
    assert calls >= 3  # Initial discovery, unstable redetection and fresh retry.


@pytest.mark.parametrize("repeat", range(3))
async def test_concurrent_revocation_and_durable_start_are_serialized(
    notification_context, repeat
):
    """Independent PostgreSQL transactions racing on the same rule yield cancellation or a fully recorded begun attempt, never deadlock."""
    import asyncio
    from uuid import uuid4

    from ecs_ec.identity.schemas import AccountUpdate
    from ecs_ec.notifications.models import Attempt, Delivery
    from ecs_ec.notifications.repository import prepare_attempt

    env = notification_context
    service = env["service"]
    recipient = env["recipient"]
    identifier = await env["pending"](await env["make_rule"]())
    capture, _ = await asyncio.wait_for(
        asyncio.gather(
            prepare_attempt(service, identifier, uuid4()),
            service.identity.update_account(
                env["principal"],
                recipient.id,
                AccountUpdate(
                    email=recipient.email, role="operador", status="inactive"
                ),
                recipient.revision,
            ),
        ),
        5,
    )
    async with service.database.sessions() as session:
        delivery = await session.get(Delivery, identifier)
        assert delivery.state == ("en_intento" if capture else "cancelada")
        if capture:
            assert (
                await session.get(Attempt, capture["attempt_id"])
            ).effective_email == recipient.email
