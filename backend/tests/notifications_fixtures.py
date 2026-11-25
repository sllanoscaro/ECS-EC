"""008 isolated fixtures reuse real009 database,006 accounts and001/002 providers; never inject public failures."""

import pytest


@pytest.fixture
def mail_settings():
    """Return local test transport options; no external recipient or relay is authorized."""
    from ecs_ec.notifications.settings import NotificationSettings

    return NotificationSettings(
        _env_file=None, environment="test", smtp_host="127.0.0.1", smtp_port=11025
    )
