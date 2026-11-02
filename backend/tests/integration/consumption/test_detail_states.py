"""Real002 incorporation distinguishes source absence, zero, pending totals and physical general data."""

from uuid import UUID

import pytest

from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration
START, END, ZONE = '2025-12-31T21:00:00-03:00', '2025-12-31T23:00:00-03:00', 'America/Santiago'


async def test_calculated_missing_then_complete(consumption_reception_environment, database, clock):
    """Only confirmed contributions produce20kWh; reading an incomplete total never incorporates it."""
    env, service = consumption_reception_environment, facade(database, clock)
    assert (await service.detail('CAT-02', START, END, ZONE)).state == 'no_meter'
    assert (await service.detail('CAT-05', START, END, ZONE)).state == 'no_data'
    await env.publish([record(value='12')])
    incomplete = await service.detail('CAT-01', START, END, ZONE)
    assert incomplete.state == 'incomplete' and not incomplete.rows
    assert incomplete.diagnostics[0].reason_code == 'missing_contributions'
    await env.publish([record(category_id='CAT-03', source_id=UUID(int=3), value='8')])
    complete = await service.detail('CAT-01', START, END, ZONE)
    assert complete.state == 'available' and complete.rows[0].energy_kwh == '20'
    assert complete.rows[0].origin.kind == 'calculated'
    assert {c.energy_kwh for c in complete.rows[0].origin.contributions} == {'12', '8'}


async def test_physical_general_never_uses_partials(history_environment, database, clock):
    """PhysicalCAT-01 stays empty despite partial data; an accepted zero is available, not absent."""
    from backend.tests.contract.consumption.test_reception_contract import publish
    service = facade(database, clock)
    await publish(history_environment, [record(value='0')])
    assert (await service.detail('CAT-01', START, END, ZONE)).state == 'no_data'
    partial = await service.detail('CAT-05', START, END, ZONE)
    assert partial.state == 'available' and partial.rows[0].energy_kwh == '0'


async def test_changed_calculation_signature_keeps_partials(history_environment, database, clock):
    """001 exposes002's captured change segments without inventing a single category revision or missing inputs."""
    from backend.tests.integration.consumption.test_pending_totals import calculated_config
    from backend.tests.contract.consumption.test_reception_contract import publish
    await calculated_config(database, clock)
    await publish(history_environment, [record(start='2026-01-01T00:00:00Z', end='2026-01-01T00:01:00Z')])
    service = facade(database, clock)
    result = await service.detail('CAT-01', START, END, ZONE)
    assert result.state == 'incomplete' and result.rows == ()
    diagnostic = result.diagnostics[0]
    assert diagnostic.category_revision is None and diagnostic.missing_categories == ()
    assert diagnostic.next_admissible_at is None
    assert len({s.category_revision for s in diagnostic.configuration_segments}) == 2
    assert (await service.detail('CAT-05', START, END, ZONE)).rows[0].energy_kwh == '1'


async def test_maximum_calculated_total_survives_wire_projection(history_environment, database, clock):
    """Six physical maxima retain the exact larger calculated domain in001's wire strings."""
    from backend.tests.integration.consumption.test_pending_totals import test_six_maximum_partials_produce_exact_calculated_ceiling
    # Reuse the real-port scenario, whose expected ledger total is independently asserted.
    await test_six_maximum_partials_produce_exact_calculated_ceiling(history_environment, database, clock)
    result = await facade(database, clock).detail('CAT-01', '2026-01-01T21:00:00-03:00', '2026-01-01T22:00:00-03:00', ZONE)
    assert result.rows[0].energy_kwh == '5999999999999999999999999999999.999999999999994'
    assert len(result.rows[0].origin.contributions) == 6


async def test_calculated_zero_and_empty_basis(consumption_reception_environment, database, clock):
    """A nonempty all-zero basis yields actual zero; removing the basis yields no numeric surrogate."""
    from ecs_ec.consumption.configuration import ConfigurationService
    from ecs_ec.consumption.store import MeasurementStore
    from ecs_ec.core.unit_of_work import UnitOfWork
    from backend.tests.unit.consumption.test_catalog import installation
    env = consumption_reception_environment
    await env.publish([record(value='0'), record(category_id='CAT-03', source_id=UUID(int=3), value='0')])
    service = facade(database, clock)
    zero = await service.detail('CAT-01', START, END, ZONE)
    assert zero.state == 'available' and zero.rows[0].energy_kwh == '0'
    clock.advance(3601)
    async with UnitOfWork(database.sessions) as uow:
        await ConfigurationService(clock, MeasurementStore()).apply(uow, building_id=UUID(int=99),
            request=installation(()).model_copy(update={'expected_revision': 2, 'effective_from': None}), actor_ref='process:test')
        await uow.commit()
    empty = await service.detail('CAT-01', '2025-12-31T23:00:00-03:00', '2026-01-01T00:00:00-03:00', ZONE)
    assert empty.state == 'no_data' and empty.rows == ()
    assert any(w.code == 'no_calculation_basis' for w in empty.warnings)
