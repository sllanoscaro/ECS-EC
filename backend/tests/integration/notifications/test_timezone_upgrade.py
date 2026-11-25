"""Controlled calendar-rule upgrades preserve already due slots and reconcile only unmaterialized futures."""

from copy import deepcopy
from datetime import timedelta

import pytest
from ecs_ec.notifications import calendar_reconciliation as reconciliation
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import next_occurrences, stamp
from ecs_ec.notifications.scheduler import LEADER_KEY, LeadershipLost, Scheduler
from ecs_ec.notifications.schemas import instant
from sqlalchemy import select, text


async def test_new_rules_reconcile_future_without_rewriting_captures(
    notification_context, monkeypatch
):
    """Changing the controlled rule version updates a future cut exactly once and invalidates old previews."""
    ctx = notification_context
    await ctx["make_rule"]()
    async with ctx["service"].database.sessions() as session:
        original = await session.scalar(select(models.Activation))
        old_due = original.next_due_at

    def shifted(*args, **kwargs):
        """A controlled second calendar implementation shifts the resolved local rules by one hour."""
        result = deepcopy(next_occurrences(*args, **kwargs))
        for slot in result:
            slot["resolved_at"] = stamp(
                instant(slot["resolved_at"]) + timedelta(hours=1)
            )
            slot["window"] = {
                key: stamp(instant(value) + timedelta(hours=1))
                for key, value in slot["window"].items()
            }
        return result

    monkeypatch.setattr(reconciliation, "tzdata_version", lambda: "controlled-v2")
    monkeypatch.setattr(reconciliation, "next_occurrences", shifted)
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        async with ctx["service"].database.sessions() as session:
            current = await session.get(models.Activation, original.id)
            assert (
                current.next_due_at == old_due + timedelta(hours=1)
                and current.tzdata_version == "controlled-v2"
            )
            revision = current.revision
        await reconciliation.reconcile(scheduler)
        async with ctx["service"].database.sessions() as session:
            current = await session.get(models.Activation, original.id)
            assert current.revision == revision
    finally:
        await scheduler.close()


async def test_upgrade_keeps_due_slot_and_lock_loss_stops_scheduler(
    notification_context, monkeypatch
):
    """Overdue work preserves its exact recorded window; releasing the actual session lock stops future materialization."""
    ctx = notification_context
    await ctx["make_rule"]()
    async with ctx["service"].database.sessions() as session:
        original = await session.scalar(select(models.Activation))
        old_slot = deepcopy(original.next_slot)
    ctx["clock"].advance(
        (original.next_due_at - ctx["clock"].now()).total_seconds() + 1
    )
    monkeypatch.setattr(reconciliation, "tzdata_version", lambda: "controlled-v2")
    scheduler = Scheduler(ctx["service"])
    try:
        assert await scheduler.acquire()
        async with ctx["service"].database.sessions() as session:
            current = await session.get(models.Activation, original.id)
            assert current.next_slot == old_slot
        assert await scheduler.tick() == 1
        await scheduler.connection.execute(
            text("SELECT pg_advisory_unlock(:key)"), {"key": LEADER_KEY}
        )
        await scheduler.connection.commit()
        with pytest.raises(LeadershipLost):
            await scheduler.tick()
    finally:
        await scheduler.close()


async def test_interrupted_reconciliation_resumes_per_rule_before_planning(
    notification_context, monkeypatch
):
    """A committed first rule survives interruption; a new leader resumes only unfinished rules before tick is allowed."""
    ctx = notification_context
    await ctx["make_rule"]()
    await ctx["make_rule"]()
    monkeypatch.setattr(reconciliation, "tzdata_version", lambda: "controlled-v2")
    first = Scheduler(ctx["service"])
    original = first.check_leadership
    checks = 0

    async def interrupted():
        """Lose leadership at the second rule, after the first reconciliation has committed."""
        nonlocal checks
        checks += 1
        if checks == 3:
            raise LeadershipLost()
        await original()

    monkeypatch.setattr(first, "check_leadership", interrupted)
    with pytest.raises(LeadershipLost):
        await first.acquire()
    assert not first.reconciled and first.connection is None
    async with ctx["service"].database.sessions() as session:
        rows = list(await session.scalars(select(models.Activation)))
        assert sum(r.tzdata_version == "controlled-v2" for r in rows) == 1
        finished = next(r for r in rows if r.tzdata_version == "controlled-v2")
        revision = finished.revision
    second = Scheduler(ctx["service"])
    try:
        assert await second.acquire()
        async with ctx["service"].database.sessions() as session:
            rows = list(await session.scalars(select(models.Activation)))
            assert all(r.tzdata_version == "controlled-v2" for r in rows)
            assert next(r for r in rows if r.id == finished.id).revision == revision
    finally:
        await second.close()
