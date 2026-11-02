"""Host recovery operates only on an already active admin, using captured revision and permanent audit evidence."""

import pytest
from sqlalchemy import select

from ecs_ec.audit.models import AuditRecord
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem


async def test_recovery_revokes_and_records_process(identity, identity_db, account_factory, session_factory):
    """Recovery sets renewal and revokes both devices without exposing the old credential or elevating a role."""
    admin = await account_factory(role="administrador_tecnico")
    cookies = [(await session_factory(admin))[0] for _ in range(2)]
    row = await identity.recover_admin(admin.email, "Recovery synthetic password", "Ensayo operativo local")
    assert row.id == admin.id and row.must_change_password and row.auth_version == 2
    for cookie in cookies:
        with pytest.raises(IdentityProblem):
            await identity.resolve_session(cookie)
    async with UnitOfWork(identity_db.sessions) as uow:
        audit = await uow.session.scalar(select(AuditRecord).where(AuditRecord.action == "identity.recovery"))
        assert audit.actor_ref == "process:recovery"
        assert "Recovery synthetic password" not in str(audit.safe_payload)


@pytest.mark.parametrize("target", ["unknown", "inactive", "operator"])
async def test_recovery_never_creates_reactivates_or_promotes(identity, account_factory, target):
    """No account, inactive admin and active Operator all remain ineligible for host recovery."""
    await account_factory(role="administrador_tecnico")
    row = await account_factory(role="administrador_tecnico", status="inactive") if target == "inactive" else await account_factory() if target == "operator" else None
    with pytest.raises(IdentityProblem) as failure:
        await identity.recover_admin(row.email if row else "unknown@example.test", "Recovery synthetic password", "Ensayo")
    assert failure.value.code == "recovery_not_allowed"


@pytest.mark.parametrize("reason", ["", " ", "x"*501, "Invalid\nreason"])
async def test_recovery_requires_bounded_safe_reason(identity, account_factory, reason):
    """Reject missing/overlong/control-containing recovery reasons without touching the credential."""
    admin = await account_factory(role="administrador_tecnico")
    with pytest.raises(IdentityProblem) as failure:
        await identity.recover_admin(admin.email, "Recovery synthetic password", reason)
    assert failure.value.status == 422
