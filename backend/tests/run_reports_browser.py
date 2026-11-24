"""005 opt-in browser composition with a protected internal failure switch; production never imports this module.

Only an explicit *_test database and a private0600 file enable this harness. No
public route, header, cookie or query parameter can request a controlled failure.
"""

import os
from pathlib import Path
from sqlalchemy.engine import make_url
from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app
from ecs_ec.reports.layout import CompositionError


def create_test_app():
    """Compose real producers and their worker; inject only an internal composition failure for an E2E case."""
    import ecs_ec.reports.worker as worker

    settings = Settings()
    control = Path(os.environ["REPORTS_E2E_FAILURE_FILE"])
    if settings.environment != "test" or not (
        make_url(settings.database_url.get_secret_value()).database or ""
    ).endswith("_test"):
        raise ValueError("separate_reports_test_database_required")
    if not control.is_file() or control.stat().st_mode & 0o077:
        raise ValueError("private_failure_control_required")
    real_render = worker.render

    def controlled(*args, **kwargs):
        """Exercise the actual admitted-failure transaction without substituting a snapshot or a PDF."""
        if control.read_text() == "composition":
            raise CompositionError("synthetic_composition_limit")
        return real_render(*args, **kwargs)

    worker.render = controlled
    return create_app(settings)
