"""Failure injection asserts committed category results and pending work survive reconstruction."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ecs_ec.audit.events import EventWriter
from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.consumption.reception import Reception
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_reception_contract import BUILDING, PROCESS, publish
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


async def test_event_failure_rolls_back_category_and_resume_only_missing(history_environment, database, clock, monkeypatch):
    """Failure after record/aggregrate flush leaves no acceptance; same attempt resumes later."""
    original = EventWriter.append
    async def fail(self, uow, event):
        """Inject a failed producer after its writes but before transaction commit."""
        if event.event_type == 'consumption.accepted': raise RuntimeError('synthetic_event_failure')
        return await original(self, uow, event)
    attempt = uuid4()
    monkeypatch.setattr(EventWriter, 'append', fail)
    with pytest.raises(RuntimeError, match='synthetic_event_failure'):
        await publish(history_environment, [record()], attempt=attempt)
    lookup = await history_environment.read_attempt(attempt, BUILDING, PROCESS)
    assert lookup.state == 'partial_failure' and lookup.outcome.pending_positions == (0,)
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(IncorporatedRecord)) == 0
    monkeypatch.setattr(EventWriter, 'append', original)
    reconstructed = Reception(database, clock, authorized_processes={PROCESS: {BUILDING}})
    outcome = await publish(reconstructed, [record()], attempt=attempt)
    assert outcome.results[0].status == 'accepted'
    assert await publish(reconstructed, [record()], attempt=attempt) == outcome
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(FunctionalEvent.event_type == 'consumption.accepted')) == 1


async def test_partial_commit_survives_lost_response(history_environment, database, clock, monkeypatch):
    """Crash after category commit leaves immutable original recoverable without new data/events."""
    attempt = uuid4()
    original = history_environment._complete
    async def crash(*args):
        """Stop between category commit and final attempt summary, as a dropped response would."""
        raise RuntimeError('lost_response')
    monkeypatch.setattr(history_environment, '_complete', crash)
    with pytest.raises(RuntimeError, match='lost_response'): await publish(history_environment, [record()], attempt=attempt)
    lookup = await history_environment.read_attempt(attempt, BUILDING, PROCESS)
    assert lookup.outcome.results[0].status == 'accepted'
    assert lookup.outcome.pending_positions == ()
    monkeypatch.setattr(history_environment, '_complete', original)
    recovered = await publish(history_environment, [record()], attempt=attempt)
    assert recovered.results[0] == lookup.outcome.results[0] and recovered.state == 'completed'


async def test_failure_between_categories_preserves_original_commit(history_environment, database, clock, monkeypatch):
    """A later category failure never reclassifies or rolls back earlier committed positions."""
    from uuid import UUID
    original = history_environment._category
    async def fail_second(attempt, building, category, *args):
        """FailCAT-05 afterCAT-03 committed, then allow recovery to process onlyCAT-05."""
        if category == 'CAT-05': raise RuntimeError('between_categories')
        return await original(attempt, building, category, *args)
    attempt = uuid4()
    records = [record(category_id='CAT-03', source_id=UUID(int=3)), record()]
    monkeypatch.setattr(history_environment, '_category', fail_second)
    with pytest.raises(RuntimeError, match='between_categories'): await publish(history_environment, records, attempt=attempt)
    partial = await history_environment.read_attempt(attempt, BUILDING, PROCESS)
    assert partial.outcome.pending_positions == (1,)
    accepted = partial.outcome.results[0]
    monkeypatch.setattr(history_environment, '_category', original)
    complete = await publish(history_environment, records, attempt=attempt)
    assert complete.results[0] == accepted
    assert all(r.status == 'accepted' for r in complete.results)
