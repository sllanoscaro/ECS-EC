"""A malformed optional SMTP setting cannot prevent unrelated API readiness."""

from ecs_ec.core.settings import Settings
from ecs_ec.main import create_app
from pydantic import SecretStr


async def test_invalid_mail_environment_disables_only_mail(
    identity, test_url, clock, tmp_path, monkeypatch
):
    """The fallback supplies all fields explicitly instead of re-reading the malformed environment."""
    monkeypatch.setenv("SMTP_PORT", "invalid-test-port")
    monkeypatch.setenv("NOTIFICATION_CYCLE_SECONDS", "invalid-test-cycle")
    (tmp_path / "index.html").write_text("Synthetic export")
    settings = Settings(
        _env_file=None,
        database_url=SecretStr(test_url),
        environment="test",
        web_directory=tmp_path,
        identity_enabled=True,
    )
    app = create_app(settings, clock=clock, identity_service=identity)
    async with app.router.lifespan_context(app):
        assert app.state.notification_configuration_invalid
        assert app.state.notifications.settings.notification_enabled is False
