"""Identity-only deployment options; secrets are external and stable across restarts."""

import base64
import ipaddress
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def key_bytes(value: SecretStr) -> bytes:
    """Decode a base64url external key with >=256 bits; never echo invalid key material."""
    try:
        raw = value.get_secret_value()
        decoded = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True)
        if len(decoded) < 32:
            raise ValueError()
        return decoded
    except Exception:
        raise ValueError("A base64url key of at least 32 bytes is required") from None


class IdentitySettings(BaseSettings):
    """Validate identity keys, public origin, trusted proxy networks and memory concurrency."""

    model_config = SettingsConfigDict(env_prefix="IDENTITY_", env_file=".env", extra="ignore", hide_input_in_errors=True)
    csrf_key: SecretStr
    login_bucket_key: SecretStr
    csrf_key_id: str = Field(default="csrf-v1", pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    login_bucket_key_id: str = Field(default="bucket-v1", pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    previous_login_bucket_key: SecretStr | None = None
    previous_login_bucket_key_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    public_url: str = "https://localhost:8000"
    environment: Literal["local", "test", "production"] = "local"
    development_http: bool = False
    trusted_proxies: list[str] = Field(default_factory=list)
    hash_concurrency: int = Field(default=2, ge=1, le=8)
    building_id: UUID = UUID("00000000-0000-0000-0000-000000000001")

    @field_validator("previous_login_bucket_key", "previous_login_bucket_key_id", mode="before")
    @classmethod
    def optional_previous(cls, value):
        """Treat an unconfigured optional Compose rotation variable as absent, never as a usable key."""
        return None if value == "" else value

    @field_validator("csrf_key", "login_bucket_key", "previous_login_bucket_key")
    @classmethod
    def valid_key(cls, value):
        """Require persistent externally provisioned HMAC keys, preserving SecretStr redaction."""
        if value is not None:
            key_bytes(value)
        return value

    @field_validator("trusted_proxies")
    @classmethod
    def explicit_proxies(cls, values):
        """Accept explicit IP/CIDR networks, rejecting universal trust and hostnames."""
        for value in values:
            network = ipaddress.ip_network(value, strict=False)
            if network.prefixlen == 0:
                raise ValueError("Universal proxy trust is forbidden")
        return values

    @model_validator(mode="after")
    def safe_deployment(self):
        """Allow HTTP only when explicitly enabled on a loopback origin outside production."""
        origin = urlsplit(self.public_url)
        if origin.port is not None and not 1 <= origin.port <= 65535:
            raise ValueError("Public URL requires a valid port")
        if origin.scheme not in {"http", "https"} or not origin.hostname or origin.username or origin.password:
            raise ValueError("Public URL must be an HTTP(S) origin without credentials")
        if origin.query or origin.fragment or origin.path not in {"", "/"}:
            raise ValueError("Public URL must be an origin")
        if self.development_http and (self.environment == "production" or origin.hostname not in {"localhost", "127.0.0.1", "::1"}):
            raise ValueError("Development HTTP is restricted to local loopback origins")
        if origin.scheme == "http" and not self.development_http:
            raise ValueError("HTTPS is required without the explicit local development option")
        if key_bytes(self.csrf_key) == key_bytes(self.login_bucket_key):
            raise ValueError("CSRF and bucket keys must be distinct")
        if bool(self.previous_login_bucket_key) != bool(self.previous_login_bucket_key_id):
            raise ValueError("Both previous bucket key and ID are required for rotation")
        if self.previous_login_bucket_key_id == self.login_bucket_key_id:
            raise ValueError("Rotation requires distinct key IDs")
        return self

    @property
    def origin(self) -> str:
        """Return the exact canonical configured origin for transport/CSRF comparisons."""
        return self.public_url.rstrip("/")
