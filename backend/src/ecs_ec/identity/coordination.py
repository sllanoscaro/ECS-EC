"""Neutral frozen participant registry; resources are coordinated inside the producer UoW."""

import inspect
import re


class ParticipantSession:
    """Limited transactional port; participants cannot commit/rollback or replace the transaction."""

    def __init__(self, session):
        """Wrap the producer session without exposing engine/connection/transaction methods."""
        self._session = session

    async def execute(self, statement, *args, **kwargs):
        """Execute participant SQL except explicit transaction-control statements."""
        if re.match(r"\s*(commit|rollback|begin|end|savepoint|start|prepare)\b", str(statement), re.I):
            raise RuntimeError("Participant transaction control is forbidden")
        return await self._session.execute(statement, *args, **kwargs)

    async def scalar(self, statement, *args, **kwargs):
        """Return the first column through the same transaction-control guard."""
        return (await self.execute(statement, *args, **kwargs)).scalar()

    async def scalars(self, statement, *args, **kwargs):
        """Return typed scalar results without opening another transaction."""
        return (await self.execute(statement, *args, **kwargs)).scalars()

    def add(self, row):
        """Stage an owned domain row in the producer transaction."""
        self._session.add(row)

    async def flush(self):
        """Flush staged participant rows without committing."""
        await self._session.flush()


class ParticipantWork:
    """Expose only the limited session port, never commit or networking facilities."""

    def __init__(self, uow):
        """Bind a participant to the existing producer UoW."""
        self.session = ParticipantSession(uow.session)


class ParticipantRegistry:
    """Register complete async participants with disjoint explicit ranges, then freeze."""

    def __init__(self):
        """Create a mutable composition-only registry; an empty frozen registry is valid."""
        self._participants = []
        self._frozen = False

    def register(self, participant):
        """Reject duplicate names, invalid ranges, incomplete ports and registration after serving."""
        if self._frozen or not getattr(participant, "name", ""):
            raise ValueError("Participant registry is frozen or name is missing")
        if any(other.name == participant.name for other in self._participants):
            raise ValueError("Duplicate participant name")
        if not all(inspect.iscoroutinefunction(getattr(participant, method, None)) for method in ("discover", "lock", "revalidate", "apply")):
            raise ValueError("Participant must implement every async protocol method")
        for phase in ("before", "after"):
            bounds = getattr(participant, phase + "_range", ())
            if len(bounds) != 2 or not all(isinstance(value, int) for value in bounds) or not 0 <= bounds[0] <= bounds[1] <= 10000:
                raise ValueError("Invalid participant lock range")
            for other in self._participants:
                existing = getattr(other, phase + "_range")
                if bounds[0] <= existing[1] and existing[0] <= bounds[1]:
                    raise ValueError("Participant lock ranges overlap")
        self._participants.append(participant)

    def freeze(self):
        """Return an immutable composition snapshot; additional registrations are prohibited."""
        self._frozen = True
        return tuple(self._participants)

    async def discover(self, mutation, uow):
        """Collect owned references after the identity guard, without effects or another UoW."""
        work = ParticipantWork(uow)
        return [(participant, await participant.discover(mutation, work)) for participant in self.freeze()]

    async def lock(self, plans, phase, uow):
        """Acquire the specified global phase by explicit domain range; each owner sorts its UUIDs."""
        for participant, plan in sorted(plans, key=lambda item: getattr(item[0], phase + "_range")):
            await participant.lock(plan, phase, ParticipantWork(uow))

    async def stable(self, mutation, plans, uow):
        """Revalidate every discovery under locks; false requests a complete rollback/redetection."""
        for participant, plan in plans:
            if not await participant.revalidate(mutation, plan, ParticipantWork(uow)):
                return False
        return True

    async def apply(self, mutation, plans, uow):
        """Apply owned adjustments with the account/evidence transaction, without independent commits."""
        for participant, plan in plans:
            await participant.apply(mutation, plan, ParticipantWork(uow))
