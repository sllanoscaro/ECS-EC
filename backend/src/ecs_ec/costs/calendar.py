"""004 versioned month/peak rules in an explicit IANA zone; no default billing month or proration."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ecs_ec.costs.profiles import applicable_segments


def shift_month(year, month, offset):
    """Shift a calendar month arithmetically, preserving distinct month identities across years."""
    ordinal = year * 12 + month - 1 + offset
    year, month0 = divmod(ordinal, 12)
    return year, month0 + 1


def month_bounds(reference, timezone):
    """Return actual UTC boundaries of a local month, respecting DST rather than assuming a fixed duration."""
    year, month = map(int, reference.split('-'))
    next_year, next_month = shift_month(year, month, 1)
    zone = ZoneInfo(timezone)
    return datetime(year, month, 1, tzinfo=zone).astimezone(UTC), datetime(next_year, next_month, 1, tzinfo=zone).astimezone(UTC)


def history_window(reference, timezone):
    """Return twelve calendar months including the explicitly resolved billing month."""
    year, month = map(int, reference.split('-'))
    lower_year, lower_month = shift_month(year, month, -11)
    return month_bounds(f'{lower_year:04}-{lower_month:02}', timezone)[0], month_bounds(reference, timezone)[1]


def previous_peak_months(reference, months):
    """Find the immediately preceding contiguous peak season, including a season spanning two years."""
    year, month = map(int, reference.split('-'))
    result, found = [], False
    for offset in range(-1, -25, -1):
        y, m = shift_month(year, month, offset)
        if m in months:
            result.append(f'{y:04}-{m:02}')
            found = True
        elif found:
            break
    return tuple(reversed(result))


def is_peak(start, end, calendar, timezone):
    """Classify an entire real quarter-hour block, not just its first instant, against the captured local window."""
    zone = ZoneInfo(timezone)
    first, last = start.astimezone(zone), (end - timedelta(microseconds=1)).astimezone(zone)
    return (first.date() == last.date() and first.month in calendar.months and first.weekday() in calendar.weekdays
        and first.date() not in calendar.excluded_dates and calendar.start_time <= first.strftime('%H:%M')
        and last.strftime('%H:%M') < calendar.end_time)


def resolve_month(evidence):
    """Validate explicit document metadata or derive a month using one supported, documented policy version."""
    request, profile = evidence.request, evidence.profile
    if profile is None:
        return None, None, None
    segments = applicable_segments(profile, request.start, request.end)
    cursor = request.start
    for segment in segments:
        if max(segment.valid_from, request.start) != cursor:
            return None, None, None
        cursor = min(segment.valid_to or request.end, request.end)
    if cursor != request.end:
        return None, None, None
    policies = {s.billing_month_policy.model_dump_json() for s in segments}
    if len(policies) != 1:
        return None, None, None
    policy = segments[0].billing_month_policy
    if not policy.source_refs:
        return None, None, policy.version
    if policy.mode == 'explicit_evidence':
        source = request.billing_month_source_ref
        if (source is None or source.supply_id != request.supply_id or source.start != request.start or source.end != request.end
                or source.billing_month_ref != request.billing_month_ref):
            return None, None, policy.version
        return request.billing_month_ref, source, policy.version
    if request.billing_month_ref is not None:
        from ecs_ec.costs.repository import CostsProblem
        raise CostsProblem('month_not_client_selectable', 422)
    if policy.rule_id not in {'cycle_end_month_v1', 'cycle_start_month_v1'}:
        return None, None, policy.version
    # The rule itself is a captured administrative choice; no rule is selected by default.
    instant = request.end - timedelta(microseconds=1) if policy.rule_id == 'cycle_end_month_v1' else request.start
    reference = instant.astimezone(ZoneInfo(profile.timezone)).strftime('%Y-%m')
    from ecs_ec.costs.schemas import MonthEvidence
    source = MonthEvidence(document_reference=policy.source_refs[0], supply_id=request.supply_id,
        start=request.start, end=request.end, billing_month_ref=reference)
    return reference, source, policy.version
