"""Optional mail configuration never silently permits insecure production submission."""

import pytest
from ecs_ec.notifications.settings import NotificationSettings
from pydantic import ValidationError


@pytest.mark.parametrize(
    "changes",
    [
        {"smtp_starttls": False},
        {"smtp_port": 25},
        {"smtp_password": ""},
        {"smtp_username": ""},
        {"app_public_base_url": "http://example.com"},
    ],
)
def test_production_requires_verified_submission_and_https(changes):
    """Production stays opt-in and requires all configured authentication/TLS/origin prerequisites."""
    body = dict(
        _env_file=None,
        environment="production",
        notification_enabled=True,
        mail_transport="smtp_produccion",
        mail_from="ecs@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_starttls=True,
        smtp_username="synthetic",
        smtp_password="synthetic-test-only",
        app_public_base_url="https://example.com",
    )
    with pytest.raises(ValidationError):
        NotificationSettings(**(body | changes))
