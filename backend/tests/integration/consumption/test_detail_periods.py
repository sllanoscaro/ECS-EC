"""Containment and diagnostic crossings use real002 records and never prorate."""

import pytest
from backend.tests.integration.consumption.test_detail_queries import facade
from backend.tests.unit.consumption.test_validation import record

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('category', ['CAT-05', pytest.param('CAT-01', marks=pytest.mark.xfail(strict=True,
    reason='spec-002 MeasurementStore.read_detail does not expose crossing diagnostic IDs; spec-001 T041 pending'))])
async def test_crossing_rows_and_diagnostics(consumption_reception_environment, database, clock, category):
    """An interval crossing both boundaries counts once; the same holds for an incomplete candidate."""
    env = consumption_reception_environment
    await env.publish([record()])
    service = facade(database, clock)
    result = await service.detail(category, '2025-12-31T21:15:00-03:00', '2025-12-31T21:45:00-03:00', 'America/Santiago')
    assert result.rows == () and result.diagnostics == () and result.state == 'no_data'
    assert next(w for w in result.warnings if w.code == 'crossing_intervals_excluded').count == 1
