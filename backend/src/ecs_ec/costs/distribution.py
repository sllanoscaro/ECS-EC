"""Read-only proportional energy estimate; never changes the tariff calculation or its snapshot."""

from decimal import Decimal, localcontext, ROUND_DOWN

from ecs_ec.consumption.dashboard import summarize
from ecs_ec.consumption.models import instant
from ecs_ec.costs.money import decimal_text, number


def apportion(amount, weights):
    """Allocate exact monetary quanta by largest remainder, with deterministic category tie breaks."""
    with localcontext() as context:
        context.prec = 128
        quantum = Decimal(1).scaleb(min(0, amount.as_tuple().exponent))
        units = amount / quantum
        total = sum(weights)
        exact = [units * weight / total for weight in weights]
        whole = [value.to_integral_value(rounding=ROUND_DOWN) for value in exact]
        remainder = int(units - sum(whole))
        order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - whole[i]), i))
        for i in order[:remainder]:
            whole[i] += 1
        return [decimal_text(value * quantum) for value in whole]


def project_distribution(calculation, capture):
    """Use coherent current category evidence only when it reconciles with captured physicalCAT-01.

    This is a transient estimate with its own cutoff, not a reproduced historical
    tariff result. Missing or overlapping evidence never becomes zero or a full pie.
    """
    with localcontext() as context:
        context.prec = 128
        return _project(calculation, capture)


def _project(calculation, capture):
    start, end = (instant(calculation['snapshot']['request'][key]) for key in ('start', 'end'))
    charges = [c for c in calculation['components'] if c['kind'] == 'energia']
    valid_charge = (calculation['execution_state'] == 'completado' and bool(charges)
        and all(c['presented_amount'] is not None and c['state'] == 'available' and c['tax_basis'] == 'neto' for c in charges))
    amount = sum((number(c['presented_amount']) for c in charges), Decimal(0)) if valid_charge else None
    result = dict(calculation_id=calculation['id'], cutoff_at=capture['cutoff_at'].isoformat(),
        state='unavailable', reason_code=None, energy_amount=decimal_text(amount) if amount is not None else None,
        other_amount=decimal_text(number(calculation['complete_total']) - amount)
            if calculation['complete_total'] is not None and amount is not None else None,
        categories=[], unassigned_amount=None, unassigned_percent=None)
    weights, available = [], True
    for item in capture['categories']:
        if item['category']['id'] == 'CAT-01':
            general = item
            continue
        detail, segments = item['detail'], item['provenance_segments']
        summary = summarize(detail.rows, start, end)
        missing = not detail.rows and (not segments or all(s.source_mode == 'unavailable' for s in segments))
        limited = bool(detail.diagnostics or detail.crossing_record_ids or detail.crossing_diagnostic_ids or detail.withdrawn_record_ids)
        complete = not limited and summary['covered_duration_us'] == summary['elapsed_duration_us']
        state = 'no_meter' if missing and not limited else 'available' if complete else 'incomplete' if detail.rows or limited else 'no_data'
        available = available and state in {'available', 'no_meter'}
        energy = number(summary['energy_kwh']) if complete and summary['energy_kwh'] is not None else None
        result['categories'].append(dict(id=item['category']['id'], name=item['category']['name'], state=state,
            energy_kwh=decimal_text(energy) if energy is not None else None, percent=None, estimated_amount=None))
        weights.append(energy if energy is not None else Decimal(0))
    if amount is None or amount < 0:
        result['reason_code'] = 'energy_charge_unavailable'
        return result
    captured = calculation['snapshot']['measurements']
    captured_ids = {(str(r['record_id']), r['revision']) for r in captured}
    current_ids = {(str(r.record_id), r.revision) for r in general['detail'].rows}
    general_summary = summarize(general['detail'].rows, start, end)
    total = sum((number(r['energy_kwh']) for r in captured), Decimal(0))
    if (not captured_ids or captured_ids != current_ids or any(r.kind != 'measured' for r in general['detail'].rows)
        or general_summary['covered_duration_us'] != general_summary['elapsed_duration_us']
        or general['detail'].withdrawn_record_ids or general['detail'].diagnostics):
        result['reason_code'] = 'general_evidence_changed'
    elif not available:
        result['reason_code'] = 'category_coverage_incomplete'
    elif total <= 0:
        result['reason_code'] = 'zero_energy_basis'
    elif sum(weights) > total:
        result['reason_code'] = 'categories_exceed_general'
    else:
        remainder = total - sum(weights)
        amounts = apportion(amount, weights + [remainder])
        # Percentages also conserve100.00 exactly, including a visible residual.
        percentages = apportion(Decimal('100.00'), weights + [remainder])
        for row, value, percentage in zip(result['categories'], amounts, percentages):
            if row['state'] == 'available':
                row.update(estimated_amount=value, percent=percentage)
        result.update(state='available', unassigned_amount=amounts[-1], unassigned_percent=percentages[-1])
    return result
