"""Real-clock partial profile: two periodic rules, ten accounts, twenty first attempts and four local SMTP slots."""

import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import pytest
from ecs_ec.core.clock import SystemClock
from ecs_ec.notifications import models
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.lifecycle import Runner
from ecs_ec.notifications.settings import NotificationSettings
from sqlalchemy import select

from backend.tests.contract.notifications.test_rules_api import config


async def test_twenty_periodic_deliveries_real_clock(
    notification_context, account_factory
):
    """This partial profile verifies US2 only; the forty-delivery urgent mix remains a separate SC003 gate."""
    if os.environ.get("NOTIFICATION_TEST_SMTP") != "1":
        pytest.skip("Exclusive local Mailpit required")
    ctx = notification_context
    clock = SystemClock()
    accounts = [await account_factory() for _ in range(10)]
    due = clock.now() + timedelta(seconds=3)
    for index in range(2):
        body = config(
            accounts[0].id,
            name="Perfil periódico " + str(index),
            recipient_ids=[str(a.id) for a in accounts],
            schedule=dict(
                kind="intervalo",
                interval_value=1,
                interval_unit="minutos",
                starts_at=stamp(due),
            ),
        )
        response = await ctx["client"].post(
            "/api/v1/notifications/rules",
            json=body,
            headers=ctx["headers"] | {"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201, response.text
        rule = response.json()
        preview = (
            await ctx["client"].post(
                "/api/v1/notifications/rules/preview", json=body, headers=ctx["headers"]
            )
        ).json()
        active = await ctx["client"].post(
            "/api/v1/notifications/rules/" + rule["id"] + "/activate",
            json={"preview_token": preview["preview_token"]},
            headers=ctx["headers"]
            | {"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
        )
        assert active.status_code == 200, active.text
    ctx["service"].clock = clock
    ctx["service"].settings = NotificationSettings(
        _env_file=None,
        environment="test",
        smtp_host="127.0.0.1",
        smtp_port=11025,
        notification_cycle_seconds=5,
    )
    runner = Runner(ctx["service"])
    runner.start()
    try:
        async with asyncio.timeout(59):
            while True:
                async with ctx["service"].database.sessions() as session:
                    rows = list(
                        await session.execute(
                            select(models.Attempt, models.Occurrence)
                            .join(
                                models.Delivery,
                                models.Delivery.id == models.Attempt.delivery_id,
                            )
                            .join(
                                models.Message,
                                models.Message.id == models.Delivery.message_id,
                            )
                            .join(
                                models.Occurrence,
                                models.Occurrence.id == models.Message.occurrence_id,
                            )
                        )
                    )
                if len(rows) == 20 and all(a.finished_at for a, _ in rows):
                    break
                await asyncio.sleep(0.1)
        assert all(
            a.outcome == "aceptada"
            and (a.finished_at - a.started_at).total_seconds() <= 1
            and 0 <= (a.started_at - o.scheduled_at).total_seconds() <= 60
            for a, o in rows
        )
        print(
            "periodic profile:20/20 accepted;max_first_start_seconds="
            + str(max((a.started_at - o.scheduled_at).total_seconds() for a, o in rows))
            + ";max_attempt_seconds="
            + str(max((a.finished_at - a.started_at).total_seconds() for a, _ in rows))
        )
    finally:
        await runner.close()
