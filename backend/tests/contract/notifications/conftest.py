"""Share008 real-provider fixtures with contract tests; no public bootstrap endpoints."""

from backend.tests.integration.notifications.conftest import (  # noqa: F401
    identity_settings,
    notification_context,
    notification_database_reset,
)
