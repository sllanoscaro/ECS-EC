"""Independent signed comparison references with zero denominators and explicit exclusions."""

from uuid import UUID
import pytest


def inputs(calculated='105', billed='100', tax_basis='neto'):
    """Provide one aligned synthetic concept; debt stays separate from the comparable electrical subtotal."""
    return (dict(cycle_id='cycle', currency='CLP', snapshot=dict(supply_id='supply'), components=[dict(code='energy',
        kind='energia', unit='kWh', tax_basis='neto', presented_amount=calculated)]),
        dict(cycle_id='cycle', supply_id='supply', currency='CLP', total_payable='900', lines=[dict(code='energy',
            unit='kWh', amount=billed, tax_basis=tax_basis, tax_amount=None, cycle_relation='current_cycle')]))


def test_reference_percentage_zero_and_signed_credit():
    """105 versus100 is+5/+5%; a zero denominator has null percentage and a credit retains its sign."""
    from ecs_ec.costs.comparison import compare
    result = compare(*inputs())
    assert result['delta_amount'] == '5' and result['delta_percent'] == '5'
    assert compare(*inputs(billed='0'))['delta_percent'] is None
    credit = compare(*inputs(calculated='-105', billed='-100'))
    assert credit['delta_amount'] == '-5' and credit['delta_percent'] == '-5'


def test_tax_and_unknown_concepts_are_not_forced_comparable():
    """Only a documented included-tax amount can align to net; unknown concepts keep signed original values."""
    from ecs_ec.costs.comparison import compare
    calc, bill = inputs(tax_basis='impuesto_incluido')
    assert compare(calc, bill)['delta_amount'] is None
    bill['lines'][0]['tax_amount'] = '19'
    bill['lines'][0]['amount'] = '119'
    assert compare(calc, bill)['delta_amount'] == '5'
    bill['lines'].append(dict(code='credit', unit='CLP', amount='-50', tax_basis='neto', tax_amount=None, cycle_relation='outside_cycle'))
    assert compare(calc, bill)['excluded_lines'][0]['amount'] == '-50'


def test_foreign_cycle_fails():
    """Equal amounts do not prove equal supply/cycle/currency."""
    from ecs_ec.costs.comparison import compare
    from ecs_ec.costs.repository import CostsProblem
    calc, bill = inputs()
    bill['cycle_id'] = 'other'
    with pytest.raises(CostsProblem): compare(calc, bill)


def test_uncertain_effective_boundaries_cannot_produce_comparison():
    """A nominally identical cycle with documented boundary uncertainty cannot become a numerical contrast."""
    from ecs_ec.costs.comparison import compare
    from ecs_ec.costs.repository import CostsProblem
    calc, bill = inputs()
    bill['boundary_limited'] = True
    with pytest.raises(CostsProblem):
        compare(calc, bill)
