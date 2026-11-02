"""Pinned IANA calendar blocks; UTC identities preserve repeated hours and noninteger transitions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib.metadata import version
from typing import Literal

from ecs_ec.core.clock import utc
from ecs_ec.core.timezones import iana_zone

Granularity = Literal['hour', 'day', 'month', 'year']
TZDATA_VERSION = version('tzdata')


@dataclass(frozen=True)
class CalendarBlock:
    """Positive real UTC interval plus unambiguous display offsets and locked rule version."""

    start: datetime
    end: datetime
    timezone: str
    start_offset: str
    end_offset: str
    tzdata_version: str = TZDATA_VERSION


def duration_us(start, end):
    """Return exact integer UTC microseconds; reject nonpositive or naive intervals without float."""
    delta = utc(end) - utc(start)
    if delta <= timedelta(0): raise ValueError('invalid_period')
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def _occurrences(wall, zone):
    """Round-trip a naive wall time, returning zero/one/two valid UTC instants in order."""
    return sorted({candidate for fold in (0, 1)
        if (candidate := wall.replace(tzinfo=zone, fold=fold).astimezone(UTC)).astimezone(zone).replace(tzinfo=None) == wall})


def _first_valid(wall, zone):
    """Resolve calendar boundaries to earliest occurrence or the exact end of a skipped wall interval."""
    candidates = _occurrences(wall, zone)
    if candidates: return candidates[0]
    low, high = 0, 172800000000
    while low < high:
        mid = (low + high) // 2
        if _occurrences(wall + timedelta(microseconds=mid), zone): high = mid
        else: low = mid + 1
    return _occurrences(wall + timedelta(microseconds=low), zone)[0]


def _offset(value, zone):
    """Return explicit textual UTC offset, retaining seconds for historical nonminute rules."""
    raw = value.astimezone(zone).strftime('%z')
    return raw[:3] + ':' + raw[3:5] + (':' + raw[5:] if len(raw) > 5 else '')


def _block(start, end, timezone):
    """Construct only positive blocks with pinned offsets; invalid/skipped dates never create zero buckets."""
    duration_us(start, end)
    zone = iana_zone(timezone)
    return CalendarBlock(start, end, timezone, _offset(start, zone), _offset(end, zone))


@lru_cache(maxsize=1024)
def _hour_boundaries(date, timezone):
    """Enumerate local hour boundaries and exact UTC transitions across adjacent dates.

    Offsets are probed every UTC hour and transitions bisected to microsecond precision.
    Pinned IANA transitions are separated by more than an hour. Including transitions
    splits the short block at Lord Howe's30-minute change rather than forcing3600s.
    """
    zone = iana_zone(timezone)
    wall = datetime.combine(date, datetime.min.time()) - timedelta(days=1)
    result = {candidate for i in range(73) for candidate in _occurrences(wall + timedelta(hours=i), zone)}
    lower, upper = min(result), max(result)
    point = lower
    while point < upper:
        after = min(point + timedelta(hours=1), upper)
        if point.astimezone(zone).utcoffset() != after.astimezone(zone).utcoffset():
            low, high = 0, duration_us(point, after)
            before = point.astimezone(zone).utcoffset()
            while low < high:
                mid = (low + high) // 2
                if (point + timedelta(microseconds=mid)).astimezone(zone).utcoffset() == before: low = mid + 1
                else: high = mid
            result.add(point + timedelta(microseconds=low))
        point = after
    return tuple(sorted(result))


def containing_block(at, granularity, timezone):
    """Return the unique block containing aware at; use local dates and positive UTC duration."""
    at = utc(at)
    zone = iana_zone(timezone)
    local = at.astimezone(zone).replace(tzinfo=None)
    if granularity == 'hour':
        edges = _hour_boundaries(local.date(), timezone)
        for start, end in zip(edges, edges[1:]):
            if start <= at < end: return _block(start, end, timezone)
        raise ValueError('calendar_boundary_unavailable')
    lower = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == 'day': upper = lower + timedelta(days=1)
    elif granularity == 'month':
        lower = lower.replace(day=1)
        upper = lower.replace(year=lower.year + 1, month=1) if lower.month == 12 else lower.replace(month=lower.month + 1)
    elif granularity == 'year':
        lower = lower.replace(month=1, day=1)
        upper = lower.replace(year=lower.year + 1)
    else: raise ValueError('invalid_granularity')
    return _block(_first_valid(lower, zone), _first_valid(upper, zone), timezone)


def blocks(start, end, granularity, timezone):
    """Enumerate complete contained blocks in UTC order without clipping the requested filter."""
    start, end = utc(start), utc(end)
    duration_us(start, end)
    result = []
    current = containing_block(start, granularity, timezone)
    while current.start < end:
        if current.start >= start and current.end <= end: result.append(current)
        if current.end >= end: break
        current = containing_block(current.end, granularity, timezone)
    return tuple(result)
