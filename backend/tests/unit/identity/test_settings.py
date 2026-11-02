"""Identity deployment configuration must fail closed without persistent external keys."""

import pytest
from pydantic import ValidationError

from ecs_ec.identity.settings import IdentitySettings


def configuration(**changes):
    """Synthetic test configuration; these values are never operational credentials."""
    return IdentitySettings(_env_file=None, csrf_key="a" * 43, login_bucket_key="b" * 43,
                            **({"public_url": "http://localhost:8000", "development_http": True,
                                "environment": "test"} | changes))


def test_explicit_local_configuration():
    """Allow explicit loopback development with distinct persistent keys and bounded hashing."""
    settings = configuration()
    assert settings.hash_concurrency == 2
    assert "a" * 43 not in repr(settings)


@pytest.mark.parametrize("changes", [
    {"development_http": False}, {"public_url": "http://example.test"},
    {"environment": "production"}, {"hash_concurrency": 0},
    {"trusted_proxies": ["0.0.0.0/0"]}, {"public_url": "http://user:pass@localhost"},
])
def test_reject_unsafe_configuration(changes):
    """No HTTP public/production exception, unbounded proxy trust or invalid resource limit."""
    with pytest.raises(ValidationError):
        configuration(**changes)


def test_missing_keys_rejected(monkeypatch):
    """A process restart must never silently generate replacement HMAC keys."""
    monkeypatch.delenv("IDENTITY_CSRF_KEY", raising=False)
    monkeypatch.delenv("IDENTITY_LOGIN_BUCKET_KEY", raising=False)
    with pytest.raises(ValidationError):
        IdentitySettings(_env_file=None)
