"""007 shared HTTP observation boundary for installed owner routes, including early denials.

The registry contains fixed operation names only. It grants no permissions, inspects
no body/identity/query and changes no transaction. Owner adapters borrow its handle,
so framework validation and006 denials have one target terminal without double counting.
"""

from contextvars import ContextVar
from dataclasses import dataclass
import re
from uuid import uuid4

_REQUEST = ContextVar("technical_http_observation", default=None)


@dataclass
class Observation:
    """One request-local technical handle; mutable borrow state never escapes the ASGI task."""

    emitter: object
    handle: object
    borrowed: bool = False


def borrow(emitter, operation, source_module):
    """Reuse the boundary handle once for its actual installed owner; unrelated decisions stay separate."""
    active = _REQUEST.get()
    if (
        active
        and not active.borrowed
        and active.emitter is emitter
        and active.handle
        and active.handle.operation == operation
        and active.handle.source_module == source_module
    ):
        active.borrowed = True
        return active.handle
    return None


def target(method, path):
    """Map exact installed HTTP route shapes to the007 catalog; unknown routes remain unobserved."""
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return None
    if re.fullmatch(r'/api/v1/notifications/(?:catalog|recipients|rules(?:/preview|/[0-9a-fA-F-]{36}(?:/versions|/activate|/pause)?)?|deliveries(?:/[0-9a-fA-F-]{36}(?:/resends)?)?)',path):
        return ('notification.query' if method=='GET' else 'notification.configure'),'notifications'
    if re.fullmatch(r"/api/v1/reports(?:/[0-9a-fA-F-]{36}(?:/download)?)?", path):
        if path == "/api/v1/reports" and method == "POST":
            return "report.generate", "reports"
        if method == "GET" and path != "/api/v1/reports":
            return (
                "report.download" if path.endswith("/download") else "report.query"
            ), "reports"
    if re.fullmatch(
        r"/api/v1/costs/(?:readiness|supply|profiles|history|cycles|calculations(?:/[0-9a-fA-F-]{36}(?:/distribution)?)?|bills(?:/[0-9a-fA-F-]{36})?|comparisons(?:/[0-9a-fA-F-]{36})?)",
        path,
    ):
        if method == "GET":
            return "cost.query", "costs"
        if path.endswith("/calculations") and method == "POST":
            return "cost.calculate", "costs"
        if path.endswith("/comparisons") and method == "POST":
            return "cost.compare", "costs"
        if re.fullmatch(
            r"/api/v1/costs/(?:supply|profiles|bills(?:/[0-9a-fA-F-]{36})?)", path
        ):
            return "administration.change", "costs"
    if re.fullmatch(
        r"/api/v1/consumption/(?:catalog|sources|configuration|dashboard|categories/CAT-0[1-7]/(?:detail|aggregates))",
        path,
    ):
        if method == "GET":
            return (
                "consumption.query_aggregates"
                if path.endswith("/aggregates")
                else "consumption.query_detail"
                if path.endswith("/detail") or path.endswith("/dashboard")
                else "administration.query"
            ), "consumption"
        if path.endswith("/configuration"):
            return "administration.change", "consumption"
    if re.fullmatch(
        r"/api/v1/identity/(?:accounts(?:/[0-9a-fA-F-]{36}(?:/password-reset)?)?|administration-history)",
        path,
    ):
        return (
            "administration.query" if method == "GET" else "administration.change"
        ), "identity"
    if method == "POST" and path in {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/password",
    }:
        return (
            "identity.authenticate" if path.endswith("/login") else "identity.session"
        ), "identity"
    return None


class ObservationBoundary:
    """ASGI-only registration around006 admission and owner routing; no public technical API."""

    def __init__(self, app):
        """Receive the inner installed monolith; no service or credentials are created."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Observe the real request once, including framework rejection before an owner adapter runs."""
        route = (
            target(scope.get("method"), scope.get("path", ""))
            if scope["type"] == "http"
            else None
        )
        if route is None:
            return await self.app(scope, receive, send)
        from ecs_ec.observability.context import new_context

        app = scope.get("app")
        emitter = getattr(app.state, "telemetry", None) if app else None
        handle = None
        state = scope.setdefault("state", {})
        state["operation_ref"] = uuid4()
        try:
            if emitter:
                handle = emitter.begin(
                    *route, context=new_context(operation_ref=state["operation_ref"])
                )
        except Exception:
            pass
        active = Observation(emitter, handle)
        token = _REQUEST.set(active)
        status = 500

        async def observed_send(message):
            """Read only the HTTP status; response bodies and headers never enter observation state."""
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            return await self.app(scope, receive, observed_send)
        finally:
            _REQUEST.reset(token)
            try:
                if emitter and handle and not handle.closed:
                    outcome = (
                        "unexpected_error"
                        if status >= 500
                        else "expected_rejection"
                        if status >= 400
                        else "success"
                    )
                    code = (
                        "processing_interrupted"
                        if status >= 500
                        else "permission_denied"
                        if status in {401, 403}
                        else "invalid_input"
                        if status >= 400
                        else "ok"
                    )
                    if route[0] == "report.generate" and (
                        handle.admission_emitted or status < 400
                    ):
                        emitter.release(handle, outcome=outcome, code=code)
                    else:
                        emitter.stage(
                            handle,
                            "authorize"
                            if status in {401, 403}
                            else "validate"
                            if status >= 400
                            else "read",
                            outcome=outcome,
                            code=code,
                        )
                        emitter.complete(handle, outcome=outcome, code=code,event='notification.operation.completed' if route[1]=='notifications' else 'operation.completed')
            except Exception:
                pass
