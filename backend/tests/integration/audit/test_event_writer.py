"""Synthetic producers prove evidence/result atomicity, event deduplication and safe schemas."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from ecs_ec.audit.events import EventInput, EventWriter, PayloadRegistry, SafePayload
from ecs_ec.audit.models import AuditRecord, FunctionalEvent
from ecs_ec.audit.services import AuditInput, FunctionalAudit
from ecs_ec.core.errors import InvalidEvidence
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


class SyntheticPayload(SafePayload):
    """Approved synthetic result vocabulary; free text, identities and secrets are absent."""

    outcome: Literal["ok", "failed"]


def registry():
    """Register only the synthetic event/action owned by this test producer."""
    result = PayloadRegistry()
    result.register("synthetic.changed", SyntheticPayload, results={"succeeded", "denied"})
    return result


def event(entity_id, **changes):
    """Build an explicit producer event; caller can override fields to test rejection/dedup."""
    return EventInput(event_id=uuid4(), event_type="synthetic.changed", source_module="synthetic",
                      source_entity_id=entity_id, source_revision=1,
                      occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
                      safe_payload={"outcome": "ok"}, **changes)


async def test_atomic_commit_and_dedup(database, clock):
    """A producer result and one stable event survive commit and two provenance retries."""
    source_id = uuid4()
    writer = EventWriter(registry(), clock, "America/Santiago")
    name = "result_" + uuid4().hex
    async with database.engine.begin() as connection:
        await connection.execute(text(f"CREATE TABLE {name} (id uuid PRIMARY KEY)"))
    try:
        original = event(source_id)
        async with UnitOfWork(database.sessions) as uow:
            await uow.session.execute(text(f"INSERT INTO {name} VALUES (:id)"), {"id": source_id})
            first = await writer.append(uow, original)
            same = await writer.append(uow, event(source_id))
            assert same.id == first.id == original.event_id
            await uow.commit()
        async with UnitOfWork(database.sessions) as uow:
            again = await writer.append(uow, event(source_id))
            assert again.id == original.event_id
            assert again.recorded_at == clock.now()
            assert again.retain_until > again.recorded_at
            assert await uow.session.scalar(text(f"SELECT count(*) FROM {name}")) == 1
            assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(
                FunctionalEvent.source_entity_id == source_id)) == 1
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE {name}"))


async def test_rollback_both_result_and_event(database, clock):
    """Failure after append leaves neither the synthetic result nor its event."""
    source_id = uuid4()
    writer = EventWriter(registry(), clock, "UTC")
    name = "result_" + uuid4().hex
    async with database.engine.begin() as connection:
        await connection.execute(text(f"CREATE TABLE {name} (id uuid PRIMARY KEY)"))
    try:
        with pytest.raises(RuntimeError):
            async with UnitOfWork(database.sessions) as uow:
                await uow.session.execute(text(f"INSERT INTO {name} VALUES (:id)"), {"id": source_id})
                await writer.append(uow, event(source_id))
                raise RuntimeError("synthetic producer rollback")
        async with UnitOfWork(database.sessions) as uow:
            assert await uow.session.scalar(text(f"SELECT count(*) FROM {name}")) == 0
            assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(
                FunctionalEvent.source_entity_id == source_id)) == 0
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE {name}"))


async def test_audit_opaque_actor_repeatable_actions(database, clock):
    """Two legitimate denied attempts by a process remain distinct and need no account FK."""
    entity_id = uuid4()
    audit = FunctionalAudit(registry(), clock, "UTC")
    action = AuditInput(actor_ref="process:synthetic", action="synthetic.changed", entity_type="synthetic",
                        entity_id=entity_id, entity_revision=1, occurred_at=clock.now(), result="denied",
                        safe_payload={"outcome": "failed"})
    async with UnitOfWork(database.sessions) as uow:
        one = await audit.append(uow, action)
        two = await audit.append(uow, action)
        assert one.id != two.id
        await uow.commit()
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(
            AuditRecord.entity_id == entity_id)) == 2


async def test_unknown_or_unsafe_payload_rejected(database, clock):
    """Unapproved fields or action schemas fail before any evidence is persisted."""
    writer = EventWriter(registry(), clock, "UTC")
    original = event(uuid4())
    for changes in ({"safe_payload": {"outcome": "ok", "password": "secret"}},
                    {"event_type": "unregistered.changed"},
                    {"safe_payload": {"outcome": "raw exception / SQL"}}):
        async with UnitOfWork(database.sessions) as uow:
            with pytest.raises(InvalidEvidence):
                await writer.append(uow, original.model_copy(update=changes))


async def test_concurrent_dedup(database, clock):
    """Concurrent PostgreSQL producers converge on the committed provenance event UUID."""
    import asyncio
    source_id = uuid4()
    writer = EventWriter(registry(), clock, "UTC")

    async def producer():
        """Append and commit in an independent connection; PostgreSQL arbitrates uniqueness."""
        async with UnitOfWork(database.sessions) as uow:
            row = await writer.append(uow, event(source_id))
            await uow.commit()
            return row.id

    ids = await asyncio.gather(*(producer() for _ in range(4)))
    assert len(set(ids)) == 1


async def test_envelope_mapping_and_retry_retention(database, clock):
    """Public envelope aliases map explicitly; measurement scope persists and reads/retries do not renew retention."""
    from datetime import timedelta
    raw = event(uuid4()).model_dump()
    raw["type"] = raw.pop("event_type")
    raw["measurement_window"] = {"start": clock.now(), "end": clock.now() + timedelta(hours=1)}
    raw["accepted_new_data"] = True
    value = EventInput.model_validate(raw)
    writer = EventWriter(registry(), clock, "UTC")
    async with UnitOfWork(database.sessions) as uow:
        original = await writer.append(uow, value)
        retention = original.retain_until
        assert original.effective_window == {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}
        assert original.accepted_new_data is True
        await uow.commit()
    clock.advance(86400)
    async with UnitOfWork(database.sessions) as uow:
        repeated = await writer.append(uow, value)
        assert repeated.retain_until == retention
        assert repeated.recorded_at < clock.now()
