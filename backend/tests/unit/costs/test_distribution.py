"""Independent expectations for proportional estimates and unavailable evidence states."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from ecs_ec.costs.distribution import apportion, project_distribution


def example(weights=('400', '100', '160', '220', '70', '50')):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)
    def row(index, value):
        return NS(record_id=str(index), revision=1, kind='measured', start=start, end=end, energy_kwh=Decimal(value))
    categories = []
    for i, value in enumerate(('1000', *weights), 1):
        categories.append(dict(category=dict(id=f'CAT-{i:02}', name=f'Category {i}'),
            detail=NS(rows=(row(i, value),), diagnostics=(), crossing_record_ids=(), crossing_diagnostic_ids=(), withdrawn_record_ids=()),
            provenance_segments=(NS(source_mode='measured'),)))
    calculation = dict(id='calculation', execution_state='completado', complete_total='1428000',
        components=[dict(kind='energia', presented_amount='1000000', state='available', tax_basis='neto')],
        snapshot=dict(request=dict(start=start.isoformat(), end=end.isoformat()),
            measurements=[dict(record_id='1', revision=1, energy_kwh='1000')]))
    return calculation, dict(cutoff_at=end, categories=categories)


def test_exact_energy_only_shares_and_conserved_rounding():
    calculation, capture = example()
    result = project_distribution(calculation, capture)
    assert result['state'] == 'available'
    assert [r['estimated_amount'] for r in result['categories']] == ['400000', '100000', '160000', '220000', '70000', '50000']
    assert result['other_amount'] == '428000'
    assert apportion(Decimal('1'), [Decimal(1)] * 3) == ['1', '0', '0']
    assert apportion(Decimal('10.01'), [Decimal(1)] * 3) == ['3.34', '3.34', '3.33']
    assert apportion(Decimal('100.00'), [Decimal(1)] * 3) == ['33.34', '33.33', '33.33']


def test_unmetered_categories_keep_a_visible_unassigned_balance():
    calculation, capture = example()
    item = capture['categories'][-1]
    item['detail'].rows = ()
    item['provenance_segments'] = (NS(source_mode='unavailable'),)
    result = project_distribution(calculation, capture)
    assert result['state'] == 'available'
    assert result['categories'][-1]['estimated_amount'] is None
    assert result['categories'][-1]['state'] == 'no_meter'
    assert result['unassigned_amount'] == '50000' and result['unassigned_percent'] == '5'


@pytest.mark.parametrize('failure', ['gap', 'exceeded', 'changed', 'zero', 'tax_included', 'withdrawn'])
def test_invalid_evidence_never_produces_monetary_slices(failure):
    calculation, capture = example()
    if failure == 'gap': capture['categories'][1]['detail'].rows[0].end -= timedelta(minutes=15)
    if failure == 'exceeded': capture['categories'][1]['detail'].rows[0].energy_kwh = Decimal('1500')
    if failure == 'changed': capture['categories'][0]['detail'].rows[0].revision = 2
    if failure == 'zero':
        calculation['snapshot']['measurements'][0]['energy_kwh'] = '0'
        for item in capture['categories']: item['detail'].rows[0].energy_kwh = Decimal(0)
    if failure == 'tax_included': calculation['components'][0]['tax_basis'] = 'impuesto_incluido'
    if failure == 'withdrawn':
        capture['categories'][1]['detail'].rows = ()
        capture['categories'][1]['detail'].withdrawn_record_ids = ('retired',)
    result = project_distribution(calculation, capture)
    assert result['state'] == 'unavailable' and result['reason_code']
    assert all(row['estimated_amount'] is None and row['percent'] is None for row in result['categories'])


def test_real_zero_is_retained_as_zero_when_the_general_basis_is_positive():
    calculation, capture = example(('400', '100', '160', '220', '120', '0'))
    result = project_distribution(calculation, capture)
    assert result['categories'][-1]['estimated_amount'] == '0'
    assert result['categories'][-1]['percent'] == '0'
