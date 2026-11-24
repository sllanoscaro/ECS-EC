"""001/002 instrumentation adapters; native values never enter technical signals.

001 observes its routes;002 observes reception, aggregates, pending work and retention.
The real007 emitter owns transport; technical failures cannot change functional results.
"""

from functools import wraps
from uuid import UUID
from ecs_ec.observability.context import Context


def observe(operation, stage):
    """Wrap a001 route with one trusted007 operation and fixed stage/result codes.

    Operation/stage are internal catalog constants. Inputs, entities and exception text
    are never forwarded; only a server-generated UUID correlates the request. The route
    owns its transaction and authorization; terminal success occurs after it returns.
    """

    def decorate(function):
        """Retain the HTTP signature and response contract of the wrapped route."""

        @wraps(function)
        async def wrapped(request, *args, **kwargs):
            """Invoke the functional route even when technical admission/completion fails."""
            emitter = getattr(request.app.state, "telemetry", None)
            handle = None
            try:
                reference = getattr(request.state, "operation_ref", None)
                context = (
                    Context(operation_ref=reference, context_status="available")
                    if type(reference) is UUID
                    else None
                )
                if emitter:
                    handle = emitter.begin(operation, "consumption", context=context)
            except Exception:
                pass
            outcome, code = "success", "ok"
            try:
                result = await function(request, *args, **kwargs)
                return result
            except Exception as error:
                status = getattr(error, "status", 503)
                outcome = "expected_rejection" if status < 500 else "unexpected_error"
                code = (
                    "permission_denied"
                    if status in (401, 403)
                    else "invalid_input"
                    if status < 500
                    else "database_unavailable"
                )
                raise
            finally:
                try:
                    if emitter:
                        emitter.stage(handle, stage, outcome=outcome, code=code)
                        emitter.complete(handle, outcome=outcome, code=code)
                except Exception:
                    pass

        return wrapped

    return decorate


def restored(fields):
    """Decode producer-owned UUID metadata; absent/corrupt historical context stays unavailable."""
    try:
        return Context(
            **{
                key: UUID(value) if key.endswith("_ref") and value else value
                for key, value in fields.items()
            }
        )
    except TypeError, ValueError, AttributeError:
        return Context()


def signal(emitter, handle, *, stage=None, **fields):
    """Keep transport exceptions outside every owner transaction and functional result."""
    try:
        if emitter:
            return (
                emitter.stage(handle, stage, **fields)
                if stage
                else emitter.complete(handle, **fields)
            )
    except Exception:
        pass


def begin(emitter, operation, context):
    """Admit only internal catalog constants and validated context, tolerating broken destinations."""
    try:
        return (
            emitter.begin(operation, "consumption", context=context)
            if emitter
            else None
        )
    except Exception:
        return None


def internal(operation, stage):
    """Observe a002 provider execution after its owner commits, without persisting telemetry outcomes."""
    from ecs_ec.observability.context import bind, current, new_context

    def decorate(function):
        """Keep the provider signature and domain exceptions intact."""

        @wraps(function)
        async def wrapped(self, *args, **kwargs):
            """Use a fresh internal child operation; technical failures never change business work."""
            emitter = getattr(self, "telemetry", None)
            parent = current()
            context = new_context(
                publication_ref=parent.publication_ref,
                parent_operation_ref=parent.operation_ref,
            )
            handle = begin(emitter, operation, context)
            outcome, code = "success", "ok"
            try:
                with bind(context), recording(emitter, handle):
                    result = await function(self, *args, **kwargs)
                if isinstance(result, tuple) and any(
                    isinstance(r, dict) and r.get("status") == "rejected"
                    for r in result
                ):
                    outcome, code = "expected_rejection", "invalid_input"
                return result
            except Exception:
                outcome, code = "unexpected_error", "processing_interrupted"
                raise
            finally:
                signal(emitter, handle, stage=stage, outcome=outcome, code=code)
                signal(emitter, handle, outcome=outcome, code=code)

        return wrapped

    return decorate


def reception_counts(outcome):
    """Count immutable original positions, including commits from earlier recovered executions."""
    results = outcome.results
    invalid = {
        "unknown_category",
        "invalid_measurement",
        "invalid_energy",
        "source_building_mismatch",
        "source_mismatch",
        "invalid_unit",
        "unsupported_unit",
        "energy_out_of_supported_range",
        "source_configuration_missing",
        "source_configuration_changed",
        "unknown_or_uninstalled_source",
    }
    return dict(
        records_seen=len(results),
        records_accepted=sum(r.status == "accepted" for r in results),
        records_duplicate=sum(r.status == "duplicate" for r in results),
        records_invalid=sum(
            r.status == "rejected" and r.reason_code in invalid for r in results
        ),
        records_other_rejected=sum(
            r.status == "rejected" and r.reason_code not in invalid for r in results
        ),
    )


from contextvars import ContextVar
from contextlib import contextmanager

_ACTIVE = ContextVar("consumption_technical_execution", default=(None, None))


@contextmanager
def recording(emitter, handle):
    """Scope aggregate progress to one trusted execution without global mutable handles."""
    token = _ACTIVE.set((emitter, handle))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def progress(stage, **fields):
    """Report a flushed stage only; functional acceptance still requires its owner's commit."""
    emitter, handle = _ACTIVE.get()
    signal(emitter, handle, stage=stage, **fields)
