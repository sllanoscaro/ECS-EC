"""Approved mixed real-clock profile uses two periodic and two actual consumption conditions for ten accounts."""

import asyncio
import json
import os
import platform
import resource
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from ecs_ec.core.clock import SystemClock
from ecs_ec.identity.security import csrf
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.episodes import Evaluator
from ecs_ec.notifications.lifecycle import Runner
from ecs_ec.notifications.scheduler import Scheduler
from ecs_ec.notifications.settings import NotificationSettings
from sqlalchemy import func, select

from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.contract.notifications.test_rules_api import config
from backend.tests.unit.consumption.test_validation import record


@pytest.mark.parametrize(
    "supervised", [False, True], ids=["fairness-materialized", "supervised-clock"]
)
async def test_mixed_forty_deliveries_real_clock(
    notification_context,
    history_environment,
    account_factory,
    session_factory,
    identity_settings,
    supervised,
):
    """Real timing begins at a shared cut; source normalization, captures, claim and local SMTP are actual implementations."""
    if os.environ.get("NOTIFICATION_TEST_SMTP") != "1":
        pytest.skip("Exclusive local Mailpit required")
    ctx = notification_context
    clock = SystemClock()
    ctx["clock"].advance((clock.now() - ctx["clock"].now()).total_seconds())
    bearer, _ = await session_factory(ctx["admin"])
    ctx["client"].cookies.set("ecs_ec_session", bearer)
    ctx["headers"]["X-CSRF-Token"] = csrf(identity_settings, "session", bearer)
    accounts = [await account_factory() for _ in range(10)]
    due = clock.now() + timedelta(seconds=3)
    for index in range(4):
        body = config(
            accounts[0].id,
            name="Perfil mixto " + str(index),
            recipient_ids=[str(a.id) for a in accounts],
        )
        if index < 2:
            body["schedule"] = dict(
                kind="intervalo",
                interval_value=1,
                interval_unit="minutos",
                starts_at=stamp(due),
            )
        else:
            body.pop("schedule")
            body.pop("content_types")
            body.update(
                mode="urgente",
                condition=dict(
                    kind="consumo",
                    category_id="CAT-03" if index == 2 else "CAT-05",
                    unit="kWh",
                    window=dict(kind="intervalo", measurement_interval_seconds=1),
                    comparison="gt",
                    threshold_kwh="1",
                ),
            )
        response = await ctx["client"].post(
            "/api/v1/notifications/rules",
            json=body,
            headers=ctx["headers"] | {"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201, response.text
        preview = (
            await ctx["client"].post(
                "/api/v1/notifications/rules/preview", json=body, headers=ctx["headers"]
            )
        ).json()
        active = await ctx["client"].post(
            "/api/v1/notifications/rules/" + response.json()["id"] + "/activate",
            json={"preview_token": preview["preview_token"]},
            headers=ctx["headers"]
            | {"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
        )
        assert active.status_code == 200, active.text
    await publish(
        history_environment,
        [
            record(
                category_id=category,
                source_id=UUID(int=number),
                start=due - timedelta(seconds=1),
                end=due,
                value="2",
                source_evidence_ref="synthetic:mixed:" + category,
            )
            for category, number in [("CAT-03", 3), ("CAT-05", 5)]
        ],
    )
    ctx["service"].clock = clock
    ctx["service"].settings = NotificationSettings(
        _env_file=None,
        environment="test",
        smtp_host="127.0.0.1",
        smtp_port=11025,
        notification_slots=4,
    )
    scheduler = Scheduler(ctx["service"])
    dispatcher = Dispatcher(ctx["service"])
    evaluator = Evaluator(ctx["service"])
    started = clock.monotonic()
    before_cpu = __import__("time").process_time()
    runner = None
    try:
        async with ctx["service"].database.sessions() as session:
            assert (
                await session.scalar(select(func.count()).select_from(models.Delivery))
                == 0
            )
        if supervised:
            runner = Runner(ctx["service"])
            runner.start()
            async with asyncio.timeout(59):
                while True:
                    async with ctx["service"].database.sessions() as session:
                        completed = await session.scalar(
                            select(func.count())
                            .select_from(models.Attempt)
                            .where(models.Attempt.outcome == "aceptada")
                        )
                    if completed == 40:
                        break
                    await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(max(0, (due - clock.now()).total_seconds()))
            assert await scheduler.acquire()
            assert await scheduler.tick() == 2
            assert await evaluator.tick() == 2
            async with ctx["service"].database.sessions() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(models.Delivery)
                    )
                    == 40
                )
            async with asyncio.timeout(55):
                while await dispatcher.dispatch_once():
                    pass
        async with ctx["service"].database.sessions() as session:
            rows = list(
                await session.execute(
                    select(models.Attempt, models.Occurrence)
                    .join(
                        models.Delivery,
                        models.Delivery.id == models.Attempt.delivery_id,
                    )
                    .join(
                        models.Message, models.Message.id == models.Delivery.message_id
                    )
                    .join(
                        models.Occurrence,
                        models.Occurrence.id == models.Message.occurrence_id,
                    )
                    .order_by(models.Attempt.started_at, models.Attempt.id)
                )
            )
        assert len(rows) == 40 and all(
            a.outcome == "aceptada" and a.attempt_number == 1 for a, o in rows
        )
        delays = [
            (
                a.started_at
                - (o.detected_at if o.kind == "urgente" else o.scheduled_at)
            ).total_seconds()
            for a, o in rows
        ]
        durations = [(a.finished_at - a.started_at).total_seconds() for a, o in rows]
        assert min(delays) >= 0 and max(delays) <= 60 and max(durations) <= 1
        if not supervised:
            assert [o.kind for a, o in rows[:4]].count("urgente") == 3
        result = dict(
            profile="mixed40_supervised" if supervised else "mixed40_fairness",
            supervised=supervised,
            recipients=10,
            periodic_rules=2,
            urgent_rules=2,
            deliveries=40,
            accepted=40,
            slots=4,
            max_start_seconds=max(delays),
            max_attempt_seconds=max(durations),
            first_wave=[o.kind for a, o in rows[:4]],
            elapsed_seconds=clock.monotonic() - started,
            cpu_seconds=__import__("time").process_time() - before_cpu,
            max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            host_logical_cpus=os.cpu_count(),
            python=platform.python_version(),
            tzdata=version("tzdata"),
            source="synthetic1second intervals normalized by real002; runtime uses SystemClock",
            references=[
                dict(
                    delivery_id=str(a.delivery_id),
                    scheduled_at=stamp(o.scheduled_at) if o.scheduled_at else None,
                    detected_at=stamp(o.detected_at) if o.detected_at else None,
                    started_at=stamp(a.started_at),
                    finished_at=stamp(a.finished_at),
                )
                for a, o in rows
            ],
        )
        artifact = os.environ.get("NOTIFICATION_MIXED_ARTIFACT")
        if artifact:
            Path(artifact if supervised else artifact + ".fairness.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
        print(
            "mixed40:40/40 accepted;max_start_seconds="
            + str(max(delays))
            + ";max_attempt_seconds="
            + str(max(durations))
        )
    finally:
        if runner:
            await runner.close()
        await dispatcher.close()
        await scheduler.close()
