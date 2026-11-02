"""Load IANA rules from the locked tzdata wheel instead of varying host OS databases."""

from importlib.resources import files
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def iana_zone(name: str) -> ZoneInfo:
    """Read one named zone from pinned tzdata; reject paths and raise ZoneInfoNotFoundError safely."""
    if not name or name.startswith("/") or any(part in {"", ".", ".."} for part in name.split("/")):
        raise ZoneInfoNotFoundError("Unknown IANA timezone")
    try:
        with files("tzdata.zoneinfo").joinpath(*name.split("/")).open("rb") as stream:
            return ZoneInfo.from_file(stream, key=name)
    except (OSError, ValueError):
        raise ZoneInfoNotFoundError("Unknown IANA timezone") from None
