"""PostgreSQL constraints defend002 state, exclusion and permanent identity even without services."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def test_history_schema_constraints(database):
    """All13 domain tables, GiST exclusion, unique evaluation requests and RESTRICT FKs exist."""
    names = ('reception_attempt', 'category_update', 'reception_record_result', 'building_reception_state',
        'category_reception_state', 'incorporated_record', 'accepted_measurement', 'incorporated_total',
        'total_calculation_state', 'total_evaluation_request', 'consumption_aggregate', 'aggregate_contribution', 'calculation_contribution_reference')
    async with UnitOfWork(database.sessions) as uow:
        for name in names:
            assert await uow.session.scalar(text('SELECT to_regclass(:name)'), {'name': name}) == name
        constraints = (await uow.session.execute(text("SELECT contype, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='incorporated_record'::regclass"))).all()
        assert any(kind == 'x' and 'tstzrange' in definition for kind, definition in constraints)
        assert all('CASCADE' not in definition for kind, definition in constraints if kind == 'f')
        assert await uow.session.scalar(text("SELECT count(*) FROM pg_constraint WHERE conrelid='total_evaluation_request'::regclass AND contype='u'")) == 1


async def test_schema_rejects_overlap_and_allows_contiguity(history_environment, database):
    """Direct SQL clone attempts prove the database exclusion independently of admission checks."""
    from backend.tests.unit.consumption.test_validation import record
    await history_environment.accept(uuid4(), record()['building_id'], 'schema', 'process:history_test', [record()], 'schema')
    async with UnitOfWork(database.sessions) as uow:
        columns = (await uow.session.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name='incorporated_record' ORDER BY ordinal_position"))).all()
    columns_sql = ', '.join('"' + c + '"' for c in columns)
    expressions = ', '.join(':id' if c == 'id' else '"' + c + '"' for c in columns)
    with pytest.raises(IntegrityError):
        async with UnitOfWork(database.sessions) as uow:
            await uow.session.execute(text(f'INSERT INTO incorporated_record ({columns_sql}) SELECT {expressions} FROM incorporated_record LIMIT 1'), {'id': uuid4()})
            await uow.commit()


async def test_database_rejects_invalid_states_and_protects_evidence(history_environment, database):
    """State CHECKs, unique positions, immutable manifests and RESTRICT references hold independently from services."""
    from sqlalchemy import delete, select
    from ecs_ec.consumption.models import IncorporatedRecord, ReceptionAttempt, ReceptionRecordResult
    from ecs_ec.consumption.catalog_storage import InstallationRow
    from backend.tests.contract.consumption.test_reception_contract import BUILDING, publish
    from backend.tests.unit.consumption.test_validation import record
    result = await publish(history_environment, [record()])
    attempt, record_id = result.attempt_id, result.results[0].measurement_id
    statements = [
        ("UPDATE reception_attempt SET status='unknown' WHERE id=:id", attempt),
        ("UPDATE reception_attempt SET input_manifest='{}'::jsonb WHERE id=:id", attempt),
        ("UPDATE reception_attempt SET input_schema_version=0 WHERE id=:id", attempt),
        ("UPDATE incorporated_record SET energy_quanta=1.5 WHERE id=:id", record_id),
        ("UPDATE incorporated_record SET kind='calculated' WHERE id=:id", record_id),
        ("UPDATE incorporated_record SET category_revision=0 WHERE id=:id", record_id),
        ("UPDATE category_reception_state SET next_admissible_at=last_new_data_at WHERE building_id=:id", BUILDING),
        ("DELETE FROM incorporated_record WHERE id=:id", record_id),
        ("DELETE FROM consumption_installation WHERE building_id=:id", BUILDING),
    ]
    for statement, identifier in statements:
        with pytest.raises(IntegrityError):
            async with UnitOfWork(database.sessions) as uow:
                await uow.session.execute(text(statement), {'id': identifier})
                await uow.commit()
    async with UnitOfWork(database.sessions) as uow:
        row = (await uow.session.scalars(select(ReceptionRecordResult).where(ReceptionRecordResult.attempt_id == attempt))).one()
        values = {c.name: getattr(row, c.name) for c in ReceptionRecordResult.__table__.columns}
    values['id'] = uuid4()
    with pytest.raises(IntegrityError):
        async with UnitOfWork(database.sessions) as uow:
            uow.session.add(ReceptionRecordResult(**values))
            await uow.commit()
