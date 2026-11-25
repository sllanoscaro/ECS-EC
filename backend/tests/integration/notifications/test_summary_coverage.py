"""Periodic captures preserve real functional coverage, including the approved empty first window."""

from datetime import timedelta
from uuid import UUID

import pytest
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.notifications.models import RuleVersion
from ecs_ec.notifications.summaries import read_summary, summary_status


async def test_empty_initial_window_is_unknown_for_every_selected_content(
    notification_context,
):
    """An empty first window never claims observed history or zero events."""
    ctx = notification_context
    rule = await ctx["make_rule"](contents=["recepcion", "calidad"])
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        version = await uow.session.get(RuleVersion, UUID(rule["current_version_id"]))
        now = ctx["clock"].now()
        items = await read_summary(ctx["service"], uow, version, now, now, now)
    assert [item["kind"] for item in items] == ["recepcion", "calidad"]
    assert all(
        item["count"] is None
        and item["coverage"] == "desconocida"
        and item["limitation_code"] == "ventana_inicial_vacia"
        for item in items
    )
    assert summary_status(items) == "informacion_insuficiente"


async def test_period_before_registration_is_incomplete_not_empty(notification_context):
    """The actual consumption owner establishes a known registration gap without inventing totals."""
    ctx = notification_context
    rule = await ctx["make_rule"]()
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        version = await uow.session.get(RuleVersion, UUID(rule["current_version_id"]))
        now = ctx["clock"].now()
        items = await read_summary(
            ctx["service"], uow, version, now - timedelta(days=1), now, now
        )
    assert items[0]["coverage"] == "incompleta"
    assert items[0]["known_gaps"]
    assert summary_status(items) == "informacion_insuficiente"


def test_status_requires_all_contents_complete_and_known():
    """Known zero, known events and unknown history have three distinct global states."""
    assert summary_status([{"coverage": "completa", "count": 0}]) == "sin_novedades"
    assert summary_status([{"coverage": "completa", "count": 2}]) == "disponible"
    assert (
        summary_status(
            [
                {"coverage": "completa", "count": 2},
                {"coverage": "desconocida", "count": None},
            ]
        )
        == "informacion_insuficiente"
    )


async def test_real_complete_reception_and_quality_counts(
    notification_context, history_environment
):
    """Actual002 accepted publication establishes reception events and complete known zero quality rejections."""
    from backend.tests.contract.consumption.test_reception_contract import publish
    from backend.tests.unit.consumption.test_validation import record

    ctx = notification_context
    rule = await ctx["make_rule"](contents=["recepcion", "calidad"])
    start = ctx["clock"].now()
    await publish(history_environment, [record(value="2")])
    ctx["clock"].advance(7200)
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        version = await uow.session.get(RuleVersion, UUID(rule["current_version_id"]))
        items = await read_summary(
            ctx["service"], uow, version, start, ctx["clock"].now(), ctx["clock"].now()
        )
    assert all(i["coverage"] == "completa" for i in items)
    assert (
        items[0]["count"] > 0
        and items[1]["count"] == 0
        and summary_status(items) == "disponible"
    )


@pytest.mark.parametrize("reason", ["conservacion_vencida", "fuente_no_consultable"])
async def test_explicit_functional_coverage_overrides_inferred_history(
    notification_context, reason
):
    """Real009 coverage evidence preserves expiry gaps or source unavailability, never synthesizing zero."""
    from ecs_ec.audit.events import Interval
    from ecs_ec.audit.services import CoverageInput, CoverageService

    ctx = notification_context
    rule = await ctx["make_rule"]()
    start = ctx["clock"].now()
    ctx["clock"].advance(7200)
    end = ctx["clock"].now()
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        missing = reason == "fuente_no_consultable"
        await CoverageService(ctx["clock"], "America/Santiago").append(
            uow,
            CoverageInput(
                content_type="recepcion",
                source_ref="process:consumption",
                cutoff_at=end,
                window_start=start,
                window_end=end,
                integrity="desconocida" if missing else "incompleta",
                observed_count=None if missing else 2,
                covered_periods=[]
                if missing
                else [Interval(start=start + timedelta(hours=1), end=end)],
                known_gaps=[]
                if missing
                else [Interval(start=start, end=start + timedelta(hours=1))],
                limitation_code=reason,
                recorded_by="process:test",
            ),
        )
        await uow.commit()
    async with UnitOfWork(ctx["service"].database.sessions) as uow:
        version = await uow.session.get(RuleVersion, UUID(rule["current_version_id"]))
        items = await read_summary(ctx["service"], uow, version, start, end, end)
    assert items[0]["limitation_code"] == reason
    assert items[0]["count"] == (None if missing else 2)
    assert summary_status(items) == "informacion_insuficiente"
