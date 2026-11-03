"""Acquisition audit commits with its own transitions, while002 remains the durable owner of consumption outcomes."""
import pytest
from sqlalchemy import select,func
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.acquisition.models import PublicationEvaluation
from ecs_ec.audit.models import AuditRecord
from backend.tests.integration.acquisition.test_recovery import service,sealed

pytestmark=pytest.mark.integration


async def test_result_copy_and_audit_rollback_together(acquisition_environment,monkeypatch):
    """A failed audit cannot confirm003's result copy; recovery reads the completed002 outcome and records audit exactly once."""
    import ecs_ec.acquisition.service as producer
    env=acquisition_environment;acquisition=service(env)
    publication=await sealed(env)
    original=producer.append_audit
    async def fail(*args,**kwargs):
        """Abort the audit after the actual002 outcome exists, without exposing the synthetic error publicly."""
        raise RuntimeError('synthetic_audit_failure')
    monkeypatch.setattr(producer,'append_audit',fail)
    with pytest.raises(RuntimeError):await acquisition.process_sealed(publication)
    async with UnitOfWork(env['database'].sessions) as uow:
        evaluation=(await uow.session.scalars(select(PublicationEvaluation))).one()
        identifier=evaluation.id
        assert evaluation.outcome is None and evaluation.state=='processing'
        assert not await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(AuditRecord.entity_id==identifier))
    monkeypatch.setattr(producer,'append_audit',original)
    outcome=await acquisition.process_sealed(publication)
    assert outcome['results'][0]['status']=='accepted'
    await acquisition.process_sealed(publication)
    async with UnitOfWork(env['database'].sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(AuditRecord.entity_id==identifier))==1
