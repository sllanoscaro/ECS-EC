"""Transactional001 configuration, safe evidence and fail-closed002 reconfiguration coordination."""

from typing import Literal
from uuid import UUID, uuid4

from ecs_ec.audit.events import EventInput, EventWriter, PayloadRegistry, SafePayload
from ecs_ec.audit.services import AuditInput, FunctionalAudit
from ecs_ec.consumption.catalog import CATEGORY_IDS, category_signature, make_revision
from ecs_ec.consumption.catalog_storage import MeasurementSourceRow, append_revision, lock_configuration, read_revisions
from ecs_ec.consumption.models import CategoryId, ConfigurationInput, ReconfigurationBounds
from ecs_ec.core.clock import utc


class ConfigurationError(ValueError):
    """Safe stable domain code; HTTP mapping belongs to the future authorized adapter."""

    def __init__(self, code):
        """Construct a code-only error without provider exception text or user-entered source labels."""
        self.code = code
        super().__init__(code)


class ConfigurationPayload(SafePayload):
    """Allowlist IDs/revisions/category codes only; source labels/credentials never enter events."""

    building_id: UUID
    configuration_id: UUID
    revision: int
    changed_categories: list[CategoryId]
    reason_code: Literal["configuration_changed"] = "configuration_changed"


async def append_evidence(unit_of_work, revision, changed_categories, clock):
    """Record the administration audit plus two common events in the producer's transaction."""
    registry = PayloadRegistry()
    registry.register("consumption.configuration.changed", ConfigurationPayload, results={"allowed"})
    for code in ("source.changed", "administration.changed"): registry.register(code, ConfigurationPayload)
    payload = ConfigurationPayload(building_id=revision.building_id, configuration_id=revision.id,
        revision=revision.revision, changed_categories=list(changed_categories)).model_dump()
    await FunctionalAudit(registry, clock, revision.timezone).append(unit_of_work, AuditInput(
        actor_ref=revision.created_by, action="consumption.configuration.changed", entity_type="consumption_configuration",
        entity_id=revision.id, entity_revision=revision.revision, occurred_at=revision.recorded_at,
        result="allowed", safe_payload=payload))
    writer = EventWriter(registry, clock, revision.timezone)
    operation_ref = str(uuid4())
    for code in ("source.changed", "administration.changed"):
        await writer.append(unit_of_work, EventInput(event_id=uuid4(), event_type=code, source_module="consumption",
            source_entity_id=revision.id, source_revision=revision.revision, occurred_at=revision.recorded_at,
            safe_payload=payload, correlation_ref=operation_ref))


class ConfigurationService:
    """Apply authorized commands inside caller-owned UoW; session/permission checks stay with006."""

    def __init__(self, clock, store=None):
        """Receive the platform clock and optional002 bounds provider; absence permits only bootstrap/no-op."""
        self.clock, self.store = clock, store

    async def apply(self, unit_of_work, *, building_id, request, actor_ref):
        """Lock, validate bounds and append configuration/evidence atomically; never commit independently.

        Caller must authorize before invoking. Any exception requires rollback of the
        entire UoW, including source/audit flushes; bootstrap supplies a trusted process.
        """
        request = ConfigurationInput.model_validate(request.model_dump())
        building = await lock_configuration(unit_of_work, building_id)
        if building is None: raise ConfigurationError("building_context_missing")
        revisions = await read_revisions(unit_of_work, building_id)
        previous = revisions[-1] if revisions else None
        if request.expected_revision != (previous.revision if previous else 0): raise ConfigurationError("revision_conflict")
        requested = tuple(sorted(request.categories, key=lambda s: s.category_id))
        if previous and previous.timezone == request.timezone and all(
            a.model_dump() == b.model_dump(exclude={"category_revision"}) for a, b in zip(requested, previous.categories, strict=True)):
            return previous
        now = utc(self.clock.now())
        effective = request.effective_from or now
        if previous and effective != now: raise ConfigurationError("effective_time_mismatch")
        if effective > now or (previous and effective <= previous.effective_from):
            raise ConfigurationError("effective_time_conflict")
        changed = tuple(c for c in CATEGORY_IDS if previous is None or
            category_signature(previous.categories, c) != category_signature(requested, c))
        if previous:
            if self.store is None: raise ConfigurationError("reconfiguration_bounds_unavailable")
            try:
                bounds = await self.store.read_reconfiguration_bounds(building_id, changed, unit_of_work)
                bounds = ReconfigurationBounds.model_validate(bounds.model_dump())
                bounds.require_categories(changed)
            except Exception:
                raise ConfigurationError("reconfiguration_bounds_unavailable") from None
            if request.timezone != previous.timezone and bounds.has_accepted_history:
                raise ConfigurationError("timezone_has_history")
            if any(end is not None and effective < end for end in bounds.latest_interval_end_by_category.values()):
                raise ConfigurationError("accepted_interval_conflict")
        elif request.timezone != building.timezone:
            raise ConfigurationError("initial_timezone_mismatch")
        for entry in requested:
            if not entry.has_meter: continue
            source = await unit_of_work.session.get(MeasurementSourceRow, entry.source_id)
            if source and source.building_id != building_id: raise ConfigurationError("source_building_mismatch")
            if source is None:
                unit_of_work.session.add(MeasurementSourceRow(id=entry.source_id, building_id=building_id,
                    label=entry.source_label, created_at=now))
        await unit_of_work.session.flush()
        revision = make_revision(request, building_id=building_id, previous=previous,
            effective_from=effective, recorded_at=now, actor_ref=actor_ref)
        await append_revision(unit_of_work, revision)
        building.timezone = request.timezone
        await append_evidence(unit_of_work, revision, changed, self.clock)
        return revision
