"""002 minimum calendar retention and explicit authorized detail withdrawal; ledger/configuration remain permanent."""
from typing import Literal
from uuid import UUID

from sqlalchemy import select

from ecs_ec.audit.events import Code, PayloadRegistry, SafePayload
from ecs_ec.audit.services import AuditInput, FunctionalAudit
from ecs_ec.consumption.models import (AcceptedMeasurement, CalculationContributionReference,
    IncorporatedRecord, IncorporatedTotal, TotalCalculationState, TotalEvaluationRequest)
from ecs_ec.core.clock import utc
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork


def retention_deadline(incorporated_at, timezone, previous=None):
    """Return a nondecreasing12-calendar-month anniversary from substantive incorporation, never measured time."""
    deadline = anniversary(incorporated_at, timezone)
    return max(previous, deadline) if previous is not None else deadline


async def protect_contributions(uow, contributions, deadline):
    """Extend required permanent ledger/original evidence to a dependent's deadline without shortening any limit."""
    for contribution in contributions:
        row = await uow.session.get(IncorporatedRecord, contribution.measurement_id)
        if row is None:
            raise ValueError('calculation_evidence_unavailable')
        row.retain_until = max(row.retain_until, deadline)
        payload = await uow.session.get(AcceptedMeasurement, row.id)
        if payload is None and row.detail_state == 'retained':
            raise ValueError('calculation_evidence_unavailable')
        if payload is not None:
            payload.retain_until = max(payload.retain_until, deadline)


async def dependency_protected(uow, row, now):
    """Conservatively protect pending requests/candidates and retained calculated dependents under common locks.

    A pending request can precede its candidate/reference rows; inspect its exact
    interval directly. Source/configuration rows and all record/contribution ledgers
    remain FK-protected permanently, independent of withdrawable original payloads.
    """
    request = await uow.session.scalar(select(TotalEvaluationRequest).where(
        TotalEvaluationRequest.building_id == row.building_id, TotalEvaluationRequest.status == 'pending',
        TotalEvaluationRequest.start == row.start, TotalEvaluationRequest.end == row.end))
    if request is not None and row.category_id != 'CAT-01':
        return True
    candidates = (await uow.session.scalars(select(TotalCalculationState).join(CalculationContributionReference,
        CalculationContributionReference.candidate_id == TotalCalculationState.id).where(
        CalculationContributionReference.record_id == row.id))).all()
    for candidate in candidates:
        if candidate.status == 'pending' or candidate.retain_until > now:
            return True
        if candidate.incorporated_record_id:
            dependent = await uow.session.get(IncorporatedRecord, candidate.incorporated_record_id)
            if dependent is None or dependent.retain_until > now:
                return True
    return False


class WithdrawalPayload(SafePayload):
    """Audit includes stable IDs/codes only, never an original measurement body or arbitrary free text."""

    building_id: UUID
    record_id: UUID
    reason: Code
    outcome: Literal['withdrawn', 'rejected', 'already_withdrawn']
    reason_code: Code


class Retention:
    """Trusted internal maintenance boundary; callers explicitly bind process references to building IDs."""

    def __init__(self, database, clock, *, authorized_processes):
        """Inject real009 resources and trusted composition grants; no public endpoint or automatic purge."""
        self.database, self.clock = database, clock
        self.authorized_processes = {key: frozenset(value) for key, value in authorized_processes.items()}

    async def withdraw_detail(self, *, building_id, record_ids, process, reason, preview=False):
        """Check/revalidate all records under context→category→record locks and audit execution atomically.

        Preview is read-only apart from row locks and writes no audit. At/after the
        minimum, only expired payloads with no protected dependent are removed.
        A mixed request reports per-record decisions, committing permitted removals
        and their audit together; any infrastructure error rolls the whole batch back.
        """
        from ecs_ec.consumption.store import lock_history
        # Validate before locks; unknown processes gain no maintenance access.
        if building_id not in self.authorized_processes.get(process, ()):
            raise PermissionError('retention_process_required')
        from pydantic import TypeAdapter
        TypeAdapter(Code).validate_python(reason)
        async with UnitOfWork(self.database.sessions) as uow:
            building, _, _, _ = await lock_history(uow, building_id)
            now = utc(self.clock.now())
            registry = PayloadRegistry()
            registry.register('consumption.detail.withdrawn', WithdrawalPayload, results={'withdrawn', 'rejected', 'already_withdrawn'})
            audit = FunctionalAudit(registry, self.clock, building.timezone)
            outcomes = []
            for identifier in sorted(set(record_ids)):
                row = await uow.session.scalar(select(IncorporatedRecord).where(
                    IncorporatedRecord.id == identifier, IncorporatedRecord.building_id == building_id).with_for_update())
                payload = None if row is None else await uow.session.get(
                    AcceptedMeasurement if row.kind == 'measured' else IncorporatedTotal, identifier)
                status, code = 'rejected', 'not_found'
                if row is not None:
                    if row.detail_state == 'withdrawn':
                        status, code = 'already_withdrawn', 'already_withdrawn'
                    elif payload is None:
                        code = 'insufficient_evidence'
                    elif now < max(row.retain_until, payload.retain_until):
                        code = 'protected'
                    elif await dependency_protected(uow, row, now):
                        code = 'protected_dependency'
                    else:
                        status, code = 'withdrawn', 'eligible'
                        if not preview:
                            await uow.session.delete(payload)
                            row.detail_state, row.detail_withdrawn_at = 'withdrawn', now
                outcomes.append(dict(record_id=identifier, status=status, reason_code=code))
                if not preview:
                    await audit.append(uow, AuditInput(actor_ref=process, action='consumption.detail.withdrawn',
                        entity_type='consumption.record', entity_id=identifier, entity_revision=row.revision if row else None,
                        occurred_at=now, result=status, safe_payload=WithdrawalPayload(building_id=building_id,
                            record_id=identifier, reason=reason, outcome=status, reason_code=code).model_dump()))
            if not preview:
                await uow.commit()
            return tuple(outcomes)
