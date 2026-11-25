"""008 pure nominal calendar over locked tzdata; no scheduler, storage or SMTP effects.

Elapsed intervals are UTC anchored. Calendar recurrences retain nominal day/time,
resolve gaps to their first valid instant and use fold0 once. Retention intentionally
uses a different fold policy in009. Only an explicitly identified first cut may be empty.
"""

from calendar import monthrange
from datetime import UTC, datetime, timedelta
from importlib.metadata import version

from ecs_ec.core.timezones import iana_zone
from ecs_ec.notifications.schemas import instant


def tzdata_version():
    """Return installed locked wheel version, never infer it from the host timezone database."""
    return version("tzdata")


def stamp(value):
    """Serialize an aware UTC technical/functional instant without changing its cutoff."""
    return instant(value).isoformat().replace("+00:00", "Z")


def resolve(wall, zone):
    """Resolve one naive nominal local slot to first UTC fold or the exact end of a gap."""

    def valid(candidate):
        """Return distinct UTC mappings which round-trip to the same requested wall time."""
        return sorted(
            {
                candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                for fold in (0, 1)
                if candidate.replace(tzinfo=zone, fold=fold)
                .astimezone(UTC)
                .astimezone(zone)
                .replace(tzinfo=None)
                == candidate
            }
        )

    candidates = valid(wall)
    if candidates:
        return candidates[0], "primera_hora_repetida" if len(
            candidates
        ) > 1 else "ninguno"
    low, high = 0, 172800000000
    while low < high:
        middle = (low + high) // 2
        if valid(wall + timedelta(microseconds=middle)):
            high = middle
        else:
            low = middle + 1
    candidates = valid(wall + timedelta(microseconds=low))
    if not candidates:
        raise ValueError("Unresolvable calendar slot")
    return candidates[0], "hora_inexistente"


def next_occurrences(schedule, timezone, after, count=3):
    """Return up to three strictly future slots with original windows and an explicit empty initial cut.

    starts_at bounds the first window; no older activation backlog is generated.
    Invalid schedules are rejected by RuleInput before this pure trusted boundary.
    """
    if not 1 <= count <= 3:
        raise ValueError("Bounded preview required")
    zone = iana_zone(timezone)
    after = instant(after)
    starts = instant(schedule["starts_at"])
    kind = schedule["kind"]
    candidates = []
    if kind == "intervalo":
        delta = timedelta(
            **{
                schedule["interval_unit"]
                .replace("minutos", "minutes")
                .replace("horas", "hours"): schedule["interval_value"]
            }
        )
        index = max(0, (after - starts) // delta + 1)
        for n in range(index - 1, index + count + 1):
            value = starts + n * delta
            candidates.append(
                (
                    value,
                    value.astimezone(zone).replace(tzinfo=None).isoformat(),
                    "ninguno",
                )
            )
    else:
        base = max(after, starts).astimezone(zone).replace(tzinfo=None)
        hour, minute = map(int, schedule["local_time"].split(":"))
        dates = []
        if kind in {"diaria", "semanal"}:
            for offset in range(-8, 33):
                day = base.date() + timedelta(days=offset)
                if kind == "diaria" or day.isoweekday() == schedule["weekday"]:
                    dates.append((day.year, day.month, day.day, day.day))
        elif kind == "mensual":
            for offset in range(-2, 39):
                year, month = divmod(base.year * 12 + base.month - 1 + offset, 12)
                month += 1
                nominal = schedule["day_of_month"]
                dates.append(
                    (year, month, min(nominal, monthrange(year, month)[1]), nominal)
                )
        elif kind == "anual":
            for year in range(base.year - 2, base.year + 6):
                month = schedule["month"]
                nominal = schedule["day_of_month"]
                dates.append(
                    (year, month, min(nominal, monthrange(year, month)[1]), nominal)
                )
        else:
            raise ValueError("Unknown recurrence")
        for year, month, day, nominal in dates:
            value, adjustment = resolve(datetime(year, month, day, hour, minute), zone)
            if day != nominal and adjustment == "ninguno":
                adjustment = "ultimo_dia_valido"
            candidates.append(
                (
                    value,
                    f"{year:04}-{month:02}-{nominal:02}T{hour:02}:{minute:02}:00",
                    adjustment,
                )
            )
    candidates.sort()
    result = []
    for index, (value, nominal, adjustment) in enumerate(candidates):
        if value <= after or value < starts:
            continue
        previous = candidates[index - 1][0] if index else starts
        lower = max(starts, previous)
        result.append(
            dict(
                nominal_local=nominal,
                timezone=timezone,
                resolved_at=stamp(value),
                window=dict(start=stamp(lower), end=stamp(value)),
                calendar_adjustment=adjustment,
                initial_window_empty=lower == value,
            )
        )
        if len(result) == count:
            break
    if len(result) != count:
        raise ValueError("Calendar range exhausted")
    return result
