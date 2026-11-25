"""008 PostgreSQL constraints reject duplicate durable identities and invalid states, never SQLite substitutes."""

from datetime import timedelta
from uuid import uuid4

import pytest
from ecs_ec.notifications.models import Activation, Rule, RuleVersion, Schedule
from sqlalchemy.exc import IntegrityError


async def seed(database, clock, account_factory):
    """Create one valid inactive rule/version/schedule in a deferred transaction, owned only by this test."""
    actor = await account_factory(role="administrador_tecnico")
    rule, version, schedule = uuid4(), uuid4(), uuid4()
    async with database.sessions() as session:
        session.add(
            Rule(
                id=rule,
                building_id=uuid4(),
                name="Regla sintética",
                current_version_id=version,
                created_by=actor.id,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        session.add(
            RuleVersion(
                id=version,
                rule_id=rule,
                version_number=1,
                mode="periodica",
                content_types=["recepcion"],
                timezone="America/Santiago",
                config={},
                schedule_id=schedule,
                created_by=actor.id,
                created_at=clock.now(),
                retain_until=clock.now() + timedelta(days=400),
            )
        )
        session.add(
            Schedule(
                id=schedule,
                version_id=version,
                kind="diaria",
                starts_at=clock.now(),
                local_time="06:00",
                timezone="America/Santiago",
            )
        )
        await session.commit()
    return rule, version


@pytest.mark.parametrize(
    "invalid",
    ["duplicate_activation", "negative_revision", "invalid_schedule", "two_modes"],
)
async def test_real_database_invariants(database, clock, invalid, account_factory):
    """Independent transactions must fail the actual unique/check/FK rules before claiming durability."""
    rule, version = await seed(database, clock, account_factory)
    async with database.sessions() as session:
        with pytest.raises(IntegrityError):
            if invalid == "duplicate_activation":
                for _ in range(2):
                    session.add(
                        Activation(
                            rule_id=rule,
                            version_id=version,
                            activated_at=clock.now(),
                            tzdata_version="test",
                        )
                    )
            elif invalid == "negative_revision":
                row = await session.get(Rule, rule)
                row.revision = -1
            elif invalid == "invalid_schedule":
                row = await session.get(
                    Schedule, (await session.get(RuleVersion, version)).schedule_id
                )
                row.interval_value = 5
            else:
                row = await session.get(RuleVersion, version)
                row.condition_id = uuid4()
            await session.commit()


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("version", "uq_notification_rule_version_rule_id"),
        ("occurrence", "uq_notification_occurrence_version_id"),
        ("message", "uq_notification_message_occurrence_id"),
        ("delivery", "uq_notification_delivery_message_id"),
        ("attempt", "uq_notification_delivery_attempt_delivery_id"),
        ("open_attempt", "uq_notification_open_attempt"),
    ],
)
async def test_unique_logical_identities_are_real_database_constraints(
    notification_context, kind, expected
):
    """Deliberate duplicate rows must fail the intended PostgreSQL uniqueness constraint, not an unrelated foreign key."""
    from ecs_ec.notifications import models
    from ecs_ec.notifications.repository import prepare_attempt
    from sqlalchemy import select

    env = notification_context
    rule = await env["make_rule"]()
    identifier = await env["pending"](rule)
    if kind in {"attempt", "open_attempt"}:
        await prepare_attempt(env["service"], identifier, uuid4())
    types = {
        "version": models.RuleVersion,
        "occurrence": models.Occurrence,
        "message": models.Message,
        "delivery": models.Delivery,
        "attempt": models.Attempt,
        "open_attempt": models.Attempt,
    }
    cls = types[kind]
    async with env["service"].database.sessions() as session:
        row = await session.scalar(select(cls).order_by(cls.id))
        values = {
            column.key: getattr(row, column.key) for column in cls.__table__.columns
        }
        values["id"] = uuid4()
        if kind == "open_attempt":
            values["attempt_number"] = 2
        session.add(cls(**values))
        with pytest.raises(IntegrityError) as failed:
            await session.commit()
        assert failed.value.orig.diag.constraint_name == expected


async def test_immutable_definition_and_protected_graph(notification_context):
    """A direct update cannot rewrite an approved version/schedule; FK/retention guards preserve evidence under the same database."""
    from uuid import UUID

    from ecs_ec.notifications.models import RuleVersion, Schedule

    env = notification_context
    rule = await env["make_rule"]()
    version_id = UUID(rule["current_version_id"])
    for cls in (RuleVersion, Schedule):
        async with env["service"].database.sessions() as session:
            version = await session.get(RuleVersion, version_id)
            row = (
                version
                if cls is RuleVersion
                else await session.get(Schedule, version.schedule_id)
            )
            if cls is RuleVersion:
                row.config = rule["config"] | {"name": "Unauthorized rewrite"}
            else:
                row.local_time = "07:00"
            with pytest.raises(IntegrityError):
                await session.commit()
    async with env["service"].database.sessions() as session:
        version = await session.get(RuleVersion, version_id)
        await session.delete(version)
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_one_open_episode_per_activation_scope(notification_context):
    """Two open episodes for one actual activation/category fail the dedicated unique index, irrespective of consumers."""
    from datetime import timedelta
    from uuid import UUID

    from ecs_ec.notifications.models import Activation, Episode, Evidence
    from sqlalchemy import select

    env = notification_context
    rule = await env["make_rule"]()
    now = env["clock"].now()
    proof = uuid4()
    async with env["service"].database.sessions() as session:
        activation = await session.scalar(
            select(Activation).where(
                Activation.version_id == UUID(rule["current_version_id"])
            )
        )
        session.add(
            Evidence(
                id=proof,
                payload={},
                created_at=now,
                retain_until=now + timedelta(days=400),
            )
        )
        session.add(
            Episode(
                id=uuid4(),
                activation_id=activation.id,
                scope_key="CAT-05",
                opened_at=now,
                opening_evidence_id=proof,
                created_at=now,
                retain_until=now + timedelta(days=400),
            )
        )
        await session.commit()
        activation_id = activation.id
    async with env["service"].database.sessions() as session:
        session.add(
            Episode(
                id=uuid4(),
                activation_id=activation_id,
                scope_key="CAT-05",
                opened_at=now,
                opening_evidence_id=proof,
                created_at=now,
                retain_until=now + timedelta(days=400),
            )
        )
        with pytest.raises(IntegrityError) as failed:
            await session.commit()
        assert failed.value.orig.diag.constraint_name == "uq_notification_open_episode"


async def test_original_delivery_joins_only_one_recovery_batch(notification_context):
    """Actual SQL membership validates same rule/account and never-attempted original, then rejects duplicate membership by PK."""
    from ecs_ec.notifications.models import Delivery, RecoveryMember

    env = notification_context
    rule = await env["make_rule"]()
    original = await env["pending"](rule)
    recovery = await env["pending"](rule, kind="recuperacion")
    values = dict(
        original_delivery_id=original,
        recovery_delivery_id=recovery,
        original_slot="fixture-original",
        original_window={},
        created_at=env["clock"].now(),
    )
    async with env["service"].database.sessions() as session:
        row = await session.get(Delivery, original)
        row.state = "cancelada"
        row.cancellation_reason = "consolidada_en_recuperacion"
        session.add(RecoveryMember(**values))
        await session.commit()
    async with env["service"].database.sessions() as session:
        session.add(RecoveryMember(**values))
        with pytest.raises(IntegrityError) as failed:
            await session.commit()
        assert (
            failed.value.orig.diag.constraint_name == "pk_notification_recovery_member"
        )
