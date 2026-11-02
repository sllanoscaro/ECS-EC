"""Controlled provisioning via trusted internal code; no public seed, clock or account endpoints."""

from sqlalchemy.dialects.postgresql import insert

from ecs_ec.consumption.catalog_storage import BuildingRow
from ecs_ec.consumption.configuration import ConfigurationError, ConfigurationService
from ecs_ec.consumption.models import BuildingContext


async def bootstrap(unit_of_work, *, building, configuration, clock, actor_ref, store=None):
    """Provision one explicit context and apply first config; caller commits or rolls back all changes.

    Intended for trusted environment preparation. Existing contexts must match UUID/name;
    replay uses the current expected_revision. Later changes require the real002 provider.
    No credentials, production identifiers or a default building timezone are inferred.
    """
    building = BuildingContext.model_validate(building.model_dump())
    if not actor_ref.startswith("process:"): raise ConfigurationError("bootstrap_process_required")
    await unit_of_work.session.execute(insert(BuildingRow).values(singleton=1, **building.model_dump())
        .on_conflict_do_nothing(index_elements=[BuildingRow.singleton]))
    existing = await unit_of_work.session.get(BuildingRow, building.id)
    if existing is None or existing.name != building.name: raise ConfigurationError("building_context_conflict")
    return await ConfigurationService(clock, store).apply(unit_of_work, building_id=building.id,
        request=configuration, actor_ref=actor_ref)
