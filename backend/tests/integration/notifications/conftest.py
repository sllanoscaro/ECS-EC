"""008 notification integration fixtures use actual006 sessions/rules and prepared pending work, without SMTP injection endpoints."""

from uuid import UUID, uuid4

import pytest
from ecs_ec.core.retention import anniversary
from ecs_ec.notifications.models import Activation, Delivery, Message, Occurrence
from sqlalchemy import select, text

from backend.tests.contract.notifications.test_rules_api import authenticated, config
from backend.tests.integration.observability.conftest import (  # noqa: F401
    deliver_telemetry,
    gateway_client,
    gateway_image,
    gateway_project,
    gateway_root,
)


@pytest.fixture
def identity_settings(identity_settings):
    """Use the same provisioned singleton as real001/002 integration fixtures."""
    return identity_settings.model_copy(update={"building_id": UUID(int=99)})


@pytest.fixture
async def notification_context(
    notification_database_reset,
    history_environment,
    client,
    account_factory,
    session_factory,
    identity_settings,
    clock,
):
    """Create actual active rules through the API, plus an eligible registered recipient; no background mail loops."""
    admin, headers = await authenticated(
        client, account_factory, session_factory, identity_settings
    )
    recipient = await account_factory(role="operador")
    service = client._transport.app.state.notifications
    principal = await service.identity.resolve_session(
        client.cookies.get("ecs_ec_session")
    )

    async def make_rule(*, contents=None, recipient_id=None, config_changes=None):
        """Publish and explicitly activate one validated real rule with a current preview."""
        body = config(
            recipient_id or recipient.id, content_types=contents or ["recepcion"]
        )
        if config_changes:
            body.update(config_changes)
        if body["mode"] == "urgente":
            body.pop("content_types", None)
            body.pop("schedule", None)
        response = await client.post(
            "/api/v1/notifications/rules",
            json=body,
            headers=headers | {"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201, response.text
        rule = response.json()
        preview = (
            await client.post(
                "/api/v1/notifications/rules/preview", json=body, headers=headers
            )
        ).json()
        active = await client.post(
            "/api/v1/notifications/rules/" + rule["id"] + "/activate",
            json={"preview_token": preview["preview_token"]},
            headers=headers | {"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
        )
        assert active.status_code == 200, active.text
        return active.json()

    async def pending(rule, *, kind="periodica"):
        """Prepare one pending row for transaction/coordination tests; no invented domain result or actual email."""
        version = UUID(rule["current_version_id"])
        now = clock.now()
        retain = anniversary(now, rule["config"]["timezone"])
        occurrence, message, delivery = uuid4(), uuid4(), uuid4()
        async with service.database.sessions() as session:
            activation = await session.scalar(
                select(Activation).where(
                    Activation.version_id == version, Activation.ended_at.is_(None)
                )
            )
            session.add(
                Occurrence(
                    id=occurrence,
                    version_id=version,
                    activation_id=activation.id,
                    kind=kind,
                    logical_key=str(uuid4()),
                    scheduled_at=now,
                    cutoff_at=now,
                    tzdata_version=activation.tzdata_version,
                    created_at=now,
                    retain_until=retain,
                )
            )
            session.add(
                Message(
                    id=message,
                    occurrence_id=occurrence,
                    functional_content={},
                    content_hash="0" * 64,
                    required_permissions=["administration.history.read"]
                    if "cambios_administrativos" in rule["config"]["content_types"]
                    else ["consumption.read"],
                    created_at=now,
                    retain_until=retain,
                )
            )
            session.add(
                Delivery(
                    id=delivery,
                    message_id=message,
                    account_id=UUID(rule["config"]["recipient_ids"][0]),
                    next_attempt_at=now,
                    smtp_message_id=f"<{delivery}@example.test>",
                    transport_kind="local_prueba",
                    created_at=now,
                    retain_until=retain,
                )
            )
            await session.commit()
        return delivery

    yield dict(
        client=client,
        service=service,
        admin=admin,
        principal=principal,
        recipient=recipient,
        headers=headers,
        make_rule=make_rule,
        pending=pending,
        clock=clock,
    )
    # Fixture-only teardown on the explicitly checked disposable database. Restrictive
    # functional-event references remain intact in the production application.
    async with service.database.engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE notification_rule, notification_evidence CASCADE")
        )


@pytest.fixture
async def notification_database_reset(identity_db):
    """Run006's checked account/evidence reset before001/002's history fixture begins cleanup."""
    async with identity_db.engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE notification_rule, notification_evidence CASCADE")
        )
    yield identity_db
