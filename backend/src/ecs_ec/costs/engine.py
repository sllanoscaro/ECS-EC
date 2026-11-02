"""Pure versioned004 charge evaluation; insufficient inputs never become zero or a complete BT4.3 total."""

from datetime import timedelta
from decimal import Decimal, DecimalException, localcontext

from ecs_ec.costs.demand import bases
from ecs_ec.costs.money import decimal_text, number, rounded
from ecs_ec.costs.profiles import applicable_segments, ENERGY_KINDS
from ecs_ec.costs.schemas import InputEvidence

ENGINE_VERSION = 'bt43-v1'


def complete_coverage(rows, start, end):
    """Prove exact contiguous coverage from actual contained intervals; do not infer cadence or fill gaps."""
    cursor = start
    for row in sorted(rows, key=lambda r: r.start):
        if row.start != cursor or row.end > end:
            return False
        cursor = row.end
    return start < end and cursor == end


def evaluate(evidence):
    """Calculate only from typed captured inputs, producing a JSON-compatible immutable component/result value."""
    evidence = InputEvidence.model_validate(evidence)
    with localcontext() as context:
        context.prec = 256
        return _evaluate(evidence)


def _evaluate(evidence):
    """Evaluate independent charge groups, then explicit tax dependencies, within the private exact context."""
    request, profile = evidence.request, evidence.profile
    components, reasons, monthly = [], [], []
    if profile is None:
        return result([], ['profile_unavailable'], request.end <= evidence.cutoff_at and not request.boundary_limited)
    if evidence.general_reason in {'calculated_general', 'no_source'}:
        reasons.append('physical_general_required')
    if request.boundary_limited:
        reasons.append('cycle_boundaries_unresolved')
    end = min(request.end, evidence.cutoff_at)
    segments = applicable_segments(profile, request.start, request.end)
    covered_segments = [(max(s.valid_from, request.start), min(s.valid_to or request.end, request.end)) for s in segments]
    cursor = request.start
    calendar_complete = bool(covered_segments)
    for lower, upper in covered_segments:
        if lower != cursor:
            calendar_complete = False
        cursor = upper
    calendar_complete = calendar_complete and cursor == request.end
    physical_ok = (evidence.general_reason is None and not request.boundary_limited and
        all(r.source_id == evidence.supply.general_source_id for r in evidence.measurements) and
        complete_coverage(evidence.measurements, request.start, end))
    grouped = {}
    for index, segment in enumerate(segments):
        for charge in segment.charges:
            grouped.setdefault(charge.code, []).append((index, segment, charge))
    for kind in profile.required_kinds:
        if not any(c.kind == kind for s in segments for c in s.charges):
            reasons.append('required_charge_missing')
    for code, entries in grouped.items():
        if entries[0][2].kind == 'impuesto':
            continue
        amount, quantities, limits, policies = Decimal(0), [], [], []
        first = entries[0][2]
        if len({(c.kind, c.quantity_unit, c.tax_basis) for _, _, c in entries}) != 1:
            limits.append('incompatible_charge_segments')
        if not calendar_complete:
            limits.append('profile_validity_gap')
        if len(entries) != len(segments):
            limits.append('charge_validity_gap')
        for _, segment, charge in entries:
            policies.append(segment.rounding_policy)
            if not (segment.source_refs and charge.source_refs and profile.source_refs):
                limits.append('missing_documented_source')
            if charge.unit_price is None:
                limits.append('missing_price')
            if charge.applicability != 'always':
                limits.append('unsupported_applicability')
            quantity = None
            if charge.kind in ENERGY_KINDS and charge.vigency_strategy == 'exact_intervals' and charge.quantity_unit == 'kWh':
                lower, upper = max(segment.valid_from, request.start), min(segment.valid_to or end, end)
                rows = tuple(r for r in evidence.measurements if r.start >= lower and r.end <= upper)
                if physical_ok and lower < upper and complete_coverage(rows, lower, upper):
                    quantity = sum((number(r.energy_kwh) for r in rows), Decimal(0))
                else:
                    limits.append(evidence.general_reason or 'insufficient_energy_coverage')
            elif charge.kind in {'fijo', 'otro_documentado'} and charge.vigency_strategy == 'cycle_once' and charge.quantity_unit == 'cycle':
                if len(entries) == 1 and segment.valid_from <= request.start and (segment.valid_to is None or segment.valid_to >= request.end):
                    quantity = Decimal(1)
                else:
                    limits.append('monthly_strategy_unresolved')
            elif charge.kind in {'potencia_suministrada', 'demanda_punta'} and charge.vigency_strategy == 'cycle_once' and charge.quantity_unit == 'kW':
                if len(entries) != 1 or segment.valid_from > request.start or (segment.valid_to and segment.valid_to < request.end):
                    limits.append('monthly_strategy_unresolved')
                elif evidence.general_reason in {'calculated_general', 'no_source'} or any(r.source_id != evidence.supply.general_source_id for r in evidence.history):
                    limits.append('physical_general_required')
                else:
                    supplied, peak, maxima, reason = bases(evidence, segment)
                    monthly.extend(maxima)
                    quantity = supplied if charge.kind == 'potencia_suministrada' else peak
                    if quantity is None:
                        limits.append(reason)
                        if any(r.end - r.start != timedelta(minutes=15) for r in evidence.history):
                            limits.append('insufficient_demand_resolution')
            else:
                limits.append('unsupported_charge_rule')
            if quantity is not None and charge.unit_price is not None:
                quantities.append(quantity)
                amount += quantity * number(charge.unit_price)
        if len({p.model_dump_json() for p in policies}) != 1:
            limits.append('incompatible_rounding_policies')
        components.append(component(code, first, amount if not limits else None, sum(quantities) if quantities and not limits else None,
            policies[0], limits, evidence, entries))
    # Tax dependencies must reference known non-tax net components; included tax never gets taxed again.
    for code, entries in grouped.items():
        first, policy = entries[0][2], entries[0][1].rounding_policy
        if first.kind != 'impuesto':
            continue
        selected = [next((c for c in components if c['code'] == ref), None) for ref in first.tax_codes]
        limits = []
        if (len(entries) != 1 or first.vigency_strategy != 'cycle_once' or first.applicability != 'always'
                or first.quantity_unit != 'CLP' or first.tax_basis != 'impuesto_separado' or first.unit_price is None or not first.source_refs or not first.tax_codes
                or not calendar_complete):
            limits.append('tax_rule_unresolved')
        if any(c is None or c['presented_amount'] is None or c['tax_basis'] != 'neto' for c in selected):
            limits.append('tax_basis_unresolved')
        quantity = sum((number(c['presented_amount']) for c in selected if c and c['presented_amount'] is not None), Decimal(0))
        components.append(component(code, first, quantity * number(first.unit_price) if not limits else None,
            quantity if not limits else None, policy, limits, evidence, entries))
    if not components:
        reasons.append('charges_unavailable')
    if not all((evidence.supply.distributor, evidence.supply.location, evidence.supply.connection_conditions, evidence.supply.document_refs)):
        reasons.append('supply_conditions_missing')
    output = result(components, reasons, request.end <= evidence.cutoff_at and not request.boundary_limited)
    output['monthly_maxima'] = list({(m['kind'], m['month']): m for m in monthly}.values())
    return output


def component(code, charge, amount, quantity, policy, limits, evidence, entries):
    """Capture quantity, raw/presented amount, explicit policy and evidence references even when limited."""
    presented = amount
    if amount is not None:
        try:
            # Prove both captured output range and configured rounding precision before exposing any amount.
            number(decimal_text(amount))
            if quantity is not None:
                number(decimal_text(quantity))
            rounded_amount = rounded(amount, policy)
            presented = rounded_amount if policy.stage == 'component' else amount
        except (DecimalException, ValueError):
            amount, quantity, presented = None, None, None
            limits = list(limits) + ['monetary_precision_exceeded']
    return dict(code=code, kind=charge.kind, basis_value=decimal_text(quantity) if quantity is not None else None,
        unit=charge.quantity_unit, rule_id=charge.vigency_strategy, unit_price=charge.unit_price if len({c.unit_price for _, _, c in entries}) == 1 else None, tax_basis=charge.tax_basis,
        unrounded_amount=decimal_text(amount) if amount is not None else None,
        presented_amount=decimal_text(presented) if presented is not None else None,
        state='available' if amount is not None else 'limited', limitation_codes=sorted(set(limits)),
        rounding_policy=policy.model_dump(mode='json'), profile_version_refs=[str(evidence.profile_id)],
        evidence_refs=[str(r.record_id) for r in evidence.measurements],
        applied_prices=[dict(segment_start=s.valid_from.isoformat(), price=c.unit_price) for _, s, c in entries])


def result(components, reasons, closed):
    """Sum available presented components separately from a nullable complete total; never advertise partial as full."""
    reasons = sorted(set(reasons + [reason for c in components for reason in c['limitation_codes']]))
    available = [number(c['presented_amount']) for c in components if c['presented_amount'] is not None]
    subtotal = sum(available, Decimal(0))
    complete = bool(components) and len(available) == len(components) and not reasons
    # At total-stage rounding, preserve reconciliation by adding an explicit rounding adjustment component.
    policies = {str(c['rounding_policy']) for c in components if c['presented_amount'] is not None and c['rounding_policy']['stage'] == 'total'}
    if policies:
        from ecs_ec.costs.schemas import RoundingPolicy
        if len(policies) != 1 or len(policies) and any(c['rounding_policy']['stage'] != 'total' for c in components):
            complete = False
            reasons.append('incompatible_rounding_stages')
        elif complete:
            policy = RoundingPolicy.model_validate(components[0]['rounding_policy'])
            adjusted = rounded(subtotal, policy)
            if adjusted != subtotal:
                adjustment = dict(components[0], code='rounding_adjustment', kind='otro_documentado', basis_value=None,
                    unit='CLP', unit_price=None, unrounded_amount=decimal_text(adjusted-subtotal), presented_amount=decimal_text(adjusted-subtotal),
                    rule_id='captured_total_rounding', applied_prices=[])
                components = components + [adjustment]
                subtotal = adjusted
    included_tax = any(c['presented_amount'] is not None and c['tax_basis'] == 'impuesto_incluido' for c in components)
    return dict(execution_state='completado', temporal_state='cerrado' if closed else 'en_curso',
        sufficiency='completo' if complete else 'parcial' if available else 'no_calculable',
        available_subtotal=decimal_text(subtotal), complete_total=decimal_text(subtotal) if complete else None,
        net_total=None if included_tax else decimal_text(sum((number(c['presented_amount']) for c in components if c['presented_amount'] is not None and c['kind'] != 'impuesto'), Decimal(0))),
        tax_total=None if included_tax else decimal_text(sum((number(c['presented_amount']) for c in components if c['presented_amount'] is not None and c['kind'] == 'impuesto'), Decimal(0))),
        currency='CLP', reason_codes=sorted(set(reasons)), components=components, monthly_maxima=[])
