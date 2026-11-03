"""001 instrumentation adapter; no request values or business evidence enter technical signals.

Only catalog, detail and configuration belong here. Reception, aggregates and retention
are instrumented by002. Failures of this best-effort adapter cannot affect the route.
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
            emitter = getattr(request.app.state, 'telemetry', None)
            handle = None
            try:
                reference = getattr(request.state, 'operation_ref', None)
                context = Context(operation_ref=reference, context_status='available') if type(reference) is UUID else None
                if emitter:
                    handle = emitter.begin(operation, 'consumption', context=context)
            except Exception:
                pass
            outcome, code = 'success', 'ok'
            try:
                result = await function(request, *args, **kwargs)
                return result
            except Exception as error:
                status = getattr(error, 'status', 503)
                outcome = 'expected_rejection' if status < 500 else 'unexpected_error'
                code = 'permission_denied' if status in (401, 403) else 'invalid_input' if status < 500 else 'database_unavailable'
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
