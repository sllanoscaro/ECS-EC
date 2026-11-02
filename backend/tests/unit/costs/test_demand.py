"""Demand references use proven exact blocks and distinct months, without inventing historical coverage."""

import pytest
from decimal import Decimal


def test_exact_block_and_month_ties():
    """Ten kWh per900 seconds is40kW; equal maxima in two months both count toward the base."""
    from ecs_ec.costs.demand import block_power, top_two
    assert block_power('10', 900000000) == Decimal('40')
    assert block_power('10', 3600000000) is None
    assert top_two([('2025-01', '60'), ('2025-02', '50')]) == Decimal('55')
    assert top_two([('2025-01', '30'), ('2025-02', '20')]) == Decimal('25')
    assert top_two([('2025-01', '60'), ('2025-02', '60')]) == Decimal('60')
    assert top_two([('2025-01', '60')]) is None


def test_documentary_month_between_months():
    """A cycle crossing March/April uses only validated policy/evidence, never the issue date by default."""
    from ecs_ec.costs.calendar import resolve_month, history_window
    from backend.tests.unit.costs.test_engine import evidence
    snapshot = evidence()
    assert resolve_month(snapshot)[0] is None
    lower, upper = history_window('2026-04', 'Etc/UTC')
    assert lower.isoformat() == '2025-05-01T00:00:00+00:00'
    assert upper.isoformat() == '2026-05-01T00:00:00+00:00'


def test_full_coverage_supplied_and_seasonal_bases():
    """Actual quarter-hour coverage proves60/50→55 and30/20→25; removing a block invalidates its month's maximum."""
    from datetime import timedelta
    from types import SimpleNamespace
    from ecs_ec.costs.calendar import month_bounds
    from ecs_ec.costs.demand import bases
    from ecs_ec.costs.schemas import ProfileInput
    from backend.tests.costs_fixtures import profile_input
    from uuid import UUID
    calendar = ProfileInput.model_validate(profile_input(UUID(int=1))).segments[0]
    rows, seen_peak = [], set()
    cursor, end = month_bounds('2025-04', 'Etc/UTC')[0], month_bounds('2026-04', 'Etc/UTC')[1]
    while cursor < end:
        month = cursor.strftime('%Y-%m')
        energy = '1'
        if cursor.day == 1 and cursor.hour == 0 and cursor.minute == 0:
            energy = {'2025-05': '15', '2025-06': '12.5'}.get(month, '1')
        if cursor.weekday() < 5 and cursor.hour == 18 and month not in seen_peak:
            energy = {'2025-04': '7.5', '2025-05': '5', '2026-04': '7.5'}.get(month, '1')
            seen_peak.add(month)
        rows.append(SimpleNamespace(start=cursor, end=cursor+timedelta(minutes=15), energy_kwh=energy))
        cursor += timedelta(minutes=15)
    evidence = SimpleNamespace(billing_month_ref='2026-04', history=rows, request=SimpleNamespace(timezone='Etc/UTC'))
    supplied, peak, maxima, _ = bases(evidence, calendar)
    assert supplied == Decimal('55') and peak == Decimal('30')
    evidence.billing_month_ref = '2026-03'
    assert bases(evidence, calendar)[1] == Decimal('25')
    evidence.billing_month_ref = '2026-04'
    # Remove evidence from May2025: remaining observed maxima cannot prove the missed quarter did not exceed them.
    evidence.history = rows[:5000] + rows[5001:]
    assert bases(evidence, calendar)[0] is None
