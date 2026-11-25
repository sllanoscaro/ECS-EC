"""Independent real PostgreSQL consumers serialize snapshots before deciding episode transitions."""

import asyncio

from ecs_ec.notifications import models
from ecs_ec.notifications.episodes import Evaluator
from sqlalchemy import func, select

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record


async def test_eight_consumers_create_one_episode_occurrence_delivery(
    notification_context, history_environment
):
    """Waiting consumers take a fresh snapshot after exclusion, preserving a single logical condition opening."""
    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(
                kind="consumo",
                category_id="CAT-05",
                unit="kWh",
                window=dict(kind="hora"),
                comparison="gt",
                threshold_kwh="1",
            ),
        )
    )
    await publish(history_environment, [record(value="2")])
    ctx["clock"].advance(3600)
    await asyncio.wait_for(
        asyncio.gather(*(Evaluator(ctx["service"]).tick() for _ in range(8))), 10
    )
    async with ctx["service"].database.sessions() as session:
        for cls in (models.Episode, models.Occurrence, models.Message, models.Delivery):
            assert await session.scalar(select(func.count()).select_from(cls)) == 1


async def test_missing_calculated_contribution_never_normalizes(
    notification_context, consumption_reception_environment
):
    """A missing physical contribution cannot produce a zero or a closing episode for the calculatedCAT01 total."""
    from datetime import timedelta
    from uuid import UUID

    ctx = notification_context
    start = ctx["clock"].now()
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(
                kind="consumo",
                category_id="CAT-01",
                unit="kWh",
                window=dict(kind="hora"),
                comparison="gt",
                threshold_kwh="15",
            ),
        )
    )
    await consumption_reception_environment.publish(
        [
            record(value="12"),
            record(category_id="CAT-03", source_id=UUID(int=3), value="8"),
        ]
    )
    ctx["clock"].advance(3600)
    engine = Evaluator(ctx["service"])
    await engine.tick()
    await consumption_reception_environment.publish(
        [
            record(
                start=start + timedelta(hours=1),
                end=start + timedelta(hours=2),
                value="12",
            )
        ]
    )
    ctx["clock"].advance(3600)
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        episode = await session.scalar(select(models.Episode))
        assert episode.status == "abierto" and episode.closing_evidence_id is None
        assert (
            await session.scalar(select(func.count()).select_from(models.Delivery)) == 1
        )
