"""CAT-01 evaluations survive crashes before candidates and publish backlog in one timed update."""

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import select

from ecs_ec.consumption.catalog_storage import read_revisions
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.models import ConfigurationInput, IncorporatedRecord, SourceInput, TotalCalculationState, TotalEvaluationRequest
from ecs_ec.consumption.pending_totals import PendingTotals
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import BUILDING, publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def calculated_config(database, clock):
    """Switch001 to calculatedCAT-01 with CAT-03/05 basis through real configuration, not SQL."""
    clock.advance(1)
    async with UnitOfWork(database.sessions) as uow:
        previous = (await read_revisions(uow, BUILDING))[-1]
        entries = tuple(SourceInput(category_id=e.category_id, has_meter=e.category_id in ('CAT-03', 'CAT-05'),
            source_id=e.source_id if e.category_id in ('CAT-03', 'CAT-05') else None,
            source_label=e.source_label if e.category_id in ('CAT-03', 'CAT-05') else None) for e in previous.categories)
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=BUILDING,
            request=ConfigurationInput(expected_revision=previous.revision, effective_from=None, timezone=previous.timezone, categories=entries),
            actor_ref='process:history_test')
        await uow.commit()


def partials(start='2026-01-02T00:00:00Z', end='2026-01-02T01:00:00Z'):
    """Return two aligned source readings; independent expectedCAT-01 energy is3kWh."""
    return [record(start=start, end=end, category_id='CAT-03', source_id=UUID(int=3), value='2'), record(start=start, end=end)]


async def test_missing_request_recovery_pending_backlog_and_concurrency(history_environment, database, clock):
    """A fresh worker recovers committed work without re-send, then batches due totals after900s."""
    await calculated_config(database, clock)
    rows = partials()
    await publish(history_environment, rows[:1])
    worker = PendingTotals(database, clock)
    await worker.run_due()
    async with UnitOfWork(database.sessions) as uow:
        state = (await uow.session.scalars(select(TotalCalculationState))).one()
        assert state.status == 'incomplete' and state.missing_categories == ['CAT-05']
    await publish(history_environment, rows[1:])
    await worker.run_due()
    async with UnitOfWork(database.sessions) as uow:
        total = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).one()
        assert total.energy_kwh == 3
    # A new interval in both categories only becomes eligible after their independent900s.
    clock.advance(900)
    await publish(history_environment, partials('2026-01-03T00:00:00Z', '2026-01-03T01:00:00Z'))
    # ForceCAT-01 later than the source acceptance by making its last acceptance happen
    # at the current clock, then creating additional history in the same eligible source batch.
    await worker.run_due()
    clock.advance(900)
    await publish(history_environment, partials('2026-01-04T00:00:00Z', '2026-01-04T01:00:00Z') + partials('2026-01-05T00:00:00Z', '2026-01-05T01:00:00Z'))
    await asyncio.gather(worker.run_due(), PendingTotals(database, clock).run_due())
    async with UnitOfWork(database.sessions) as uow:
        totals = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()
        assert len(totals) == 4
        assert totals[-1].update_id == totals[-2].update_id
        assert all(r.status == 'processed' for r in (await uow.session.scalars(select(TotalEvaluationRequest))).all())


async def test_pending_has_no_numeric_record_until_exact_boundary(history_environment, database, clock, monkeypatch):
    """Delayed first evaluation leavesCAT-01's own limit later than the partial-source limits."""
    await calculated_config(database, clock)
    original = history_environment._evaluate
    async def crash(*args):
        """Simulate a crash after partial commits before even a candidate is created."""
        raise RuntimeError('before_candidate')
    monkeypatch.setattr(history_environment, '_evaluate', crash)
    with pytest.raises(RuntimeError, match='before_candidate'): await publish(history_environment, partials())
    async with UnitOfWork(database.sessions) as uow:
        assert len((await uow.session.scalars(select(TotalEvaluationRequest).where(TotalEvaluationRequest.status == 'pending'))).all()) == 1
        assert not (await uow.session.scalars(select(TotalCalculationState))).all()
    clock.advance(300)
    await PendingTotals(database, clock).run_due()
    monkeypatch.setattr(history_environment, '_evaluate', original)
    clock.advance(600)
    await publish(history_environment, partials('2026-01-03T00:00:00Z', '2026-01-03T01:00:00Z') + partials('2026-01-04T00:00:00Z', '2026-01-04T01:00:00Z'))
    async with UnitOfWork(database.sessions) as uow:
        states = (await uow.session.scalars(select(TotalCalculationState).where(TotalCalculationState.status == 'pending'))).all()
        assert len(states) == 2
        before = [(s.id, s.revision, s.retain_until, s.next_admissible_at) for s in states]
        assert len((await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()) == 1
    clock.advance(299)
    await PendingTotals(database, clock).run_due()
    async with UnitOfWork(database.sessions) as uow:
        states = (await uow.session.scalars(select(TotalCalculationState).where(TotalCalculationState.status == 'pending'))).all()
        assert [(s.id, s.revision, s.retain_until, s.next_admissible_at) for s in states] == before
    clock.advance(1)
    await asyncio.gather(PendingTotals(database, clock).run_due(), PendingTotals(database, clock).run_due())
    async with UnitOfWork(database.sessions) as uow:
        totals = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated').order_by(IncorporatedRecord.start))).all()
        assert len(totals) == 3 and totals[1].update_id == totals[2].update_id
        assert totals[1].first_incorporated_at == clock.now()


async def test_worker_result_and_processed_marker_rollback_together(history_environment, database, clock, monkeypatch):
    """A fault exactly between result flush and processed marker preserves durable recovery work."""
    await calculated_config(database, clock)
    async def before_candidate(*args):
        """Leave the committed partials' request for a new worker instance to recover."""
        raise RuntimeError('before_candidate')
    monkeypatch.setattr(history_environment, '_evaluate', before_candidate)
    with pytest.raises(RuntimeError): await publish(history_environment, partials())
    worker = PendingTotals(database, clock)
    original = worker._finish_requests
    async def before_processed(uow, requests, now):
        """Assert a calculated result exists inside the uncommitted transaction, then fail."""
        assert len((await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()) == 1
        raise RuntimeError('before_processed')
    monkeypatch.setattr(worker, '_finish_requests', before_processed)
    with pytest.raises(RuntimeError, match='before_processed'): await worker.run_due()
    async with UnitOfWork(database.sessions) as uow:
        assert not (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()
        assert (await uow.session.scalars(select(TotalEvaluationRequest))).one().status == 'pending'
    monkeypatch.setattr(worker, '_finish_requests', original)
    await worker.run_due()
    async with UnitOfWork(database.sessions) as uow:
        assert (await uow.session.scalars(select(TotalEvaluationRequest))).one().status == 'processed'


async def test_new_partial_concurrent_with_evaluation_is_not_lost(history_environment, database, clock):
    """The common context lock includes the new part or reactivates processed work after its commit."""
    await calculated_config(database, clock)
    await publish(history_environment, partials()[:1])
    await asyncio.gather(PendingTotals(database, clock).run_due(), publish(history_environment, partials()[1:]))
    await PendingTotals(database, clock).run_due()
    async with UnitOfWork(database.sessions) as uow:
        assert len((await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()) == 1
        assert (await uow.session.scalars(select(TotalEvaluationRequest))).one().status == 'processed'


async def test_six_maximum_partials_produce_exact_calculated_ceiling(history_environment, database, clock):
    """The six-source total exceeds the physical ceiling legally and keeps every immutable reference."""
    clock.advance(1)
    async with UnitOfWork(database.sessions) as uow:
        previous = (await read_revisions(uow, BUILDING))[-1]
        entries = tuple(SourceInput(**(e.model_dump(exclude={'category_revision'}) |
            ({'has_meter': False, 'source_id': None, 'source_label': None} if e.category_id == 'CAT-01' else {}))) for e in previous.categories)
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=BUILDING,
            request=ConfigurationInput(expected_revision=1, effective_from=None, timezone=previous.timezone, categories=entries),
            actor_ref='process:history_test')
        await uow.commit()
    maximum = '999999999999999999999999999999.999999999999999'
    await publish(history_environment, [record(category_id=f'CAT-{i:02}', source_id=UUID(int=i), value=maximum,
        start='2026-01-02T00:00:00Z', end='2026-01-02T01:00:00Z') for i in range(2, 8)])
    async with UnitOfWork(database.sessions) as uow:
        row = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).one()
        assert int(row.energy_quanta) == 6 * (10**45 - 1)
        assert len(row.provenance_snapshot['contributions']) == 6
        assert row.category_revision == 2 and row.source_id is None


async def test_configuration_change_diagnosis_preserves_segments_without_fake_missing(history_environment, database, clock):
    """A total mode change within a physical partial's stable interval cannot yield a fabricated numeric total."""
    await calculated_config(database, clock)
    await publish(history_environment, [record(start='2026-01-01T00:00:00Z', end='2026-01-01T00:01:00Z')])
    async with UnitOfWork(database.sessions) as uow:
        diagnosis = (await uow.session.scalars(select(TotalCalculationState))).one()
        assert diagnosis.status == 'incomplete' and diagnosis.reason_code == 'calculation_configuration_changed'
        assert diagnosis.base_categories == diagnosis.missing_categories == []
        assert diagnosis.next_admissible_at is None and len(diagnosis.configuration_segments) == 2
        assert not (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()


async def test_unrelated_global_revision_and_misaligned_partial(history_environment, database, clock):
    """A label-only revision preserves the total signature; subintervals cannot fake aligned contributions."""
    await calculated_config(database, clock)
    clock.advance(1)
    async with UnitOfWork(database.sessions) as uow:
        previous = (await read_revisions(uow, BUILDING))[-1]
        entries = tuple(SourceInput(**(e.model_dump(exclude={'category_revision'}) |
            ({'source_label': 'Updated synthetic meter'} if e.has_meter else {}))) for e in previous.categories)
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=BUILDING,
            request=ConfigurationInput(expected_revision=previous.revision, effective_from=None, timezone=previous.timezone, categories=entries),
            actor_ref='process:history_test')
        await uow.commit()
    await publish(history_environment, partials('2026-01-01T00:00:01Z', '2026-01-01T00:01:00Z'))
    async with UnitOfWork(database.sessions) as uow:
        total = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).one()
        assert total.energy_kwh == 3 and len(total.provenance_snapshot['configuration_segments']) == 2
    clock.advance(900)
    await publish(history_environment, [partials('2026-01-02T00:00:00Z', '2026-01-02T01:00:00Z')[0],
        partials('2026-01-02T00:00:00Z', '2026-01-02T00:30:00Z')[1]])
    async with UnitOfWork(database.sessions) as uow:
        assert len((await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()) == 1
        assert len((await uow.session.scalars(select(TotalCalculationState).where(TotalCalculationState.status == 'incomplete'))).all()) == 2


async def test_empty_basis_and_physical_total_never_create_substitute(history_environment, database, clock):
    """Without a logical source no zero is invented; a physicalCAT-01 stays independent from partial sums."""
    await publish(history_environment, [record(category_id='CAT-01', source_id=UUID(int=1), value='100'),
        record(category_id='CAT-03', source_id=UUID(int=3), value='20'), record(value='40')])
    async with UnitOfWork(database.sessions) as uow:
        totals = (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.category_id == 'CAT-01'))).all()
        assert len(totals) == 1 and totals[0].kind == 'measured' and totals[0].energy_kwh == 100
        assert not (await uow.session.scalars(select(TotalEvaluationRequest))).all()
    # Replace all sources only after the accepted maximum interval end, using real bounds.
    from ecs_ec.consumption.models import instant
    clock.instant = instant('2026-01-01T02:00:00Z')
    async with UnitOfWork(database.sessions) as uow:
        previous = (await read_revisions(uow, BUILDING))[-1]
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=BUILDING,
            request=ConfigurationInput(expected_revision=previous.revision, effective_from=None, timezone=previous.timezone,
                categories=tuple(SourceInput(category_id=e.category_id, has_meter=False, source_id=None, source_label=None) for e in previous.categories)),
            actor_ref='process:history_test')
        await uow.commit()
    outcome = await publish(history_environment, partials())
    assert all(r.status == 'rejected' and r.reason_code == 'unknown_or_uninstalled_source' for r in outcome.results)
    async with UnitOfWork(database.sessions) as uow:
        assert not (await uow.session.scalars(select(TotalEvaluationRequest))).all()
        assert not (await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.kind == 'calculated'))).all()
