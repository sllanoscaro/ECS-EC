"""Validated external configuration; local defaults are explicitly synthetic."""

from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from ecs_ec.core.timezones import iana_zone


class Settings(BaseSettings):
    """Load environment/.env, validate infrastructure, and hide database credentials in repr."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    environment: Literal["local", "test", "production"] = "local"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://ecs_local:synthetic-local-only@localhost:5432/ecs_local"
    )
    public_url: str = "http://localhost:8000"
    building_timezone: str = "America/Santiago"
    web_directory: Path = Path(__file__).resolve().parents[1] / "web"

    @field_validator("database_url")
    @classmethod
    def check_database(cls, value: SecretStr) -> SecretStr:
        """Accept only PostgreSQL/Psycopg with an explicit database; expose no URL on failure."""
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and bool(url.database)
        except Exception:
            valid = False
        if not valid:
            raise ValueError("PostgreSQL/Psycopg database URL required")
        return value

    @field_validator("building_timezone")
    @classmethod
    def check_zone(cls, value: str) -> str:
        """Require a known IANA timezone, never the host's implicit timezone."""
        try:
            iana_zone(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Known IANA timezone required") from None
        return value

    @model_validator(mode="after")
    def check_deployment(self):
        """Production requires HTTPS and externally supplied non-synthetic credentials."""
        from urllib.parse import urlsplit
        parsed = urlsplit(self.public_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Public URL requires an HTTP(S) origin without credentials")
        if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Public URL must be an origin")
        if self.environment == "production":
            db = make_url(self.database_url.get_secret_value())
            if parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Production requires a public HTTPS origin")
            if not db.password or db.password == "synthetic-local-only":
                raise ValueError("Production requires external database credentials")
        return self
