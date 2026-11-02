"""Synthetic004 profiles and real001/002/006 resources on the checked disposable PostgreSQL test database."""

from uuid import UUID

import pytest


@pytest.fixture
async def costs_environment(history_environment, database, clock):
    """Reuse actual002 admission/configuration; no production URL or direct measurement inserts are permitted."""
    from backend.tests.integration.consumption.test_detail_queries import facade
    from ecs_ec.core.unit_of_work import UnitOfWork
    from sqlalchemy import delete
    from ecs_ec.costs.models import Idempotency
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(delete(Idempotency))
        await uow.commit()
    yield dict(database=database, clock=clock, building_id=UUID(int=99), consumption=facade(database, clock), reception=history_environment)
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.execute(delete(Idempotency))
        await uow.commit()


def profile_input(supply_id, *, previous=None, price='100', state='published'):
    """Return a documented synthetic calendar and an energy-only draftable charge set, never a real tariff."""
    return dict(supply_id=str(supply_id), expected_previous_version_id=previous, tariff='BT4.3', currency='CLP',
        publication_state=state, timezone='America/Santiago', source_refs=['synthetic:tariff'], territory_conditions='Synthetic test only',
        required_kinds=['energia'], segments=[dict(valid_from='2025-01-01T00:00:00Z', valid_to=None,
            source_refs=['synthetic:segment'], peak_calendar=dict(version='fixture-peak-v1', months=[4,5,6,7,8,9],
                weekdays=[0,1,2,3,4], start_time='18:00', end_time='22:00', excluded_dates=[]),
            historical_rule='two_monthly_maxima_12_months_v1',
            billing_month_policy=dict(version='fixture-month-v1', mode='explicit_evidence', source_refs=['synthetic:month'], rule_id=None),
            rounding_policy=dict(precision=50, quantum='1', mode='ROUND_HALF_UP', stage='component'),
            charges=[dict(code='energy', kind='energia', quantity_unit='kWh', unit_price=price, tax_basis='neto',
                applicability='always', vigency_strategy='exact_intervals', source_refs=['synthetic:energy'], tax_codes=[])])])


async def seed_supply(database, clock, *, source_id=UUID(int=1), price='100'):
    """Prepare owned004 configuration only; every measurement still goes through the real002 Reception port."""
    from uuid import uuid4
    from ecs_ec.costs.models import Supply
    from ecs_ec.costs.schemas import SupplyInput
    from ecs_ec.costs.profiles import append_profile
    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.core.retention import anniversary
    data = SupplyInput(general_board_ref='synthetic:general-board', category_id='CAT-01', general_source_id=source_id,
        distributor='synthetic', location='synthetic', connection_conditions='synthetic', document_refs=['synthetic:supply'],
        measurement_point_differences=[])
    async with UnitOfWork(database.sessions) as uow:
        supply = Supply(id=uuid4(), building_id=UUID(int=99), revision=1, data=data.model_dump(mode='json'),
            created_at=clock.now(), updated_at=clock.now(), actor_ref='process:costs_fixture',
            retain_until=anniversary(clock.now(), 'America/Santiago'))
        uow.session.add(supply)
        await uow.session.flush()
        await append_profile(uow, supply, profile_input(supply.id, price=price), 'process:costs_fixture', clock)
        await uow.commit()
        return supply


@pytest.fixture
async def costs_client(costs_environment, identity, identity_settings, test_url, tmp_path):
    """Serve real006/004 HTTP with the fixture's explicit building99, sharing the actual PostgreSQL database."""
    import httpx
    from ecs_ec.core.settings import Settings
    from ecs_ec.identity.services import Identity
    from ecs_ec.main import create_app
    env = costs_environment
    settings = identity_settings.model_copy(update={'building_id': UUID(int=99)})
    service = Identity(env['database'], settings, env['clock'], 'America/Santiago')
    (tmp_path/'index.html').write_text('<h1>Synthetic export</h1>')
    app = create_app(Settings(_env_file=None, database_url=test_url, environment='test', public_url=settings.origin,
        web_directory=tmp_path), identity_service=service, clock=env['clock'])
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=settings.origin) as client:
            yield client
