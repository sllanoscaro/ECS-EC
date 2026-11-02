"""Five identity-owned PostgreSQL tables; accounts persist and session FKs never cascade."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ecs_ec.core.database import Base


class Account(Base):
    """Permanent human identity and PHC credential; public projections explicitly exclude secrets."""

    __tablename__ = "identity_account"
    __table_args__ = (
        CheckConstraint("role IN ('operador','administrador_tecnico')", name="role"),
        CheckConstraint("status IN ('active','inactive')", name="status"),
        CheckConstraint("auth_version > 0 AND revision > 0", name="positive_versions"),
        Index("ix_identity_account_status_role", "status", "role", "id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320))
    email_key: Mapped[str] = mapped_column(String(640), unique=True)
    role: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(10))
    password_hash: Mapped[str] = mapped_column(Text)
    must_change_password: Mapped[bool] = mapped_column(Boolean)
    auth_version: Mapped[int] = mapped_column(BigInteger, default=1)
    revision: Mapped[int] = mapped_column(BigInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))
    updated_by: Mapped[str] = mapped_column(String(200))


class Session(Base):
    """Opaque human session; only the SHA-256 digest, never the bearer, is stored."""

    __tablename__ = "identity_session"
    __table_args__ = (
        CheckConstraint("octet_length(token_digest)=32", name="digest_length"),
        CheckConstraint("auth_version > 0", name="positive_version"),
        CheckConstraint("mode IN ('normal','password_change_required')", name="mode"),
        CheckConstraint("absolute_expires_at = created_at + interval '8 hours'", name="absolute_limit"),
        CheckConstraint("last_activity_at >= created_at AND idle_expires_at <= absolute_expires_at AND idle_expires_at > last_activity_at", name="activity_limits"),
        CheckConstraint("(revoked_at IS NULL) = (revocation_code IS NULL)", name="revocation_pair"),
        CheckConstraint("revocation_code IS NULL OR revocation_code IN ('logout','account_changed','credential_changed','csrf_key_retired')", name="revocation_code"),
        Index("ix_identity_session_account_revoked", "account_id", "revoked_at"),
        Index("ix_identity_session_expiry", "absolute_expires_at", "idle_expires_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_digest: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("identity_account.id", ondelete="RESTRICT"))
    auth_version: Mapped[int] = mapped_column(BigInteger)
    mode: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    csrf_key_id: Mapped[str] = mapped_column(String(40))


class Preauth(Base):
    """Ten-minute CSRF login context; contains no account, role or permission."""

    __tablename__ = "identity_preauth"
    __table_args__ = (
        CheckConstraint("octet_length(token_digest)=32", name="digest_length"),
        CheckConstraint("expires_at = created_at + interval '10 minutes'", name="expiry"),
        Index("ix_identity_preauth_expiry", "expires_at"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_digest: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    csrf_key_id: Mapped[str] = mapped_column(String(40))


class LoginBucket(Base):
    """Durable HMAC-keyed rolling failure window, with no email/IP/account FK."""

    __tablename__ = "identity_login_bucket"
    __table_args__ = (
        CheckConstraint("octet_length(bucket_key)=32", name="key_length"),
        CheckConstraint("jsonb_typeof(failed_at)='array' AND jsonb_array_length(failed_at)<=5", name="failure_window"),
    )
    bucket_key: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    failed_at: Mapped[list] = mapped_column(JSONB)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    key_id: Mapped[str] = mapped_column(String(40))


class Guard(Base):
    """Singleton row serializes account mutations across processes, not hashing or normal reads."""

    __tablename__ = "identity_guard"
    __table_args__ = (CheckConstraint("id=1", name="singleton"),)
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
