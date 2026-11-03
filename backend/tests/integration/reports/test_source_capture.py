"""005 integration of the installed002/004/006 ports on the guarded PostgreSQL fixture."""

import pytest
from sqlalchemy import text

from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from ecs_ec.consumption.models import instant
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.snapshots import capture_sources

pytestmark = pytest.mark.integration


async def test_capture_real_sources(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """A real1000kWh calculation and seven-category producer share one005 capture, with no SMTP."""
    client, env = costs_client, costs_environment
    body = await prepared(env)
    headers = await authenticate(client, account_factory, session_factory, identity_settings)
    response = await client.post('/api/v1/costs/calculations', json=body, headers=headers)
    assert response.status_code == 201
    service = client._transport.app.state.costs
    principal = await service.identity.resolve_session(client.cookies['ecs_ec_session'])
    async with UnitOfWork(env['database'].sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        snapshot = await capture_sources(identity=service.identity, consumption=env['consumption'], costs=service,
            building_id=env['building_id'], start=instant('2025-12-01T03:00:00Z'), end=instant('2026-01-01T03:00:00Z'),
            scale='mensual', cutoff_at=env['clock'].now(), principal=principal, unit_of_work=uow)
        assert len(snapshot['totals']['categories']) == len(snapshot['chart']['categories']) == 7
        assert str(snapshot['financial'].cycles[0].calculation.id) == response.json()['id']
        assert snapshot['financial'].comparison_totals == ()
        assert snapshot['financial'].cycles[0].bill is None
        general = snapshot['totals']['categories'][0]
        assert general['aggregates'].blocks[0].energy_kwh == '1000'


async def test_capture_requires_repeatable_read(costs_client, costs_environment, account_factory, session_factory, identity_settings):
    """READ COMMITTED must fail before invoking either data provider."""
    client, env = costs_client, costs_environment
    await authenticate(client, account_factory, session_factory, identity_settings)
    service = client._transport.app.state.costs
    principal = await service.identity.resolve_session(client.cookies['ecs_ec_session'])
    async with UnitOfWork(env['database'].sessions) as uow:
        with pytest.raises(ValueError, match='snapshot_isolation_required'):
            await capture_sources(identity=service.identity, consumption=env['consumption'], costs=service,
                building_id=env['building_id'], start=instant('2025-12-01T03:00:00Z'), end=instant('2026-01-01T03:00:00Z'),
                scale='mensual', cutoff_at=env['clock'].now(), principal=principal, unit_of_work=uow)
