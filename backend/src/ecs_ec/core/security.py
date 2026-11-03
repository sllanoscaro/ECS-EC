"""Installed identity facade for domain route dependencies, owned by spec-006 integration."""

from fastapi import Request

from ecs_ec.identity.errors import IdentityProblem


def require_action(action):
    """Build a fresh authorization dependency; callers register an explicit fixed action."""
    async def authorize(request: Request):
        """Resolve current state in a short UoW before the consumer takes any domain locks."""
        from ecs_ec.identity.security import request_context, verify_origin, verify_csrf
        request.state.identity_action = action
        identity = getattr(request.app.state, "identity", None)
        if identity is None:
            raise IdentityProblem("identity_unavailable", 503)
        request_context(request, identity.settings)
        principal = await identity.resolve_session(request.cookies.get("ecs_ec_session"), action=action)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            verify_origin(request, identity.settings)
            verify_csrf(identity.settings, "session", request.cookies.get("ecs_ec_session"), request.headers.get("x-csrf-token"))
        # A mutation renews activity only after its owning service commits successfully.
        # Admission happens before body validation and must not extend a rejected request.
        activity = request.headers.get("x-session-activity", "background") if request.method == "GET" else "background"
        return await identity.resolve_session(request.cookies.get("ecs_ec_session"), action=action, activity=activity)
    authorize.identity_action = action
    return authorize
