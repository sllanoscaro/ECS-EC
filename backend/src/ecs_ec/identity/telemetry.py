"""006 safe instrumentation over007; context is local to each request or host CLI execution.

No arguments, principals, session bearers, addresses or exceptions cross this adapter.
Business transactions and durable functional audit remain entirely owned by the caller.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from uuid import UUID
from ecs_ec.observability.context import new_context

_emitter = ContextVar('identity_emitter', default=None)
_reference = ContextVar('identity_reference', default=None)
_handle = ContextVar('identity_operation', default=None)


@contextmanager
def emission_scope(emitter, reference=None):
    """Bind an existing007 emitter and server-generated reference; always reset after the scope."""
    token = _emitter.set(emitter)
    ref = _reference.set(reference if type(reference) is UUID else None)
    try:
        yield
    finally:
        _reference.reset(ref)
        _emitter.reset(token)


def stage(name):
    """Emit an internal catalog stage only, without ever forwarding producer values or blocking a commit."""
    try:
        emitter = _emitter.get()
        if emitter:
            emitter.stage(_handle.get(), name)
    except Exception:
        pass


@contextmanager
def operation(name):
    """Emit one terminal after a real006 operation, distinguishing expected denial from technical failure."""
    emitter, handle = _emitter.get(), None
    outcome, code = 'success', 'ok'
    try:
        if emitter:
            parent = _handle.get()
            context = new_context(parent_operation_ref=parent.context.operation_ref if parent else _reference.get())
            handle = emitter.begin(name, 'identity', context=context, parent=parent)
    except Exception:
        pass
    token = _handle.set(handle)
    try:
        yield
    except Exception as error:
        status = getattr(error, 'status', 503)
        outcome = 'expected_rejection' if status < 500 else 'unexpected_error'
        code = 'authentication_failed' if name == 'identity.authenticate' and status < 500 else 'permission_denied' if status in (401,403) else 'invalid_input' if status < 500 else 'database_unavailable'
        raise
    finally:
        _handle.reset(token)
        try:
            if emitter:
                emitter.complete(handle, outcome=outcome, code=code)
        except Exception:
            pass


def observe(name):
    """Decorate an asynchronous006 entry point; maintain its signature and functional exceptions."""
    def decorate(function):
        """Build one wrapper without inspecting or retaining the function's arguments."""
        @wraps(function)
        async def wrapped(*args, **kwargs):
            """Run the producer within the current request/CLI emission context."""
            with operation(name):
                return await function(*args, **kwargs)
        return wrapped
    return decorate
