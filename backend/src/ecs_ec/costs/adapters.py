"""004 safe evidence schemas on009's shared durable audit/event tables, independent of008."""

from typing import Literal
from uuid import UUID, uuid4

from ecs_ec.audit.events import Code, EventInput, EventWriter, Interval, PayloadRegistry, SafePayload
from ecs_ec.audit.services import AuditInput, FunctionalAudit


class CostsEvidence(SafePayload):
    """Closed safe functional metadata, without financial values, request bodies or exception messages."""

    building_id: UUID
    entity_id: UUID
    revision: int
    functional_result: Literal['recorded', 'failed']
    reason_code: Code
    category_id: Literal['CAT-01'] = 'CAT-01'


class Evidence:
    """Append audit/event records in the caller's transaction; a consumer is never required."""

    def __init__(self, clock, timezone):
        """Register owned actions and cost.failed in the common trusted composition registry."""
        registry = PayloadRegistry()
        for action in ('costs.supply.changed', 'costs.profile.created', 'costs.calculation.created', 'costs.bill.created', 'costs.comparison.created'):
            registry.register(action, CostsEvidence, results={'recorded', 'failed'})
        registry.register('cost.failed', CostsEvidence)
        self.audit, self.events, self.clock = FunctionalAudit(registry, clock, timezone), EventWriter(registry, clock, timezone), clock

    async def append(self, uow, *, building_id, row, action, failed=False, window=None):
        """Flush result/audit and optional failed event atomically, without committing or networking."""
        payload = CostsEvidence(building_id=building_id, entity_id=row.id, revision=row.revision,
            functional_result='failed' if failed else 'recorded', reason_code='engine_failed' if failed else 'recorded').model_dump()
        await self.audit.append(uow, AuditInput(actor_ref=row.actor_ref, action=action, entity_type='costs.resource',
            entity_id=row.id, entity_revision=row.revision, occurred_at=self.clock.now(),
            result=payload['functional_result'], safe_payload=payload))
        if failed:
            await self.events.append(uow, EventInput(event_id=uuid4(), type='cost.failed', source_module='costs',
                source_entity_id=row.id, source_revision=row.revision, occurred_at=self.clock.now(),
                measurement_window=Interval(start=window.start, end=window.end) if window else None,
                accepted_new_data=False, safe_payload=payload, correlation_ref=str(row.id)))
