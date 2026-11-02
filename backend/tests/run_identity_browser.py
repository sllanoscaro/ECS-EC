"""Local browser-test composition with a protected filesystem clock, never a public fixture route.

Use only ENVIRONMENT=test, an explicitly named *_test database and a private clock file.
The normal production factory does not import this module or expose its clock control.
"""

import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from ecs_ec.core.clock import SystemClock
from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app


class BrowserClock(SystemClock):
    """Add a nonnegative controlled offset from an operator-owned test file to real UTC."""

    def __init__(self, path):
        """Reject an absent/public clock file before starting a test application."""
        self.path = Path(path)
        if not self.path.is_file() or self.path.stat().st_mode & 0o077:
            raise ValueError("A protected test clock file is required")

    def now(self):
        """Return current UTC plus test offset; negative or malformed values fail closed."""
        value = int(self.path.read_text())
        if value < 0:
            raise ValueError("Negative test clock offset")
        return super().now() + timedelta(seconds=value)


def create_test_app():
    """Compose the actual identity/API with internal time injection and only synthetic test data."""
    settings = Settings()
    if settings.environment != "test" or not (make_url(settings.database_url.get_secret_value()).database or "").endswith("_test"):
        raise ValueError("Browser fixtures require a separate test environment")
    return create_app(settings, clock=BrowserClock(os.environ["IDENTITY_E2E_CLOCK_FILE"]))
