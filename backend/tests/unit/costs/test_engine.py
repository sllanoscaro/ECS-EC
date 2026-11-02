"""Independent004 energy references: exact1000×100, missing evidence, explicit taxes and zero."""

from uuid import UUID
import pytest
from backend.tests.costs_fixtures import profile_input


def evidence(*, energy='1000', reason=None, price='100'):
    """Build typed synthetic physical inputs; an energy-only synthetic schedule does not represent the real supply."""
    from ecs_ec.costs.schemas import InputEvidence
    return InputEvidence.model_validate(dict(request=dict(supply_id=str(UUID(int=1)), start_at='2026-01-01T00:00:00Z',
        end_at='2026-01-01T01:00:00Z', timezone='America/Santiago', boundary_criterion='synthetic:exact'),
        cutoff_at='2026-05-01T00:00:00Z', supply_id=str(UUID(int=1)), supply_revision=1,
        supply=dict(general_board_ref='synthetic:board', category_id='CAT-01', general_source_id=str(UUID(int=1)),
            distributor='synthetic', location='synthetic', connection_conditions='synthetic', document_refs=['synthetic:source'], measurement_point_differences=[]),
        profile_id=str(UUID(int=2)), profile_revision=1, profile=profile_input(UUID(int=1), price=price),
        measurements=[dict(record_id=str(UUID(int=3)), revision=1, category_revision=1, configuration_revision=1,
            source_id=str(UUID(int=1)), energy_kwh=energy, original_value=energy, original_unit='kWh',
            start='2026-01-01T00:00:00Z', end='2026-01-01T01:00:00Z')], general_reason=reason,
        history=[], history_reason='insufficient_evidence', billing_month_ref=None,
        billing_month_source_ref=None, billing_month_policy_version=None))


def test_known_energy_and_zero():
    """The exact energy reference and a valid zero are complete for an explicitly energy-only synthetic profile."""
    from ecs_ec.costs.engine import evaluate
    result = evaluate(evidence())
    assert result['components'][0]['presented_amount'] == '100000'
    assert result['complete_total'] == '100000' and result['sufficiency'] == 'completo'
    assert evaluate(evidence(energy='0'))['complete_total'] == '0'


@pytest.mark.parametrize('reason', ['calculated_general', 'insufficient_evidence', 'no_source'])
def test_missing_evidence_is_not_a_complete_total(reason):
    """Even an available partial sum cannot enter an authoritative charge when the physical base is incomplete."""
    from ecs_ec.costs.engine import evaluate
    result = evaluate(evidence(reason=reason))
    assert result['complete_total'] is None and result['components'][0]['presented_amount'] is None


def test_missing_price_limits_only_that_charge():
    """A missing price is not zero; fixed fees remain available while energy is limited."""
    from ecs_ec.costs.engine import evaluate
    data = evidence().model_dump(mode='json')
    energy = data['profile']['segments'][0]['charges'][0]
    energy['unit_price'] = None
    fixed = energy | dict(code='fixed', kind='fijo', quantity_unit='cycle', unit_price='50', vigency_strategy='cycle_once')
    data['profile']['segments'][0]['charges'].append(fixed)
    result = evaluate(type(evidence()).model_validate(data))
    assert result['complete_total'] is None and result['available_subtotal'] == '50'


def test_explicit_tax_and_included_basis():
    """A documented19% tax on100000 yields19000; included-tax energy cannot be taxed a second time."""
    from ecs_ec.costs.engine import evaluate
    data = evidence().model_dump(mode='json')
    segment = data['profile']['segments'][0]
    segment['charges'].append(dict(code='tax', kind='impuesto', quantity_unit='CLP', unit_price='0.19', tax_basis='impuesto_separado',
        applicability='always', vigency_strategy='cycle_once', source_refs=['synthetic:tax'], tax_codes=['energy']))
    result = evaluate(type(evidence()).model_validate(data))
    assert result['complete_total'] == '119000' and result['tax_total'] == '19000'
    segment['charges'][0]['tax_basis'] = 'impuesto_incluido'
    limited = evaluate(type(evidence()).model_validate(data))
    assert limited['complete_total'] is None and limited['components'][1]['presented_amount'] is None


def test_included_tax_has_no_invented_net_or_tax_decomposition():
    """A documented gross price is available, but unknown included tax is not reported as zero or as net money."""
    from ecs_ec.costs.engine import evaluate
    data = evidence().model_dump(mode='json')
    data['profile']['segments'][0]['charges'][0]['tax_basis'] = 'impuesto_incluido'
    result = evaluate(data)
    assert result['complete_total'] == '100000'
    assert result['net_total'] is None and result['tax_total'] is None


def test_duplicate_tax_base_is_structurally_rejected():
    """Repeated taxable codes must never multiply a tax twice."""
    from ecs_ec.costs.schemas import Charge
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Charge.model_validate(dict(code='tax', kind='impuesto', quantity_unit='CLP', unit_price='0.19', tax_basis='impuesto_separado',
            applicability='always', vigency_strategy='cycle_once', source_refs=['synthetic:tax'], tax_codes=['energy', 'energy']))


def test_price_exceeding_documented_precision_is_a_limitation_not_technical_failure():
    """A finite but unrepresentable configuration preserves a limited result rather than a false number or engine event."""
    from ecs_ec.costs.engine import evaluate
    result = evaluate(evidence(price='9'*80))
    assert result['execution_state'] == 'completado' and result['complete_total'] is None
    assert 'monetary_precision_exceeded' in result['reason_codes']


def test_complete_documented_charge_set_with_physical_demand_history():
    """A full synthetic schedule reconciles every charge/tax with independent expected values and proven15-minute history."""
    from datetime import timedelta
    from ecs_ec.costs.calendar import month_bounds
    from ecs_ec.costs.engine import evaluate
    from ecs_ec.costs.schemas import InputEvidence
    data = evidence(energy='4').model_dump(mode='json')
    data['request'].update(start='2026-04-01T00:00:00Z', end='2026-04-01T01:00:00Z', timezone='Etc/UTC')
    data['measurements'][0].update(start=data['request']['start'], end=data['request']['end'])
    data['profile']['timezone'] = 'Etc/UTC'
    data['billing_month_ref'] = '2026-04'
    rows, seen_peak = [], set()
    cursor, end = month_bounds('2025-04', 'Etc/UTC')[0], month_bounds('2026-04', 'Etc/UTC')[1]
    while cursor < end:
        month, energy = cursor.strftime('%Y-%m'), '1'
        if cursor.day == 1 and cursor.hour == 0 and cursor.minute == 0:
            energy = {'2025-05':'15', '2025-06':'12.5'}.get(month, '1')
        if cursor.weekday() < 5 and cursor.hour == 18 and month not in seen_peak:
            energy = {'2025-04':'7.5', '2025-05':'5', '2026-04':'7.5'}.get(month, '1')
            seen_peak.add(month)
        rows.append(data['measurements'][0] | dict(record_id=str(UUID(int=len(rows)+1000)), start=cursor.isoformat(),
            end=(cursor+timedelta(minutes=15)).isoformat(), energy_kwh=energy, original_value=energy))
        cursor += timedelta(minutes=15)
    data['history'] = rows; data['history_reason'] = None
    segment = data['profile']['segments'][0]
    base = segment['charges'][0]
    for code, kind, unit, price, strategy in [('transmission','transmision','kWh','2','exact_intervals'),
            ('service','servicio_publico','kWh','3','exact_intervals'), ('fixed','fijo','cycle','50','cycle_once'),
            ('supplied','potencia_suministrada','kW','10','cycle_once'), ('peak','demanda_punta','kW','20','cycle_once'),
            ('other','otro_documentado','cycle','5','cycle_once')]:
        segment['charges'].append(base | dict(code=code, kind=kind, quantity_unit=unit, unit_price=price, vigency_strategy=strategy))
    segment['charges'].append(base | dict(code='tax', kind='impuesto', quantity_unit='CLP', unit_price='0.19',
        tax_basis='impuesto_separado', vigency_strategy='cycle_once', tax_codes=[c['code'] for c in segment['charges']]))
    data['profile']['required_kinds'] = [c['kind'] for c in segment['charges']]
    result = evaluate(InputEvidence.model_validate(data))
    assert {c['code']:c['presented_amount'] for c in result['components']} == dict(energy='400', transmission='8',
        service='12', fixed='50', supplied='550', peak='600', other='5', tax='309')
    assert result['net_total'] == '1625' and result['tax_total'] == '309' and result['complete_total'] == '1934'
    assert result['sufficiency'] == 'completo'


def test_total_stage_rounding_preserves_visible_reconciliation():
    """Total-stage quantum rounding adds a captured adjustment rather than silently changing component prices or quantities."""
    from decimal import Decimal
    from ecs_ec.costs.engine import evaluate
    data = evidence(energy='4.005').model_dump(mode='json')
    segment = data['profile']['segments'][0]
    segment['rounding_policy']['stage'] = 'total'
    segment['charges'].append(segment['charges'][0] | dict(code='fixed', kind='fijo', quantity_unit='cycle',
        unit_price='50.25', vigency_strategy='cycle_once'))
    result = evaluate(data)
    assert result['complete_total'] == '451'
    assert result['components'][0]['presented_amount'] == '400.5'
    assert result['components'][-1]['code'] == 'rounding_adjustment' and result['components'][-1]['presented_amount'] == '0.25'
    assert sum(Decimal(row['presented_amount']) for row in result['components']) == Decimal('451')
