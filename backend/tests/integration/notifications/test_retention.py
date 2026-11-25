"""Calendar anniversaries and later attempts/resend decisions protect the complete captured evidence graph."""

from datetime import datetime
from uuid import uuid4

import pytest
from ecs_ec.core.retention import anniversary
from ecs_ec.notifications import models
from ecs_ec.notifications.repository import prepare_attempt
from ecs_ec.notifications.resends import resend

from backend.tests.contract.notifications.test_history_resends_api import failed_context


@pytest.mark.parametrize(
    ("at", "zone", "expected"),
    [
        ("2024-02-29T12:00:00Z", "UTC", "2025-02-28T12:00:00Z"),
        ("2024-03-09T07:30:00Z", "America/New_York", "2025-03-09T07:00:00Z"),
        ("2024-11-02T05:30:00Z", "America/New_York", "2025-11-02T06:30:00Z"),
    ],
)
def test_calendar_cases_use_platform_policy(at, zone, expected):
    """Independent UTC expectations distinguish leap clamping, nonexistent time and the second repeated time."""
    assert anniversary(datetime.fromisoformat(at), zone) == datetime.fromisoformat(
        expected
    )


async def test_later_resend_attempt_extends_parents_but_reads_and_replays_do_not(
    notification_context, session_factory, identity_settings
):
    """A later decision/attempt has its own full calendar year, while stable history reads and HTTP repeats preserve deadlines."""
    ctx = notification_context
    parent = await failed_context(ctx, session_factory, identity_settings)
    ctx["clock"].advance(86400)
    bearer, principal = await session_factory(ctx["admin"])
    body = dict(reason="Verificación posterior", acknowledge_possible_duplicate=True)
    key = str(uuid4())
    result = await resend(ctx["service"], principal, parent, body, key)
    child_id = __import__("uuid").UUID(result["delivery"]["id"])
    async with ctx["service"].database.sessions() as session:
        child = await session.get(models.Delivery, child_id)
        message = await session.get(models.Message, child.message_id)
        occurrence = await session.get(models.Occurrence, message.occurrence_id)
        version = await session.get(models.RuleVersion, occurrence.version_id)
        deadline = anniversary(ctx["clock"].now(), ctx["service"].identity.timezone)
        assert (
            min(
                child.retain_until,
                message.retain_until,
                occurrence.retain_until,
                version.retain_until,
            )
            >= deadline
        )
        before = [
            child.retain_until,
            message.retain_until,
            occurrence.retain_until,
            version.retain_until,
        ]
    ctx["clock"].advance(60)
    await resend(ctx["service"], principal, parent, body, key)
    from ecs_ec.notifications.queries import delivery_detail

    await delivery_detail(ctx["service"], principal, child_id)
    async with ctx["service"].database.sessions() as session:
        rows = [
            await session.get(cls, key)
            for cls, key in [
                (models.Delivery, child_id),
                (models.Message, message.id),
                (models.Occurrence, occurrence.id),
                (models.RuleVersion, version.id),
            ]
        ]
        assert [row.retain_until for row in rows] == before
    capture = await prepare_attempt(ctx["service"], child_id, uuid4())
    assert capture
    async with ctx["service"].database.sessions() as session:
        attempt = await session.get(models.Attempt, capture["attempt_id"])
        row = await session.get(models.RuleVersion, version.id)
        assert (
            attempt.retain_until
            == anniversary(ctx["clock"].now(), ctx["service"].identity.timezone)
            and row.retain_until >= attempt.retain_until
        )
