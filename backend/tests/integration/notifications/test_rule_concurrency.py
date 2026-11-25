"""008 optimistic concurrency over independent PostgreSQL transactions and actual006 authorization."""

import asyncio
from uuid import UUID, uuid4

from ecs_ec.notifications.models import Attempt, Delivery, RuleVersion
from ecs_ec.notifications.repository import NotificationProblem, prepare_attempt
from sqlalchemy import select


async def test_two_revisions_one_winner_and_original_key_replay(notification_context):
    """One If-Match winner appends one version; replay with its original revision returns its committed result."""
    env = notification_context
    service = env["service"]
    rule = await env["make_rule"]()
    body = rule["config"]
    identifier = UUID(rule["id"])
    keys = [str(uuid4()), str(uuid4())]

    async def change(index):
        """Use an independent service-owned UoW; no process mutex or SQLite arbitration."""
        try:
            return await service.mutate(
                env["principal"],
                "revised",
                body | {"name": f"Revision {index}"},
                keys[index],
                identifier=identifier,
                if_match='"2"',
            )
        except NotificationProblem as error:
            return error

    results = await asyncio.gather(change(0), change(1))
    winners = [(i, r) for i, r in enumerate(results) if isinstance(r, dict)]
    assert (
        len(winners) == 1
        and next(r for r in results if isinstance(r, NotificationProblem)).status == 412
    )
    index, result = winners[0]
    replay = await service.mutate(
        env["principal"],
        "revised",
        body | {"name": f"Revision {index}"},
        keys[index],
        identifier=identifier,
        if_match='"2"',
    )
    assert replay == result
    async with service.database.sessions() as session:
        assert (
            len(
                list(
                    await session.scalars(
                        select(RuleVersion).where(RuleVersion.rule_id == identifier)
                    )
                )
            )
            == 2
        )


async def test_pause_cancels_pending_and_retains_started_attempt(notification_context):
    """The rule lock arbitrates pause/attempt; only work which has not durably begun is canceled."""
    env = notification_context
    service = env["service"]
    rule = await env["make_rule"]()
    pending = await env["pending"](rule)
    begun = await env["pending"](rule)
    capture = await prepare_attempt(service, begun, uuid4())
    paused = await service.mutate(
        env["principal"],
        "paused",
        {},
        str(uuid4()),
        identifier=UUID(rule["id"]),
        if_match='"2"',
    )
    assert paused["status"] == "pausada"
    async with service.database.sessions() as session:
        assert (await session.get(Delivery, pending)).state == "cancelada"
        assert (await session.get(Delivery, begun)).state == "en_intento"
        assert (
            await session.get(Attempt, capture["attempt_id"])
        ).effective_email == env["recipient"].email
