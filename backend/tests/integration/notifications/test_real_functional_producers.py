"""008 consumes real004/005 failed results/events; private fault injection exercises their existing atomic producer boundaries."""

from ecs_ec.notifications import models
from ecs_ec.notifications.episodes import Evaluator
from sqlalchemy import func, select

from backend.tests.integration.costs.test_calculation_events import (
    test_failed_result_event_and_replay as costs_failure,
)
from backend.tests.integration.reports.test_failure_events import (
    test_admitted_failure_is_atomic as pdf_failure,
)


async def test_actual_cost_failed_result_creates_one_urgent_episode(
    notification_context,
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """Real004 persists a failed calculation/event with001/002 inputs; replay cannot produce a second008 notification."""
    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(kind="evento_sistema", event_type="calculo_fallido"),
        )
    )
    await costs_failure(
        costs_client,
        costs_environment,
        account_factory,
        session_factory,
        identity_settings,
        monkeypatch,
    )
    evaluator = Evaluator(ctx["service"])
    await evaluator.tick()
    await evaluator.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )
        message = await session.scalar(select(models.Message))
        assert message.functional_content["source_event"]["module"] == "costs"
        assert (
            message.functional_content["condition"]["event_type"] == "calculo_fallido"
        )


async def test_actual_pdf_failed_result_creates_one_urgent_episode(
    notification_context,
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """Real005 request/capture/worker fails its render boundary and atomically publishes the safe durable result/event."""
    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(kind="evento_sistema", event_type="pdf_fallido"),
        )
    )
    await pdf_failure(
        costs_client,
        costs_environment,
        account_factory,
        session_factory,
        identity_settings,
        monkeypatch,
        "render",
    )
    evaluator = Evaluator(ctx["service"])
    await evaluator.tick()
    await evaluator.tick()
    async with ctx["service"].database.sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(models.Episode)) == 1
        )
        message = await session.scalar(select(models.Message))
        assert message.functional_content["source_event"]["module"] == "reports"


async def test_later_commit_with_lower_uuid_and_same_timestamp_is_not_lost(
    notification_context,
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    monkeypatch,
):
    """Two actual005 failures at the same injected timestamp are both consumed, regardless of UUID order."""
    from itertools import count
    from uuid import UUID

    import ecs_ec.reports.repository as repository
    from ecs_ec.audit.models import FunctionalEvent

    from backend.tests.contract.costs.test_calculations_api import authenticate
    from backend.tests.contract.reports.test_reports_api import terminal

    ctx = notification_context
    await ctx["make_rule"](
        config_changes=dict(
            mode="urgente",
            condition=dict(kind="evento_sistema", event_type="pdf_fallido"),
        )
    )
    await pdf_failure(
        costs_client,
        costs_environment,
        account_factory,
        session_factory,
        identity_settings,
        monkeypatch,
        "render",
    )
    engine = Evaluator(ctx["service"])
    await engine.tick()
    sequence = count(1)
    monkeypatch.setattr(repository, "uuid4", lambda: UUID(int=next(sequence)))
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    admitted = await costs_client.post(
        "/api/v1/reports", json=dict(scale="anual", year=2023), headers=headers
    )
    assert admitted.status_code == 202, admitted.text
    assert (await terminal(costs_client, admitted.json()["id"]))["state"] == "fallido"
    await engine.tick()
    await engine.tick()
    async with ctx["service"].database.sessions() as session:
        events = list(
            await session.scalars(
                select(FunctionalEvent)
                .where(FunctionalEvent.event_type == "pdf.failed")
                .order_by(FunctionalEvent.id)
            )
        )
        assert len(events) == 2 and events[0].recorded_at == events[1].recorded_at
        assert (
            await session.scalar(select(func.count()).select_from(models.Delivery)) == 2
        )
