"""004 safe route instrumentation and committed service stages over the optional007 emitter.

Only fixed catalog fields and server UUIDs cross this boundary. Financial inputs,
responses, actors and exceptions remain in004; failures never alter its transactions.
"""

from contextvars import ContextVar
from functools import wraps
from uuid import UUID
from ecs_ec.observability.context import Context

_ACTIVE = ContextVar("costs_technical_execution", default=None)


def progress(stage, *, failed=False):
    """Report a completed actual stage; remember durable engine failure without exporting its data."""
    active = _ACTIVE.get()
    if active is None:
        return
    if failed:
        active["outcome"], active["code"] = "unexpected_error", "processing_interrupted"
    try:
        if active["emitter"]:
            active["emitter"].stage(
                active["handle"],
                stage,
                outcome="unexpected_error" if failed else "success",
                code="processing_interrupted" if failed else "ok",
            )
    except Exception:
        pass


def result_state(data):
    """Classify a returned calculation only; HTTP201 can contain a committed functional failure."""
    active = _ACTIVE.get()
    if active is not None and data.get("execution_state") == "fallido":
        active["outcome"], active["code"] = "unexpected_error", "calculation_failed"


def observe(operation):
    """Wrap one actual HTTP operation, preserving FastAPI's signature and original errors/response."""

    def decorate(function):
        """Build a nonblocking wrapper without copying or recording request arguments."""

        @wraps(function)
        async def wrapped(request, *args, **kwargs):
            """Close after the route returns; nested internal reuse cannot count the request twice."""
            if _ACTIVE.get() is not None:
                return await function(request, *args, **kwargs)
            emitter = getattr(request.app.state, "telemetry", None)
            active = {
                "emitter": emitter,
                "handle": None,
                "outcome": "success",
                "code": "ok",
            }
            try:
                reference = getattr(request.state, "operation_ref", None)
                context = (
                    Context(operation_ref=reference, context_status="available")
                    if type(reference) is UUID
                    else None
                )
                if emitter:
                    active["handle"] = emitter.begin(
                        operation, "costs", context=context
                    )
            except Exception:
                pass
            token = _ACTIVE.set(active)
            try:
                progress("authorize")
                result = await function(request, *args, **kwargs)
                if request.method == "GET":
                    progress("read")
                return result
            except Exception as error:
                status = getattr(error, "status", 503)
                active["outcome"] = (
                    "expected_rejection" if status < 500 else "unexpected_error"
                )
                active["code"] = (
                    "permission_denied"
                    if status in {401, 403}
                    else "invalid_input"
                    if status < 500
                    else "processing_interrupted"
                )
                raise
            finally:
                _ACTIVE.reset(token)
                try:
                    if emitter:
                        emitter.complete(
                            active["handle"],
                            outcome=active["outcome"],
                            code=active["code"],
                        )
                except Exception:
                    pass

        return wrapped

    return decorate
