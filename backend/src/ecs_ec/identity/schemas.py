"""Fixed identity vocabulary, trusted principals and strictly separated HTTP projections."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

Role = Literal["operador", "administrador_tecnico"]
Status = Literal["active", "inactive"]
Mode = Literal["normal", "password_change_required"]


class DTO(BaseModel):
    """Forbid undeclared actor/role/permission fields and suppress validation input values."""

    model_config = ConfigDict(extra="forbid", from_attributes=True, hide_input_in_errors=True)


class FieldProblem(DTO):
    """Sanitized schema field path and fixed messages, excluding submitted values/context."""

    path: str
    code: str
    message: str


class ProblemView(DTO):
    """Published error envelope; operation reference is an opaque server UUID."""

    code: str
    detail: str
    operation_ref: UUID
    field_errors: list[FieldProblem]


@dataclass(frozen=True)
class Principal:
    """Request-local trusted human identity; never accepted as JSON or a durable permission token."""

    account_id: UUID
    session_id: UUID
    auth_version: int
    role: str
    mode: str
    building_id: UUID
    email: str
    revision: int
    absolute_expires_at: datetime
    idle_expires_at: datetime

    @classmethod
    def from_rows(cls, account, session, building_id):
        """Project checked DB rows without hashes, digests or bearer material."""
        return cls(account.id, session.id, account.auth_version, account.role, session.mode, building_id,
                   account.email, account.revision, session.absolute_expires_at, session.idle_expires_at)


@dataclass(frozen=True)
class IdentityMutation:
    """Sanitized participant command; the prepared credential stays private to identity."""

    account_id: UUID
    expected_revision: int | None
    fields: tuple[str, ...]
    role: str
    status: str
    renewal: bool
    actor_ref: str
    operation_ref: UUID


class AccountView(DTO):
    """Approved administrative projection; never serialize password_hash or auth_version."""

    id: UUID
    email: str
    role: Role
    status: Status
    must_change_password: bool
    revision: int
    created_at: datetime
    updated_at: datetime


class AccountIdentity(DTO):
    """Minimal self identity included only in a valid session response."""

    id: UUID
    email: str
    role: Role


class SessionView(DTO):
    """Client metadata and in-memory CSRF; the HttpOnly bearer is never serialized."""

    account: AccountIdentity
    session_state: Mode
    must_change_password: bool
    absolute_expires_at: datetime
    idle_expires_at: datetime
    csrf_token: str
    permissions: list[str]


class LoginInput(DTO):
    """Bounded syntax only; invalid email syntax inside this bound receives a generic denial."""

    email: str = Field(max_length=320, strict=True)
    password: SecretStr = Field(max_length=128, json_schema_extra={"writeOnly": True})


class PasswordInput(DTO):
    """Passwords preserve every Unicode code point and whitespace; confirmation is client-only."""

    current_password: SecretStr = Field(max_length=128, json_schema_extra={"writeOnly": True})
    new_password: SecretStr = Field(min_length=15, max_length=128, json_schema_extra={"writeOnly": True})


class AccountCreate(DTO):
    """Administrative creation; password is write-only and renewal cannot be supplied by the client."""

    email: str = Field(max_length=320, strict=True)
    role: Role
    status: Status
    initial_password: SecretStr = Field(min_length=15, max_length=128, json_schema_extra={"writeOnly": True})


class AccountUpdate(DTO):
    """Replace only the three editable account attributes, with an external revision precondition."""

    email: str = Field(max_length=320, strict=True)
    role: Role
    status: Status


class AccountReset(DTO):
    """A new initial credential only; neither previous credential nor renewal/role override is returned."""

    new_password: SecretStr = Field(min_length=15, max_length=128, json_schema_extra={"writeOnly": True})


class AccountPage(DTO):
    """Bounded canonical account listing with a signed filter-bound continuation."""

    items: list[AccountView]
    next_cursor: str | None


@dataclass(frozen=True)
class Recipient:
    """Internal current account projection; no session needed, and technical identities are never eligible."""

    account_id: UUID
    email: str | None
    role: str | None
    status: str | None
    must_change_password: bool | None
    auth_version: int | None
    revision: int | None
    eligible: bool


class AdministrationActor(DTO):
    """Stable trusted historical actor, independent of current account activation."""

    kind: Literal["account", "process", "unauthenticated"]
    account_id: UUID | None
    process_code: str | None


class AdministrationTarget(DTO):
    """Approved affected-object reference, never an original body or unapproved payload."""

    module: str
    entity_type: str
    id: UUID | None
    revision: int | None


class AdministrationEntry(DTO):
    """Read-only administrative projection of shared audit009 evidence."""

    id: UUID
    occurred_at: datetime
    actor: AdministrationActor
    action: str
    target: AdministrationTarget
    result: Literal["allowed", "denied", "rejected"]
    reason_code: str
    operation_ref: UUID


class HistoryPage(DTO):
    """Stable descending evidence page with a fixed cutoff authenticated in its continuation."""

    items: list[AdministrationEntry]
    next_cursor: str | None
    cutoff_at: datetime
