"""Neutral coordination works without consumers and rejects ambiguous registration."""

import pytest

from ecs_ec.identity.coordination import ParticipantRegistry


class SyntheticParticipant:
    """Participant probe records phases; no network or commits belong to this protocol."""

    name = "synthetic"
    before_range = (100, 199)
    after_range = (100, 199)

    async def discover(self, mutation, uow):
        """Return a stable synthetic discovery signature without side effects."""
        return (mutation.account_id,)

    async def lock(self, plan, phase, uow):
        """No resources are owned by this minimal registration probe."""
        return None

    async def revalidate(self, mutation, plan, uow):
        """The fixed discovery remains stable."""
        return True

    async def apply(self, mutation, plan, uow):
        """This participant has no adjustment; real transactional probes are added with services."""
        return None


def test_registry_freezes_and_checks_ranges():
    """Duplicate names, overlapping ranges and mutations after freeze are configuration errors."""
    registry = ParticipantRegistry()
    assert registry.freeze() == ()
    with pytest.raises(ValueError):
        registry.register(SyntheticParticipant())


async def test_full_redetection_and_maximum_three(identity_db, identity_settings, clock, reference_hash):
    """Every failed signature starts a new guarded transaction; three unstable attempts cannot commit."""
    from sqlalchemy import func, select
    from ecs_ec.identity.models import Account
    from ecs_ec.identity.services import Identity
    from ecs_ec.identity.errors import IdentityProblem
    from ecs_ec.core.unit_of_work import UnitOfWork

    class Unstable(SyntheticParticipant):
        """Always change discovery to exercise the complete rollback/retry limit."""

        def __init__(self):
            """Record phases without keeping any durable state outside the UoW."""
            self.calls = []

        async def discover(self, mutation, uow):
            """Record each new discovery before account/session locks."""
            self.calls.append("discover")
            return ()

        async def lock(self, plan, phase, uow):
            """Record each globally ordered lock phase."""
            self.calls.append(phase)

        async def revalidate(self, mutation, plan, uow):
            """Force a changed signature without committing anything."""
            self.calls.append("revalidate")
            return False

    participant = Unstable()
    registry = ParticipantRegistry()
    registry.register(participant)
    service = Identity(identity_db, identity_settings, clock, "UTC", registry)
    with pytest.raises(IdentityProblem, match="nuevo intento") as failure:
        await service._mutate(operation="bootstrap", actor="process:bootstrap", email="first@example.test",
                              email_key="first@example.test", prepared_hash=reference_hash)
    assert failure.value.code == "identity_coordination_retry"
    assert participant.calls == ["discover", "before", "after", "revalidate"] * 3
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Account)) == 0


async def test_participant_failure_rolls_back(identity_db, identity_settings, clock, reference_hash):
    """A failed domain adjustment cannot leave a new account or orphaned change events."""
    from sqlalchemy import func, select
    from ecs_ec.identity.models import Account
    from ecs_ec.audit.models import FunctionalEvent
    from ecs_ec.identity.services import Identity
    from ecs_ec.identity.errors import IdentityProblem
    from ecs_ec.core.unit_of_work import UnitOfWork

    class Failing(SyntheticParticipant):
        """Probe the transactional port's absence of independent commits."""

        async def apply(self, mutation, plan, uow):
            """Fail after account flush and confirm participant cannot commit its transaction."""
            assert not hasattr(uow, "commit") and not hasattr(uow.session, "commit")
            raise RuntimeError("synthetic participant failure")

    registry = ParticipantRegistry()
    registry.register(Failing())
    service = Identity(identity_db, identity_settings, clock, "UTC", registry)
    with pytest.raises(IdentityProblem) as failure:
        await service._mutate(operation="bootstrap", actor="process:bootstrap", email="first@example.test",
                              email_key="first@example.test", prepared_hash=reference_hash)
    assert failure.value.status == 503
    async with UnitOfWork(identity_db.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(Account)) == 0
        assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent)) == 0
    registry = ParticipantRegistry()
    registry.register(SyntheticParticipant())
    with pytest.raises(ValueError):
        registry.register(SyntheticParticipant())
    registry.freeze()
    with pytest.raises(ValueError):
        registry.register(SyntheticParticipant())
