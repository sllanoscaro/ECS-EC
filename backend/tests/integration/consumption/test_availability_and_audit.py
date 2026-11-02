"""001 remains independent of008/SMTP/telemetry; safe failures never look like an empty history."""

import pytest
from sqlalchemy import func, select

from ecs_ec.audit.models import AuditRecord, FunctionalEvent
from ecs_ec.consumption.catalog_storage import InstallationRow
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.contract.consumption.test_http import authenticate
from backend.tests.integration.consumption.test_detail_queries import facade

pytestmark = pytest.mark.integration


async def test_dependency_failure_is503_not_empty_or_validation(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, monkeypatch):
    """A missing/corrupt storage provider returns503; no exception text escapes as422 or no_data."""
    service = facade(database, clock)
    client._transport.app.state.consumption = service
    await authenticate(client, account_factory, session_factory, identity_settings)
    async def unavailable(*args):
        """Simulate a002 functional evidence failure, with synthetic text that must never be reflected."""
        raise ValueError('synthetic-secret-storage-error')
    monkeypatch.setattr(service.store, 'read_detail', unavailable)
    response = await client.get('/api/v1/consumption/categories/CAT-05/detail', params={
        'start': '2025-12-31T21:00:00-03:00', 'end': '2025-12-31T22:00:00-03:00', 'timezone': 'America/Santiago'})
    assert response.status_code == 503
    assert response.headers['cache-control'] == 'no-store'
    assert 'synthetic-secret' not in response.text


async def test_configuration_event_rollback_and_absent_consumers(client, account_factory, session_factory,
        identity_settings, history_environment, database, clock, monkeypatch):
    """Configuration commits without external consumers; an injected writer failure rolls back all flushed evidence."""
    from ecs_ec.audit.events import EventWriter
    from ecs_ec.consumption.configuration import ConfigurationError
    service = facade(database, clock)
    client._transport.app.state.consumption = service
    headers = await authenticate(client, account_factory, session_factory, identity_settings, role='administrador_tecnico')
    current = (await client.get('/api/v1/consumption/configuration')).json()
    command = dict(expected_revision=current['revision'], effective_from=None, timezone=current['timezone'],
        categories=[{k: v for k, v in c.items() if k != 'category_revision'} for c in current['categories']])
    command['categories'][4]['source_label'] = 'Synthetic changed label'
    clock.advance(1)
    original = EventWriter.append
    async def fail(self, uow, event):
        """Fail after001's audit/first event flush; the route must roll back, not claim the change committed."""
        if event.event_type == 'administration.changed':
            raise ConfigurationError('reconfiguration_bounds_unavailable')
        return await original(self, uow, event)
    monkeypatch.setattr(EventWriter, 'append', fail)
    response = await client.put('/api/v1/consumption/configuration', json=command, headers=headers)
    assert response.status_code == 503
    async with UnitOfWork(database.sessions) as uow:
        assert await uow.session.scalar(select(func.count()).select_from(InstallationRow)) == 1
        assert await uow.session.scalar(select(func.count()).select_from(AuditRecord).where(AuditRecord.entity_type == 'consumption_configuration')) == 1
        assert await uow.session.scalar(select(func.count()).select_from(FunctionalEvent).where(FunctionalEvent.source_module == 'consumption')) == 2
    monkeypatch.setattr(EventWriter, 'append', original)
    assert (await client.put('/api/v1/consumption/configuration', json=command, headers=headers)).status_code == 200
    assert (await client.get('/api/v1/consumption/catalog')).status_code == 200
