"""008 external mail configuration; sending is opt-in and production never downgrades TLS."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationSettings(BaseSettings):
    """Bounded workers and authenticated submission; credentials never enter snapshots or logs."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    notification_enabled: bool = False
    notification_cycle_seconds: float = Field(default=5, gt=0, le=5)
    notification_slots: int = Field(default=4, ge=1, le=4)
    mail_transport: Literal["local_prueba", "smtp_produccion"] = "local_prueba"
    mail_from: str = "ecs@example.test"
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = False
    smtp_socket_timeout: float = Field(default=10, gt=0, le=10)
    smtp_attempt_timeout: float = Field(default=30, gt=0, le=30)
    public_url: str = "http://localhost:8000"
    app_public_base_url: str | None = None
    environment: Literal["local", "test", "production"] = "local"

    @model_validator(mode="after")
    def deployment(self):
        """Reject unsafe origins, header injection and insecure production before any sending starts."""
        self.app_public_base_url = self.app_public_base_url or self.public_url
        parsed = urlsplit(self.app_public_base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid functional origin")
        if any(ord(c) < 32 for c in self.smtp_host) or not self.smtp_host:
            raise ValueError("Invalid SMTP host")
        from email_validator import validate_email

        try:
            self.mail_from = validate_email(
                self.mail_from,
                check_deliverability=False,
                test_environment=self.mail_transport == "local_prueba",
            ).normalized
        except ValueError:
            raise ValueError("Invalid authorized sender") from None
        if not self.notification_enabled:
            return self
        if self.mail_transport == "smtp_produccion" and (
            not self.smtp_starttls
            or not self.smtp_username
            or not self.smtp_password
            or not self.smtp_password.get_secret_value()
            or self.smtp_port != 587
        ):
            raise ValueError("Authenticated STARTTLS submission required")
        if self.environment == "production" and (
            self.mail_transport != "smtp_produccion"
            or parsed.scheme != "https"
            or parsed.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Production relay and HTTPS origin required")
        return self
