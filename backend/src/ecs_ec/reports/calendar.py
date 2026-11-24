"""005 calendar windows in the configured building timezone, preserving real DST day lengths."""

from datetime import datetime, timedelta, UTC
from ecs_ec.core.timezones import iana_zone


def window(selection, timezone, cutoff_at):
    """Return full calendar UTC bounds; reject a completely future period before admitting work."""
    zone = iana_zone(timezone)
    if selection.scale == "diario":
        first = selection.date
        last = first + timedelta(days=1)
        start = datetime(first.year, first.month, first.day, tzinfo=zone)
        end = datetime(last.year, last.month, last.day, tzinfo=zone)
    elif selection.scale == "mensual":
        y, m = selection.year, selection.month
        start = datetime(y, m, 1, tzinfo=zone)
        end = datetime(y + int(m == 12), m % 12 + 1, 1, tzinfo=zone)
    else:
        start = datetime(selection.year, 1, 1, tzinfo=zone)
        end = datetime(selection.year + 1, 1, 1, tzinfo=zone)
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    if start > cutoff_at:
        raise ValueError("future_period")
    return start, end
