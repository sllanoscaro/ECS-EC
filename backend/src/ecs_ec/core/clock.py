"""Injectable wall/monotonic clocks; no HTTP route can change time."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


def utc(value: datetime) -> datetime:
    """Normalize an aware instant to UTC; reject naive timestamps."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware timestamp is required")
    return value.astimezone(UTC)


class Clock(Protocol):
    """Internal time port used by services; monotonic values measure durations only."""

    def now(self) -> datetime:
        """Return the current aware UTC instant."""
        ...

    def monotonic(self) -> float:
        """Return a nondecreasing duration reference in seconds."""
        ...


class SystemClock:
    """Read conventional process wall time and monotonic time without side effects."""

    def now(self) -> datetime:
        """Return the system UTC instant."""
        return datetime.now(UTC)

    def monotonic(self) -> float:
        """Return the process-independent monotonic counter."""
        return time.monotonic()


@dataclass
class FrozenClock:
    """Deterministic internal test clock; advance updates both counters."""

    instant: datetime
    elapsed: float = 0.0

    def __post_init__(self):
        """Reject naive test values and normalize the initial instant."""
        self.instant = utc(self.instant)

    def now(self) -> datetime:
        """Return the configured UTC instant."""
        return self.instant

    def monotonic(self) -> float:
        """Return the explicitly advanced duration reference."""
        return self.elapsed

    def advance(self, seconds: float) -> None:
        """Advance both counters; negative durations are rejected."""
        if seconds < 0:
            raise ValueError("Cannot move clock backwards")
        self.instant += timedelta(seconds=seconds)
        self.elapsed += seconds
