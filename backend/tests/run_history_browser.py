"""Isolated002 browser harness with a private frozen clock; production never imports this module.

Run only against an explicit *_test database. An ISO timestamp in a0600 file controls
business time without changing the host clock or adding public control/seed routes.
"""
import os
from pathlib import Path
from sqlalchemy.engine import make_url
from ecs_ec.consumption.models import instant
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app


class HistoryBrowserClock(SystemClock):
    """Read a protected operator-owned frozen UTC instant and retain a real monotonic timer."""

    def __init__(self, path):
        """Require a private existing file; malformed timestamps fail closed when read."""
        self.path = Path(path)
        if not self.path.is_file() or self.path.stat().st_mode & 0o077:
            raise ValueError('protected_history_clock_required')

    def now(self):
        """Read exact ISO instant on each call, enabling boundary tests with no HTTP mutation seam."""
        return instant(self.path.read_text().strip())


def checked_settings():
    """Reject production/non-test destinations before provisioning or serving the internal harness."""
    settings = Settings()
    if settings.environment != 'test' or not (make_url(settings.database_url.get_secret_value()).database or '').endswith('_test'):
        raise ValueError('separate_history_test_database_required')
    return settings


def create_test_app():
    """Compose the actual monolith and real006 sessions with only an internally injected test clock."""
    return create_app(checked_settings(), clock=HistoryBrowserClock(os.environ['HISTORY_E2E_CLOCK_FILE']))
