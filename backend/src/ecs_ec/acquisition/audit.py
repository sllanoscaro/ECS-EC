"""Acquisition-owned functional audit schemas; never publish unregistered common event types."""
from typing import Literal
from uuid import UUID
from ecs_ec.audit.events import PayloadRegistry,SafePayload
from ecs_ec.audit.services import AuditInput,FunctionalAudit


class AcquisitionAudit(SafePayload):
    """Closed producer facts, excluding filenames, remote identities, tokens and measurements."""
    phase:Literal['binding','sealed','aborted','evaluated']
    reference:UUID


async def append_audit(uow,clock,zone,phase,reference):
    """Append acquisition status in the caller's transaction; audit failure rolls back that transition."""
    registry=PayloadRegistry()
    registry.register('acquisition.changed',AcquisitionAudit,results=('allowed',))
    await FunctionalAudit(registry,clock,zone).append(uow,AuditInput(actor_ref='process:acquisition',
        action='acquisition.changed',entity_type='acquisition',entity_id=reference,entity_revision=1,
        occurred_at=clock.now(),result='allowed',safe_payload={'phase':phase,'reference':reference}))
