"""Configuration and test-database gates reject unsafe destinations before any connection."""

import pytest
from pydantic import ValidationError

from conftest import checked_test_url
from ecs_ec.core.clock import FrozenClock
from ecs_ec.core.settings import Settings
from ecs_ec.core.timezones import iana_zone


@pytest.mark.parametrize("changes", [
    {"database_url": "sqlite:///wrong"}, {"building_timezone": "../UTC"},
    {"building_timezone": "Unknown/Place"}, {"public_url": "http://user:password@example.test"},
    {"public_url": "https://example.test/private"},
    {"environment": "production", "public_url": "http://example.test"},
    {"environment": "production", "public_url": "https://localhost"},
    {"environment": "production", "public_url": "https://example.test"},
])
def test_invalid_configuration(changes):
    """Reject invalid backend, timezone, public origin and synthetic production credentials."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **changes)


def test_test_database_gate_reads_dotenv(tmp_path, monkeypatch):
    """A matching production destination from .env must be rejected despite missing shell DATABASE_URL."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = "postgresql+psycopg://synthetic:synthetic@localhost/ecs_test"
    (tmp_path / ".env").write_text("DATABASE_URL=" + url + "\n")
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    with pytest.raises(pytest.UsageError, match="must be distinct"):
        checked_test_url()


@pytest.mark.parametrize("value", [None, "sqlite:///ecs_test", "postgresql+psycopg://localhost/production"])
def test_test_database_gate_rejects_missing_or_unmarked(value, monkeypatch):
    """Tests cannot silently fall back to an ordinary database or a substitute SQLite engine."""
    if value is None:
        monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("TEST_DATABASE_URL", value)
    with pytest.raises(pytest.UsageError):
        checked_test_url()


def test_pinned_timezone_and_monotonic_clock(clock):
    """Pinned IANA rules load by name and the internal test clock advances only forwards."""
    assert iana_zone("America/Santiago").key == "America/Santiago"
    start = clock.now()
    clock.advance(60)
    assert (clock.now() - start).total_seconds() == clock.monotonic() == 60
    with pytest.raises(ValueError):
        clock.advance(-1)
