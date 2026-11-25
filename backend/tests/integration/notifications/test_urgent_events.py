"""Real reception windows and source state drive durable episodes without duplicating notifications."""

from datetime import timedelta

from ecs_ec.notifications import models
from ecs_ec.notifications.episodes import Evaluator
from sqlalchemy import func, select

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.unit.consumption.test_validation import record


async def test_persistent_consumption_opens_once_and_valid_normal_rearms(
    notification_context, history_environment
):
    """Complete2kWh exceeds1; replay stays one episode; a later valid low reading closes before a new high reopens."""
    ctx = notification_context
    start = ctx["clock"].now()
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
    engine = Evaluator(ctx["service"])
    await publish(history_environment, [record(value="2")])
    ctx["clock"].advance(3600)
    assert await engine.tick() == 1
    assert await engine.tick() == 0
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )
        assert (
            await session.scalar(select(func.count()).select_from(models.Delivery)) == 1
        )
    await publish(
        history_environment,
        [
            record(
                start=start + timedelta(hours=1),
                end=start + timedelta(hours=2),
                value="0.5",
                source_evidence_ref="synthetic:normal",
            )
        ],
    )
    ctx["clock"].advance(3600)
    assert await engine.tick() == 1
    async with ctx["service"].database.sessions() as session:
        assert (await session.scalar(select(models.Episode))).status == "cerrado"
    await publish(
        history_environment,
        [
            record(
                start=start + timedelta(hours=2),
                end=start + timedelta(hours=3),
                value="2",
                source_evidence_ref="synthetic:high",
            )
        ],
    )
    ctx["clock"].advance(3600)
    assert await engine.tick() == 1
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 2
        )
        assert (
            await session.scalar(select(func.count()).select_from(models.Delivery)) == 2
        )


async def test_absence_runs_by_clock_and_no_source_never_opens(
    notification_context, consumption_reception_environment
):
    """An actual configured source becomes silent after15minutes; a category without source remains unevaluable."""
    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(
                kind="ausencia_datos", category_id="CAT-05", silence_minutes=15
            ),
        )
    )
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(
                kind="ausencia_datos", category_id="CAT-07", silence_minutes=15
            ),
        )
    )
    engine = Evaluator(ctx["service"])
    await engine.tick()
    ctx["clock"].advance(899)
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 0
        )
    ctx["clock"].advance(1)
    await engine.tick()
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )


async def test_calculated_total_keeps_real_basis_and_exact_value(
    notification_context, consumption_reception_environment
):
    """The actual002 computed20kWh total opens one CAT01 episode withCAT03/CAT05 provenance and no008 arithmetic."""
    from uuid import UUID

    ctx = notification_context
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
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        message = await session.scalar(select(models.Message))
        evidence = message.functional_content["evidence"][0]
        assert evidence["value_kwh"] == "20" and evidence["origin"] == "calculado"
        episode = await session.scalar(select(models.Episode))
        stored = await session.get(models.Evidence, episode.opening_evidence_id)
        assert (
            stored.limitation_code is None and stored.payload["limitation_code"] is None
        )
        assert (
            set(evidence["basis_categories"]) == {"CAT-03", "CAT-05"}
            and evidence["source_refs"]
        )
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )


async def test_historical_batch_records_omission_without_alerting_each_window(
    notification_context, history_environment, session_factory, identity_settings
):
    """Late preactivation readings remain functional history without an alert per archived window."""
    from ecs_ec.identity.security import csrf

    ctx = notification_context
    start = ctx["clock"].now()
    ctx["clock"].advance(7200)
    bearer, _ = await session_factory(ctx["admin"])
    ctx["client"].cookies.set("ecs_ec_session", bearer)
    ctx["headers"]["X-CSRF-Token"] = csrf(identity_settings, "session", bearer)
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
    await publish(
        history_environment,
        [record(start=start, end=start + timedelta(hours=1), value="2")],
    )
    evaluator = Evaluator(ctx["service"])
    await evaluator.tick()
    await evaluator.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Delivery)) == 0
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(models.Evaluation)
                .where(models.Evaluation.result == "omitida_historica")
            )
            == 1
        )


async def test_duplicate_and_rejected_receptions_do_not_reset_silence(
    notification_context, history_environment
):
    """Only an actual new accepted record closes absence; duplicate/rejected attempts preserve its original15minute baseline."""
    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(
                kind="ausencia_datos", category_id="CAT-05", silence_minutes=15
            ),
        )
    )
    engine = Evaluator(ctx["service"])
    ctx["clock"].advance(900)
    await engine.tick()
    reading = record(value="2")
    await publish(history_environment, [reading])
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        assert (await session.scalar(select(models.Episode))).status == "cerrado"
    ctx["clock"].advance(899)
    await publish(
        history_environment,
        [reading, record(value="-1", source_evidence_ref="synthetic:rejected")],
    )
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )
    ctx["clock"].advance(1)
    await engine.tick()
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 2
        )


async def test_complete_mixed_origin_window_keeps_actual_owner_total(
    notification_context, history_environment
):
    """A valid hour of physical10 plus owner-calculated10 remains an evaluable20, with its mixed scope explicitly identified."""
    from uuid import UUID

    from ecs_ec.consumption.configuration import ConfigurationService
    from ecs_ec.consumption.store import MeasurementStore
    from ecs_ec.core.unit_of_work import UnitOfWork

    from backend.tests.unit.consumption.test_catalog import installation

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
    await publish(
        history_environment,
        [
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                start=start,
                end=start + timedelta(minutes=30),
                value="10",
            )
        ],
    )
    ctx["clock"].advance(1800)
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        await ConfigurationService(ctx["clock"], MeasurementStore()).apply(
            uow,
            building_id=UUID(int=99),
            request=installation().model_copy(
                update={"expected_revision": 1, "effective_from": ctx["clock"].now()}
            ),
            actor_ref="process:history_test",
        )
        await uow.commit()
    await publish(
        history_environment,
        [
            record(
                start=start + timedelta(minutes=30),
                end=start + timedelta(hours=1),
                value="5",
            ),
            record(
                start=start + timedelta(minutes=30),
                end=start + timedelta(hours=1),
                value="5",
                category_id="CAT-03",
                source_id=UUID(int=3),
            ),
        ],
    )
    ctx["clock"].advance(1800)
    await Evaluator(ctx["service"]).tick()
    async with ctx["service"].database.sessions() as session:
        message = await session.scalar(select(models.Message))
        assert message is not None
        evidence = message.functional_content["evidence"][0]
        assert (
            evidence["value_kwh"] == "20"
            and "tramos medidos y calculados" in evidence["scope_description"]
        )
