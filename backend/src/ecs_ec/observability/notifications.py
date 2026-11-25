"""008 emits closed007 technical signals with opaque references only; no rule/input/email/body reaches this adapter."""

from functools import wraps
from uuid import uuid4

from ecs_ec.observability.context import Context


def observe(operation, event="notification.operation.completed"):
    """Complete one actual internal operation; technical admission/export failures never alter its result."""

    def decorate(function):
        """Preserve the original method/signature and observe only fixed catalog selections."""

        @wraps(function)
        async def wrapped(self, *args, **kwargs):
            """Never copy arguments or stringify failures into technical evidence."""
            service = getattr(self, "service", self)
            emitter = getattr(service, "telemetry", None)
            handle = None
            outcome = "success"
            code = "ok"
            try:
                if emitter:
                    handle = emitter.begin(operation, "notifications")
            except Exception:
                pass
            try:
                return await function(self, *args, **kwargs)
            except Exception:
                outcome, code = "unexpected_error", "processing_interrupted"
                raise
            finally:
                try:
                    if emitter:
                        emitter.complete(
                            handle, outcome=outcome, code=code, event=event
                        )
                except Exception:
                    pass

        return wrapped

    return decorate


def begin_attempt(service, claim):
    """Durable IDs establish a new span/execution for this attempt; they grant no functional access."""
    try:
        emitter = getattr(service, "telemetry", None)
        if emitter:
            return emitter.begin(
                "notification.smtp",
                "notifications",
                context=Context(
                    operation_ref=claim["delivery_id"],
                    attempt_ref=claim["attempt_id"],
                    execution_ref=uuid4(),
                    publication_ref=claim.get("occurrence_id"),
                    parent_operation_ref=claim.get("parent_delivery_id"),
                    context_status="available",
                ),
            )
    except Exception:
        pass
    return None


def complete_attempt(service, handle, result):
    """Record actual SMTP acceptance classification once, independently from database-result retries."""
    selected = {
        "aceptada": ("success", "smtp_accepted"),
        "no_aceptada_transitoria": ("expected_rejection", "smtp_transient_rejection"),
        "no_aceptada_definitiva": ("expected_rejection", "smtp_permanent_rejection"),
        "indeterminada": ("unexpected_error", "smtp_confirmation_unknown"),
    }
    outcome, code = selected[result.outcome]
    try:
        emitter = getattr(service, "telemetry", None)
        if emitter:
            emitter.complete(
                handle,
                outcome=outcome,
                code=code,
                event="notification.delivery.attempt.completed",
            )
    except Exception:
        pass
