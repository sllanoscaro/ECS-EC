"""Trust-only opaque operation context; public headers have no propagation interface."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
import hashlib
import hmac
import json
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Context:
    """Internal producer references; UUID objects are required, never public string IDs."""

    operation_ref: UUID | None = None
    attempt_ref: UUID | None = None
    execution_ref: UUID | None = None
    publication_ref: UUID | None = None
    parent_operation_ref: UUID | None = None
    context_status: str = "unavailable"

    def __post_init__(self):
        """Reject untyped/malformed references before context is stored or emitted."""
        if any(value is not None and type(value) is not UUID for name, value in vars(self).items() if name.endswith("_ref")):
            raise ValueError("Invalid internal context")
        if self.context_status not in {"available", "recovered", "unavailable"}:
            raise ValueError("Invalid internal context")
        if (self.operation_ref is None) != (self.context_status == "unavailable"):
            raise ValueError("Invalid internal context")

    def fields(self):
        """Return only schema-defined primitive reference fields; no identities or raw sources."""
        return {name: str(value) if isinstance(value, UUID) else value for name, value in vars(self).items()}


_CURRENT = ContextVar("ecs_technical_context", default=Context())


def current() -> Context:
    """Read this task's trusted context; unavailable is explicit outside a binding."""
    return _CURRENT.get()


@contextmanager
def bind(context: Context):
    """Temporarily bind a validated server context; always reset even on domain failure."""
    if type(context) is not Context:
        raise ValueError("Invalid internal context")
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)


def new_context(*, operation_ref=None, publication_ref=None, parent_operation_ref=None) -> Context:
    """Generate a new logical attempt/execution from typed internal references, never headers."""
    return Context(operation_ref=operation_ref or uuid4(), attempt_ref=uuid4(), execution_ref=uuid4(),
                   publication_ref=publication_ref, parent_operation_ref=parent_operation_ref, context_status="available")


def recover(context: Context) -> Context:
    """Continue a durable attempt in a new execution/tracing root, preserving logical identity."""
    if type(context) is not Context or context.operation_ref is None:
        raise ValueError("Invalid recovery context")
    return replace(context, execution_ref=uuid4(), context_status="recovered")


def resend(context: Context) -> Context:
    """Explicit resend starts a distinct logical attempt while preserving trusted publication."""
    return new_context(publication_ref=context.publication_ref, parent_operation_ref=context.operation_ref)


def opaque_reference(key: bytes, environment: str, version: str, binding: str, semantic_key: str) -> UUID:
    """HMAC a trusted semantic key with environment/version/binding separation; store neither input nor key.

    This is an internal mapping, not validation of arbitrary public references. Rotating
    keys/version changes correlation and must be declared in the active policy.
    """
    if type(key) is not bytes or len(key) < 32 or environment not in {"local", "test", "vps"}:
        raise ValueError("Invalid reference mapping")
    if any(type(v) is not str or not 1 <= len(v) <= 4096 for v in (version, binding, semantic_key)):
        raise ValueError("Invalid reference mapping")
    material = json.dumps([environment, version, binding, semantic_key], separators=(",", ":")).encode()
    return UUID(bytes=hmac.new(key, material, hashlib.sha256).digest()[:16], version=4)
