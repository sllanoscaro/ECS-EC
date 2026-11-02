"""Pure004 signed bill comparison; only aligned supply/cycle/currency/concept/tax bases enter subtotals."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from ecs_ec.costs.money import decimal_text, number
from ecs_ec.costs.repository import CostsProblem


def percentage(delta, billed):
    """Return100*delta/abs(billed), or null for zero; comparison-v1 displays six half-up decimal places."""
    if not billed:
        return None
    with localcontext() as context:
        context.prec = 128
        return decimal_text((100 * delta / abs(billed)).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))


def compare(calculation, bill):
    """Capture original/excluded signed lines and sum exactly the same aligned pairs on both sides."""
    if (calculation['snapshot'].get('request', {}).get('boundary_limited', False) or bill.get('boundary_limited', False)
            or str(calculation['cycle_id']) != str(bill['cycle_id']) or calculation['currency'] != bill['currency']
            or str(calculation['snapshot']['supply_id']) != str(bill['supply_id'])):
        raise CostsProblem('comparison_basis_mismatch', 422)
    with localcontext() as context:
        context.prec = 256
        components = {c['code']: c for c in calculation['components']}
        pairs, excluded = [], []
        for line in bill['lines']:
            component = components.get(line['code'])
            reason, amount = None, number(line['amount'])
            if line['cycle_relation'] != 'current_cycle':
                reason = 'outside_comparable_cycle'
            elif component is None:
                reason = 'no_calculated_equivalent'
            elif component['presented_amount'] is None:
                reason = 'calculation_limited'
            elif component['unit'] != line['unit']:
                reason = 'quantity_basis_mismatch'
            elif component['tax_basis'] != line['tax_basis']:
                if component['tax_basis'] == 'neto' and line['tax_basis'] == 'impuesto_incluido' and line['tax_amount'] is not None:
                    amount -= number(line['tax_amount'])
                else:
                    reason = 'tax_basis_mismatch'
            if reason:
                excluded.append(dict(code=line['code'], amount=line['amount'], reason_code=reason))
            else:
                calculated = number(component['presented_amount'])
                pairs.append(dict(code=line['code'], unit=line['unit'], tax_basis=component['tax_basis'],
                    calculated_quantity=component.get('basis_value'), billed_quantity=line.get('quantity'),
                    calculated_amount=decimal_text(calculated), billed_amount=decimal_text(amount),
                    original_billed_amount=line['amount'], delta_amount=decimal_text(calculated - amount)))
        calculated = sum((number(p['calculated_amount']) for p in pairs), Decimal(0))
        billed = sum((number(p['billed_amount']) for p in pairs), Decimal(0))
        delta = calculated - billed
        return dict(currency=bill['currency'], comparable_calculated=decimal_text(calculated) if pairs else None,
            comparable_billed=decimal_text(billed) if pairs else None, delta_amount=decimal_text(delta) if pairs else None,
            delta_percent=percentage(delta, billed) if pairs else None, total_payable=bill['total_payable'],
            pairs=pairs, excluded_lines=excluded, unmatched_calculated_codes=sorted(set(components)-{p['code'] for p in pairs}),
            limitation_codes=[] if pairs else ['no_comparable_pairs'], percentage_rule='signed_delta_absolute_denominator_6dp_v1')
