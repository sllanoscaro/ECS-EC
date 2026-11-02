"""004 immutable full calendars and local-time peak rules, including documented month contradictions."""

from uuid import UUID
import pytest
from pydantic import ValidationError
from ecs_ec.costs.schemas import ProfileInput
from backend.tests.costs_fixtures import profile_input


def test_overlaps_and_documented_gaps():
    """Overlaps within one revision are invalid; gaps remain expressible and limit the affected charge."""
    data = profile_input(UUID(int=1))
    data['segments'].append(dict(data['segments'][0]))
    with pytest.raises(ValidationError): ProfileInput.model_validate(data)
    data['segments'][0]['valid_to'] = '2025-06-01T00:00:00Z'
    data['segments'][1]['valid_from'] = '2025-07-01T00:00:00Z'
    assert len(ProfileInput.model_validate(data).segments) == 2


def test_peak_repeated_hour_has_two_distinct_real_windows():
    """Both explicit Santiago offsets of a repeated peak-hour block are evaluated, not deduplicated by wall label."""
    from ecs_ec.costs.calendar import is_peak
    from ecs_ec.costs.schemas import PeakCalendar
    from ecs_ec.consumption.models import instant
    calendar = PeakCalendar(version='fixture', months=[4], weekdays=[5], start_time='23:00', end_time='23:45', excluded_dates=[])
    for lower, upper in (('2026-04-05T02:00:00Z','2026-04-05T02:15:00Z'), ('2026-04-05T03:00:00Z','2026-04-05T03:15:00Z')):
        assert is_peak(instant(lower), instant(upper), calendar, 'America/Santiago')


def test_month_evidence_contradiction_and_missing_source_limit():
    """Well-formed but contradictory documentary data limits demand without fabricating a month."""
    from ecs_ec.costs.calendar import resolve_month
    from ecs_ec.costs.schemas import InputEvidence
    from backend.tests.unit.costs.test_engine import evidence
    data = evidence().model_dump(mode='json')
    request = data['request']
    request['billing_month_ref'] = '2026-04'
    request['billing_month_source_ref'] = dict(document_reference='synthetic:month', supply_id=str(UUID(int=999)),
        start_at=request['start'], end_at=request['end'], billing_month_ref='2026-04')
    assert resolve_month(InputEvidence.model_validate(data))[0] is None
    request['billing_month_source_ref']['supply_id'] = request['supply_id']
    assert resolve_month(InputEvidence.model_validate(data))[0] == '2026-04'


@pytest.mark.parametrize('limitation', ['missing_documented_source', 'unsupported_charge_rule', 'profile_validity_gap', 'monthly_strategy_unresolved'])
def test_unresolved_validity_or_strategy_never_prorates(limitation):
    """Missing authority, unsupported strategies, gaps and changing fixed fees remain explicit limitations."""
    from copy import deepcopy
    from ecs_ec.costs.engine import evaluate
    from backend.tests.unit.costs.test_engine import evidence
    data = evidence().model_dump(mode='json')
    segment = data['profile']['segments'][0]
    if limitation == 'missing_documented_source':
        segment['source_refs'] = []
    elif limitation == 'unsupported_charge_rule':
        segment['charges'][0]['vigency_strategy'] = 'undocumented_proration'
    else:
        second = deepcopy(segment)
        segment['valid_to'] = '2026-01-01T00:30:00Z'
        second['valid_from'] = '2026-01-01T00:30:00Z' if limitation == 'monthly_strategy_unresolved' else '2026-01-01T00:45:00Z'
        data['profile']['segments'].append(second)
        if limitation == 'monthly_strategy_unresolved':
            for item in data['profile']['segments']:
                item['charges'][0].update(kind='fijo', quantity_unit='cycle', vigency_strategy='cycle_once')
    result = evaluate(data)
    assert result['complete_total'] is None and limitation in result['reason_codes']


def test_energy_change_uses_exact_intervals_without_proration():
    """500kWh at100 plus500kWh at110 is105000 using physical intervals on both sides of the change."""
    from copy import deepcopy
    from ecs_ec.costs.engine import evaluate
    from backend.tests.unit.costs.test_engine import evidence
    data = evidence().model_dump(mode='json')
    first = data['profile']['segments'][0]
    second = deepcopy(first)
    first['valid_to'] = '2026-01-01T00:30:00Z'
    second['valid_from'] = first['valid_to']; second['charges'][0]['unit_price'] = '110'
    data['profile']['segments'].append(second)
    block = data['measurements'][0]
    second_block = deepcopy(block)
    block.update(end=first['valid_to'], energy_kwh='500', original_value='500')
    second_block.update(start=first['valid_to'], energy_kwh='500', original_value='500', record_id=str(UUID(int=4)))
    data['measurements'].append(second_block)
    assert evaluate(data)['complete_total'] == '105000'


def test_documented_month_rule_is_explicit_and_rejects_client_override():
    """An explicitly sourced cycle-end rule resolves April for a March/April cycle; absent authority never selects a month."""
    from ecs_ec.costs.calendar import resolve_month
    from ecs_ec.costs.schemas import InputEvidence
    from ecs_ec.costs.repository import CostsProblem
    from backend.tests.unit.costs.test_engine import evidence
    data = evidence().model_dump(mode='json')
    data['request'].update(start='2026-03-15T00:00:00Z', end='2026-04-15T00:00:00Z')
    policy = data['profile']['segments'][0]['billing_month_policy']
    policy.update(mode='documented_rule', rule_id='cycle_end_month_v1')
    month, source, version = resolve_month(InputEvidence.model_validate(data))
    assert month == '2026-04' and source.document_reference == 'synthetic:month' and version == 'fixture-month-v1'
    policy['rule_id'] = 'unknown_rule'
    assert resolve_month(InputEvidence.model_validate(data))[0] is None
    policy['source_refs'] = []
    assert resolve_month(InputEvidence.model_validate(data))[0] is None
