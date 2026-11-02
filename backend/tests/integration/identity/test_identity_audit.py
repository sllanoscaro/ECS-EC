"""Account evidence uses platform009 transactions and contains no emails or credentials."""

from uuid import uuid4

from sqlalchemy import select

from ecs_ec.audit.models import AuditRecord, FunctionalEvent
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.audit import IdentityAudit


async def test_evidence_atomic_and_safe(identity_db, clock):
    """Rollback removes evidence; commit keeps two provenance events and an opaque process actor."""
    source = uuid4()
    audit = IdentityAudit(clock, "America/Santiago")
    values = dict(account_id=source, revision=1, actor_ref="process:bootstrap", action="identity.account.created",
                  fields=("role",), role="administrador_tecnico", status="active", renewal=True, operation_ref=uuid4())
    async with UnitOfWork(identity_db.sessions) as uow:
        await audit.changed(uow, **values)
    async with UnitOfWork(identity_db.sessions) as uow:
        assert not (await uow.session.scalars(select(FunctionalEvent).where(FunctionalEvent.source_entity_id == source))).all()
        await audit.changed(uow, **values)
        await uow.commit()
    async with UnitOfWork(identity_db.sessions) as uow:
        events = (await uow.session.scalars(select(FunctionalEvent).where(FunctionalEvent.source_entity_id == source))).all()
        assert {row.event_type for row in events} == {"identity.changed", "administration.changed"}
        rows = (await uow.session.scalars(select(AuditRecord).where(AuditRecord.entity_id == source))).all()
        assert len(rows) == 1 and rows[0].actor_ref == "process:bootstrap"
        assert "@" not in str(rows[0].safe_payload)
        assert "password_hash" not in str(rows[0].safe_payload)


async def test_uncertain_commit_preserves_single_allowed_evidence(identity, identity_db, account_factory, session_factory, monkeypatch):
    """Simulate lost acknowledgement after a real commit: report503 without duplicating the already durable action."""
    import pytest
    from ecs_ec.identity.errors import IdentityProblem
    from ecs_ec.identity.models import Account
    from ecs_ec.identity.schemas import AccountUpdate
    admin = await account_factory(role="administrador_tecnico")
    target = await account_factory()
    _, principal = await session_factory(admin)
    operation = uuid4()
    original = UnitOfWork.commit
    first = True

    async def lost_acknowledgement(uow):
        """Commit normally, then lose exactly one acknowledgement without changing PostgreSQL's outcome."""
        nonlocal first
        await original(uow)
        if first:
            first = False
            raise RuntimeError("synthetic lost commit acknowledgement")

    monkeypatch.setattr(UnitOfWork, "commit", lost_acknowledgement)
    with pytest.raises(IdentityProblem) as failure:
        await identity.update_account(principal, target.id, AccountUpdate(email=target.email, role=target.role, status="inactive"),
                                      1, operation_ref=operation)
    assert failure.value.status == 503
    async with UnitOfWork(identity_db.sessions) as uow:
        assert (await uow.session.get(Account, target.id)).status == "inactive"
        rows = (await uow.session.scalars(select(AuditRecord).where(AuditRecord.safe_payload["operation_ref"].astext == str(operation)))).all()
        assert len(rows) == 1 and rows[0].result == "allowed"
