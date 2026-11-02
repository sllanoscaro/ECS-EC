"""Real attempt-aware reception contract; no public injection or persistence doubles."""

from uuid import UUID, uuid4

import pytest

from backend.tests.unit.consumption.test_validation import record
from ecs_ec.consumption.reception import ReceptionError

pytestmark = pytest.mark.integration
PROCESS = 'process:history_test'
BUILDING = UUID(int=99)


async def publish(service, records, *, attempt=None, publication='publication'):
    """Call the trusted internal port with stable order, publication and correlation."""
    return await service.accept(attempt or uuid4(), BUILDING, publication, PROCESS, records, 'test:correlation')


async def test_original_recovery_payload_conflict_and_new_resend(history_environment, clock):
    """Completed outcomes stay original; explicit re-send uses a new UUID even after too_early."""
    service = history_environment
    attempt = uuid4()
    original = await publish(service, [record()], attempt=attempt)
    assert original.results[0].status == 'accepted'
    clock.advance(899)
    fresh = record(start='2025-01-01T01:00:00Z', end='2025-01-01T02:00:00Z')
    early_id = uuid4()
    early = await publish(service, [fresh], attempt=early_id)
    assert early.results[0].reason_code == 'too_early'
    clock.advance(1)
    assert await publish(service, [record()], attempt=attempt) == original
    assert await publish(service, [fresh], attempt=early_id) == early
    with pytest.raises(ReceptionError, match='attempt_payload_conflict'):
        await publish(service, [record(value='2')], attempt=attempt)
    assert (await publish(service, [fresh])).results[0].status == 'accepted'


async def test_authorized_read_has_no_effect_and_missing_is_explicit(history_environment):
    """Lookup neither starts nor resumes; authorization is checked before distinguishing existence."""
    service = history_environment
    attempt = uuid4()
    missing = await service.read_attempt(attempt, BUILDING, PROCESS)
    assert missing.state == 'not_found' and missing.outcome is None
    with pytest.raises(ReceptionError, match='unauthorized_process'):
        await service.read_attempt(attempt, BUILDING, 'process:unknown')
    outcome = await publish(service, [record(), record(category_id='unknown'), record(value='NaN')], attempt=attempt)
    assert [r.position for r in outcome.results] == [0, 1, 2]
    assert [r.status for r in outcome.results] == ['accepted', 'rejected', 'rejected']
    assert (await service.read_attempt(attempt, BUILDING, PROCESS)).outcome == outcome


async def test_database_failure_is_not_not_found(history_environment, database, clock):
    """An unavailable PostgreSQL source raises explicitly; no empty successful lookup is fabricated."""
    from sqlalchemy.exc import OperationalError
    from ecs_ec.core.database import Database
    from ecs_ec.consumption.reception import Reception
    unreachable = Database(database.engine.url.set(port=1))
    try:
        service = Reception(unreachable, clock, authorized_processes={PROCESS: {BUILDING}})
        with pytest.raises(OperationalError): await service.read_attempt(uuid4(), BUILDING, PROCESS)
    finally:
        await unreachable.close()


async def test_input_types_and_authorization_do_not_alias_attempt_identity(history_environment):
    """Typed scalar canonicalization distinguishes number/text/boolean and refuses unbound context or secret fields."""
    service = history_environment
    attempt = uuid4()
    original = await publish(service, [record(value='1')], attempt=attempt)
    for changed in [record(value=1), record(value=True), record(value=1.0)]:
        with pytest.raises(ReceptionError, match='attempt_payload_conflict'): await publish(service, [changed], attempt=attempt)
    with pytest.raises(ReceptionError, match='unauthorized_process'):
        await service.read_attempt(attempt, UUID(int=100), PROCESS)
    with pytest.raises(ReceptionError, match='invalid_attempt_input'):
        await publish(service, [record(token='secret-must-not-persist')])
    assert (await service.read_attempt(attempt, BUILDING, PROCESS)).outcome == original
