"""Durable002 CAT-01 evaluation/recovery using001's pure calculator and common write coordination."""

import asyncio
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from sqlalchemy import select

from ecs_ec.consumption.aggregates import contribute, energy_quanta
from ecs_ec.consumption.calendar import TZDATA_VERSION
from ecs_ec.consumption.catalog_storage import configuration_segments
from ecs_ec.consumption.models import (CalculationContributionReference, CategoryUpdate, Contribution, IncorporatedRecord,
    IncorporatedTotal, TotalCalculationState, TotalEvaluationRequest)
from ecs_ec.consumption.reception import append_update_events
from ecs_ec.consumption.store import advance_state, lock_history
from ecs_ec.consumption.totals import TotalCalculator
from ecs_ec.core.clock import utc
from ecs_ec.consumption.retention import protect_contributions, retention_deadline
from ecs_ec.core.unit_of_work import UnitOfWork


async def _incorporate(uow, candidate, state, update, now, timezone, correlation_ref):
    """Persist a complete calculated payload, exact aggregates and initial reference protection atomically."""
    deadline = retention_deadline(now, timezone)
    snapshots = [c.model_dump(mode='json') for c in candidate.contributions]
    basis = [b.model_dump(mode='json') for b in candidate.configuration_segments[0].basis_sources]
    row = IncorporatedRecord(id=uuid4(), revision=1, building_id=candidate.building_id, category_id='CAT-01',
        kind='calculated', source_id=None, logical_source_key='CAT-01:calculated', start=candidate.start, end=candidate.end,
        energy_kwh=candidate.energy_kwh, energy_quanta=energy_quanta(candidate.energy_kwh),
        configuration_revision=candidate.configuration_revision, category_revision=candidate.category_revision,
        first_incorporated_at=now, update_id=update.id, source_evidence_ref=str(state.id), correlation_ref=correlation_ref,
        provenance_snapshot=dict(mode='calculated', base_categories=list(candidate.base_categories), basis_sources=basis,
            contributions=snapshots, category_revision=candidate.category_revision,
            configuration_segments=[s.model_dump(mode='json') for s in candidate.configuration_segments]),
        detail_state='retained', detail_withdrawn_at=None, retain_until=deadline, retention_timezone=timezone, tzdata_version=TZDATA_VERSION)
    uow.session.add(row)
    await uow.session.flush()
    uow.session.add(IncorporatedTotal(record_id=row.id, first_incorporated_at=now, retain_until=deadline,
        base_categories=list(candidate.base_categories), basis_sources=basis, contributions=snapshots))
    await protect_contributions(uow, candidate.contributions, deadline)
    await contribute(uow, row, now)
    return row


class PendingTotals:
    """Recover requests without candidates and pending incorporation, independent from source re-sends/GET."""

    def __init__(self, database, clock, *, sessions=None):
        """Receive shared009 DB/clock; each run uses fresh READ COMMITTED category transactions."""
        self.database, self.clock = database, clock
        self.sessions = sessions or database.sessions
        self.calculator = TotalCalculator()

    async def run_due(self, building_id=None):
        """Re-read durable work after common locks and batch all complete eligibleCAT-01 intervals.

        A failed building transaction leaves every request pending and every previous
        category commit intact. Concurrent runs serialize on the001 context lock. Neither
        candidate polling nor an unchanged diagnosis extends revision or retention.
        """
        async with UnitOfWork(self.sessions) as uow:
            requested = set((await uow.session.scalars(select(TotalEvaluationRequest.building_id).where(TotalEvaluationRequest.status == 'pending'))).all())
            requested.update((await uow.session.scalars(select(TotalCalculationState.building_id).where(TotalCalculationState.status == 'pending'))).all())
        if building_id is not None: requested.intersection_update({building_id})
        for selected in sorted(requested, key=str): await self._building(selected)

    async def _building(self, building_id):
        """Evaluate requests/candidates in one locked transaction; mark processed only with their result."""
        async with UnitOfWork(self.sessions) as uow:
            building, states, global_state, revisions = await lock_history(uow, building_id)
            now, state = utc(self.clock.now()), states['CAT-01']
            deadline = retention_deadline(now, building.timezone)
            requests = (await uow.session.scalars(select(TotalEvaluationRequest).where(
                TotalEvaluationRequest.building_id == building_id, TotalEvaluationRequest.status == 'pending')
                .order_by(TotalEvaluationRequest.start, TotalEvaluationRequest.end).with_for_update())).all()
            pending = (await uow.session.scalars(select(TotalCalculationState).where(
                TotalCalculationState.building_id == building_id, TotalCalculationState.status == 'pending')
                .order_by(TotalCalculationState.start, TotalCalculationState.end).with_for_update())).all()
            windows = sorted({(r.start, r.end) for r in requests + pending})
            candidates = []
            for start, end in windows:
                diagnostic = await uow.session.scalar(select(TotalCalculationState).where(
                    TotalCalculationState.building_id == building_id, TotalCalculationState.start == start,
                    TotalCalculationState.end == end).with_for_update())
                if diagnostic and diagnostic.status == 'incorporated': continue
                previous_revision = diagnostic.revision if diagnostic else None
                evidence = (await uow.session.scalars(select(IncorporatedRecord).where(
                    IncorporatedRecord.building_id == building_id, IncorporatedRecord.kind == 'measured',
                    IncorporatedRecord.category_id != 'CAT-01', IncorporatedRecord.start == start, IncorporatedRecord.end == end)
                    .order_by(IncorporatedRecord.category_id))).all()
                contributions = tuple(Contribution(measurement_id=r.id, measurement_revision=r.revision,
                    category_id=r.category_id, source_id=r.source_id, category_revision=r.category_revision,
                    start=r.start, end=r.end, energy_kwh=r.energy_kwh) for r in evidence)
                candidate = self.calculator.evaluate(building_id=building_id, start=start, end=end,
                    segments=configuration_segments(revisions, 'CAT-01', start, end), contributions=contributions)
                status = 'pending' if candidate.status == 'complete' else candidate.status
                reason = 'pending_incorporation' if status == 'pending' else candidate.reason_code
                next_at = state.next_admissible_at if status == 'pending' else None
                values = dict(status=status, reason_code=reason,
                    configuration_segments=[s.model_dump(mode='json') for s in candidate.configuration_segments],
                    base_categories=list(candidate.base_categories), contribution_refs=[c.model_dump(mode='json') for c in candidate.contributions],
                    missing_categories=list(candidate.missing_categories), next_admissible_at=next_at, incorporated_record_id=None)
                if diagnostic is None:
                    diagnostic = TotalCalculationState(id=uuid4(), building_id=building_id, start=start, end=end,
                        revision=1, updated_at=now, retain_until=deadline, **values)
                    uow.session.add(diagnostic)
                elif any(getattr(diagnostic, field) != value for field, value in values.items()):
                    for field, value in values.items(): setattr(diagnostic, field, value)
                    diagnostic.updated_at, diagnostic.revision = now, diagnostic.revision + 1
                    diagnostic.retain_until = max(diagnostic.retain_until, deadline)
                await protect_contributions(uow, candidate.contributions, diagnostic.retain_until)
                await uow.session.flush()
                for part in candidate.contributions:
                    if not await uow.session.get(CalculationContributionReference, (diagnostic.id, part.measurement_id)):
                        uow.session.add(CalculationContributionReference(candidate_id=diagnostic.id, record_id=part.measurement_id))
                if candidate.status == 'complete' and (state.next_admissible_at is None or now >= state.next_admissible_at):
                    candidates.append((candidate, diagnostic, previous_revision))
            if candidates:
                update = CategoryUpdate(id=uuid4(), attempt_id=None, building_id=building_id, category_id='CAT-01',
                    kind='calculated', evaluated_at=now, new_data_at=now, previous_new_data_at=state.last_new_data_at,
                    next_admissible_at=None, accepted_count=len(candidates), duplicate_count=0, rejected_count=0, revision=1, retain_until=deadline)
                uow.session.add(update)
                await uow.session.flush()
                records = []
                for candidate, diagnostic, previous_revision in candidates:
                    # Immutable configuration + accepted nonoverlapping partials cannot produce
                    # overlapping valid candidates. PostgreSQL still enforces ledger exclusion.
                    record = await _incorporate(uow, candidate, diagnostic, update, now, building.timezone, str(diagnostic.id))
                    if previous_revision is not None and diagnostic.revision == previous_revision: diagnostic.revision += 1
                    diagnostic.retain_until = max(diagnostic.retain_until, deadline)
                    diagnostic.status, diagnostic.reason_code = 'incorporated', None
                    diagnostic.next_admissible_at, diagnostic.incorporated_record_id = None, record.id
                    diagnostic.updated_at = now
                    records.append(record)
                advance_state(state, global_state, records, now)
                update.next_admissible_at = state.next_admissible_at
                await append_update_events(uow, update, records, [], str(update.id), self.clock, building.timezone)
            await self._finish_requests(uow, requests, now)
            await uow.session.flush()
            await uow.commit()

    async def _finish_requests(self, uow, requests, now):
        """Mark work processed after its result is flushed, in the same transaction; failures roll both back."""
        await uow.session.flush()
        for request in requests:
            request.status, request.processed_at = 'processed', now

    async def loop(self, app, *, interval=5):
        """Recover immediately, then poll with cancellable bounded monotonic waits; revalidate UTC each run.

        Failure leaves durable work for retry and a safe in-process health flag; the
        technical emitter belongs to007. No raw exception/body is logged here.
        """
        if not 0 < interval <= 60: raise ValueError('invalid_poll_interval')
        while True:
            try:
                await self.run_due()
                app.state.consumption_recovery_error = None
            except Exception:
                app.state.consumption_recovery_error = 'total_recovery_failed'
            await asyncio.sleep(interval)

    @asynccontextmanager
    async def lifespan(self, app):
        """Own and cancel/join the local recovery task through009's existing module lifecycle."""
        task = asyncio.create_task(self.loop(app), name='consumption-pending-totals')
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError): await task
