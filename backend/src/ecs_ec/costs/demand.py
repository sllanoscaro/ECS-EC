"""Exact quarter-hour power and coverage-proven monthly maxima; no hourly reconstruction or missing zeros."""

from datetime import timedelta
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo

from ecs_ec.costs.calendar import is_peak, month_bounds, shift_month, previous_peak_months
from ecs_ec.costs.money import number, decimal_text


def block_power(energy, duration_us):
    """Convert exact15-minute energy with P=E/0.25=4E; every other resolution is insufficient."""
    if duration_us != 900000000:
        return None
    with localcontext() as context:
        context.prec = 128
        return number(energy) * 4


def top_two(values):
    """Average the two largest maxima from distinct month IDs; equal values from different months both count."""
    distinct = dict(values)
    if len(distinct) < 2:
        return None
    with localcontext() as context:
        context.prec = 128
        return sum(sorted((number(v) for v in distinct.values()), reverse=True)[:2]) / 2


def month_maximum(rows, reference, timezone, calendar, *, peak=False):
    """Require every eligible actual quarter-hour in a month, including DST, before accepting its maximum."""
    start, end = month_bounds(reference, timezone)
    values = {}
    for row in rows:
        local = row.start.astimezone(ZoneInfo(timezone))
        if (row.start >= start and row.end <= end and row.end - row.start == timedelta(minutes=15)
                and local.minute % 15 == 0 and local.second == 0 and local.microsecond == 0):
            if not peak or is_peak(row.start, row.end, calendar, timezone):
                values[row.start] = block_power(row.energy_kwh, 900000000)
    cursor, expected = start, set()
    while cursor < end:
        upper = cursor + timedelta(minutes=15)
        if not peak or is_peak(cursor, upper, calendar, timezone):
            expected.add(cursor)
        cursor = upper
    if not expected or set(values) != expected:
        return None
    return max(values.values())


def bases(evidence, segment):
    """Return supplied-power/peak bases plus monthly evidence; incomplete months limit only their dependent charge."""
    reference = evidence.billing_month_ref
    if any(int(value.split(':')[1]) % 15 for value in (segment.peak_calendar.start_time, segment.peak_calendar.end_time)):
        return None, None, (), 'unsupported_peak_alignment'
    if reference is None:
        return None, None, (), 'billing_month_unresolved'
    if segment.historical_rule != 'two_monthly_maxima_12_months_v1':
        return None, None, (), 'unsupported_historical_rule'
    year, month = map(int, reference.split('-'))
    months = [f'{y:04}-{m:02}' for y, m in (shift_month(year, month, offset) for offset in range(-11, 1))]
    supplied = [(ref, month_maximum(evidence.history, ref, evidence.request.timezone, segment.peak_calendar)) for ref in months]
    supplied_base = top_two([(ref, decimal_text(value)) for ref, value in supplied]) if all(v is not None for _, v in supplied) else None
    peak_months = (reference,) if month in segment.peak_calendar.months else previous_peak_months(reference, segment.peak_calendar.months)
    peak_values = [(ref, month_maximum(evidence.history, ref, evidence.request.timezone, segment.peak_calendar, peak=True)) for ref in peak_months]
    peak_base = (peak_values[0][1] if month in segment.peak_calendar.months and peak_values else
        top_two([(ref, decimal_text(value)) for ref, value in peak_values]) if peak_values and all(v is not None for _, v in peak_values) else None)
    maxima = tuple(dict(month=ref, maximum_kw=decimal_text(value) if value is not None else None,
        coverage='complete' if value is not None else 'incomplete', kind=kind)
        for kind, values in (('supplied', supplied), ('peak', peak_values)) for ref, value in values)
    return supplied_base, peak_base, maxima, 'insufficient_demand_history'
