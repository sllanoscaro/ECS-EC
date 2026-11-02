"""Calendar retention boundaries in an explicit building timezone; never 365-day offsets."""

from calendar import monthrange
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ecs_ec.core.clock import utc
from ecs_ec.core.timezones import iana_zone


def _occurrences(wall: datetime, zone: ZoneInfo) -> list[datetime]:
    """Return valid UTC occurrences of a naive local time, latest first for repeated hours."""
    result = set()
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None) == wall:
            result.add(candidate)
    return sorted(result, reverse=True)


def anniversary(recorded_at: datetime, timezone: str) -> datetime:
    """Add 12 local calendar months, clamp Feb 29, use second fold or first valid gap instant.

    Inputs are an aware instant and an IANA zone; output is UTC. Raises ValueError for
    naive time and ZoneInfoNotFoundError for an unknown zone. This does not delete data.
    """
    zone = iana_zone(timezone)
    local = utc(recorded_at).astimezone(zone).replace(tzinfo=None)
    year = local.year + 1
    target = local.replace(year=year, day=min(local.day, monthrange(year, local.month)[1]))
    candidates = _occurrences(target, zone)
    if candidates:
        return candidates[0]
    # A timezone gap is contiguous. Binary search to microsecond precision for its end;
    # two days also covers IANA transitions that skipped an entire calendar date.
    low, high = 0, 2 * 24 * 60 * 60 * 1_000_000
    while low < high:
        middle = (low + high) // 2
        if _occurrences(target + timedelta(microseconds=middle), zone):
            high = middle
        else:
            low = middle + 1
    return _occurrences(target + timedelta(microseconds=low), zone)[0]
