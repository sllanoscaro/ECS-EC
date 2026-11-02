"""Strict query timestamps: explicit offsets must round-trip through the building's IANA zone."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ecs_ec.consumption.models import Period, instant, iana


def resolve_period(start, end, timezone, building_timezone):
    """Return a UTC period, rejecting foreign zones, nonexistent local times and mismatched offsets."""
    if iana(timezone) != building_timezone:
        raise ValueError('invalid_timezone')
    zone = ZoneInfo(timezone)
    for value in (start, end):
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        normalized = instant(value)
        if parsed.utcoffset() != normalized.astimezone(zone).utcoffset():
            raise ValueError('invalid_offset')
    return Period(start=start, end=end)


def local_day(now, timezone):
    """Return the actual local calendar day; DST days need not be twenty-four hours."""
    local = now.astimezone(ZoneInfo(timezone))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return Period(start=start, end=start + timedelta(days=1))


def timestamp(value, timezone):
    """Keep all microseconds while projecting an aware instant into the explicit building zone."""
    return value.astimezone(ZoneInfo(timezone)).isoformat()
