"""Financial retention uses calendar anniversaries and protects against accidental shortening."""

from ecs_ec.consumption.models import instant
from ecs_ec.costs.retention import deadline


def test_leap_anniversary_and_non_decreasing_deadline():
    """A leap-day document expires on February28 locally, with a previously extended deadline preserved."""
    created = instant('2024-02-29T15:00:00Z')
    assert deadline(created, 'America/Santiago') == instant('2025-02-28T15:00:00Z')
    extended = instant('2026-03-01T00:00:00Z')
    assert deadline(created, 'America/Santiago', extended) == extended
