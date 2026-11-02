"""002 read DTO contracts distinguish missing evidence, unavailable providers and explicit nulls."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from ecs_ec.consumption.ports import AttemptLookup, ReceptionOutcome
from ecs_ec.consumption.models import ReconfigurationBounds, instant


def test_lookup_requires_outcome_except_not_found():
    """An unfinished capture includes positions without durable results; absent is a separate state."""
    common = dict(attempt_id=UUID(int=1), building_id=UUID(int=99))
    assert AttemptLookup(**common, state='not_found', outcome=None).outcome is None
    with pytest.raises(ValidationError): AttemptLookup(**common, state='processing', outcome=None)
    outcome = ReceptionOutcome(**common, correlation_ref='test', received_at=instant('2026-01-01T00:00:00Z'),
        state='processing', results=(), updates=(), pending_positions=(0, 1))
    assert AttemptLookup(**common, state='processing', outcome=outcome).outcome.pending_positions == (0, 1)
    with pytest.raises(ValidationError): AttemptLookup(**common, state='not_found', outcome=outcome)


def test_incomplete_bounds_are_never_empty_history():
    """A missing category is a failed provider contract, whereas a present null means never incorporated."""
    bounds = ReconfigurationBounds(has_accepted_history=False, latest_interval_end_by_category={'CAT-01': None})
    bounds.require_categories(('CAT-01',))
    with pytest.raises(ValueError, match='incomplete_history_bounds'): bounds.require_categories(('CAT-01', 'CAT-02'))


def test_grouped_empty_and_exact_incomplete_contract():
    """Future/empty blocks carry nullable evidence, while one missing microsecond remains incomplete at100%."""
    from ecs_ec.consumption.ports import AggregateBlock
    base = dict(start='2026-01-01T00:00:00Z', end='2026-01-01T01:00:00Z', timezone='UTC',
        aggregate_id=None, revision=None, duration_us='3600000000', covered_duration_us='0', energy_kwh=None,
        coverage_percent='0', coverage_state='no_data', temporal_state='not_started', contribution_count=0,
        source_mode='unavailable', provenance_segments=(), created_at=None, last_new_data_at=None, retain_until=None, warnings=())
    block = AggregateBlock(**base)
    assert block.energy_kwh is None and block.temporal_state == 'not_started'
    with pytest.raises(ValidationError): AggregateBlock(**(base | {'energy_kwh': '0'}))
    real = base | dict(aggregate_id=UUID(int=3), revision=1, covered_duration_us='3599999999', energy_kwh='0',
        coverage_percent='100', coverage_state='incomplete', contribution_count=1, source_mode='measured',
        created_at=base['start'], last_new_data_at=base['start'], retain_until='2027-01-01T00:00:00Z')
    assert AggregateBlock(**real).coverage_state == 'incomplete'
    with pytest.raises(ValidationError): AggregateBlock(**(real | {'coverage_state': 'complete'}))
