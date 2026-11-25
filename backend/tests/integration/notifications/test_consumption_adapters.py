"""008 adapters consume installed001/002 quality and source metadata without implementing energy arithmetic."""

from ecs_ec.notifications.adapters import ConsumptionAdapter


async def test_missing_source_is_explicit(history_environment, database, clock):
    """A configured category without source has no invented energy and no arrival SLA derived from900seconds."""
    from uuid import UUID

    from ecs_ec.consumption.queries import Consumption
    from ecs_ec.consumption.store import MeasurementStore

    source = Consumption(database, clock, UUID(int=99), MeasurementStore())
    adapter = ConsumptionAdapter(source)
    state = await adapter.source_status("CAT-07", cutoff_at=clock.now())
    assert state["category_id"] == "CAT-07"
    assert state["last_new_data_at"] is None


async def test_real_latest_window_keeps_known_value_and_cursor(
    history_environment, database, clock
):
    """008's hora maps to the owner's hour;2kWh from accepted002 evidence stays2, with complete provenance and stable replay."""
    from uuid import UUID

    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.notifications.schemas import instant

    from backend.tests.contract.consumption.test_reception_contract import publish
    from backend.tests.integration.consumption.test_detail_queries import facade
    from backend.tests.unit.consumption.test_validation import record

    await publish(history_environment, [record(value="2")])
    clock.advance(7200)
    adapter = ConsumptionAdapter(facade(database, clock))
    async with UnitOfWork(database.sessions) as uow:
        selection = dict(
            building_id=UUID(int=99),
            category_id="CAT-05",
            resolution="hora",
            timezone="UTC",
            activation_at=instant("2025-01-01T00:00:00Z"),
            cursor=None,
            cutoff_at=clock.now(),
            unit_of_work=uow,
        )
        result = await adapter.latest_admissible_window(**selection)
        assert result.status == "available" and result.energy_kwh == "2"
        assert (
            result.period.end == instant("2026-01-01T01:00:00Z") and result.record_refs
        )
        replay = await adapter.latest_admissible_window(
            **(selection | {"cursor": result.cursor})
        )
        assert replay.evidence_revision == result.evidence_revision


async def test_real_calculated_total_and_base_are_owned_by_consumption(
    consumption_reception_environment, database, clock
):
    """Real002 contributes12+8→CAT01=20;008 consumes its calculated total and recorded basis without recomputing it."""
    from uuid import UUID

    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.notifications.schemas import instant

    from backend.tests.integration.consumption.test_detail_queries import facade
    from backend.tests.unit.consumption.test_validation import record

    await consumption_reception_environment.publish(
        [
            record(value="12"),
            record(category_id="CAT-03", source_id=UUID(int=3), value="8"),
        ]
    )
    clock.advance(7200)
    adapter = ConsumptionAdapter(facade(database, clock))
    state = await adapter.source_status("CAT-01", cutoff_at=clock.now())
    assert state["source_mode"] == "calculated" and set(state["base_categories"]) == {
        "CAT-03",
        "CAT-05",
    }
    async with UnitOfWork(database.sessions) as uow:
        result = await adapter.latest_admissible_window(
            building_id=UUID(int=99),
            category_id="CAT-01",
            resolution="hora",
            timezone="UTC",
            activation_at=instant("2025-01-01T00:00:00Z"),
            cursor=None,
            cutoff_at=clock.now(),
            unit_of_work=uow,
        )
        assert (
            result.status == "available"
            and result.energy_kwh == "20"
            and result.source_mode == "calculated"
        )


from backend.tests.contract.consumption.test_history_consumers import (
    test_calculated_general_is_explicit_limitation as test_calculated_general_is_explicit_limitation,
)
from backend.tests.contract.consumption.test_history_consumers import (
    test_window_revision_moves_only_after_late_completion as test_window_revision_moves_only_after_late_completion,
)
