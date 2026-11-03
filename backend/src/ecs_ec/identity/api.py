"""Same-origin identity API and security middleware; authorization precedes body/object validation."""

import re
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request as StarletteRequest

from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.permissions import permissions
from ecs_ec.identity.schemas import AccountCreate, AccountIdentity, AccountPage, AccountReset, AccountUpdate, AccountView, HistoryPage, LoginInput, PasswordInput, ProblemView, Role, SessionView, Status
from ecs_ec.identity.security import check_preauth, csrf, preauth_context, request_context, verify_csrf, verify_origin

router = APIRouter(prefix="/api/v1", responses={status: {"model": ProblemView} for status in (401, 403, 404, 409, 412, 422, 428, 429, 503)})


def route_action(method, path):
    """Classify installed identity and consumption routes; policy is explicit rather than a verb-based grant."""
    if path.startswith("/api/v1/costs/"):
        if path in {"/api/v1/costs/supply", "/api/v1/costs/profiles"}:
            return "costs.configuration.read" if method == "GET" else "costs.configuration.manage"
        if method == "GET":
            return "costs.read"
        if path == "/api/v1/costs/calculations":
            return "costs.calculations.create"
        if path == "/api/v1/costs/comparisons":
            return "costs.comparisons.create"
        return "costs.bills.manage"
    if path == "/api/v1/consumption/configuration":
        return "consumption.configuration.read" if method == "GET" else "consumption.configuration.manage"
    if path.startswith("/api/v1/consumption/"):
        return "consumption.read"
    if path.startswith("/api/v1/identity/accounts"):
        return "identity.accounts.read" if method == "GET" else "identity.accounts.manage"
    if path == "/api/v1/identity/administration-history":
        return "administration.history.read"
    return {"/api/v1/auth/session": "session.read", "/api/v1/auth/logout": "session.logout",
            "/api/v1/auth/password": "account.password.change"}.get(path)


def target_reference(path):
    """Parse an account UUID for safe audit metadata, without reflecting raw URL fragments."""
    match = re.fullmatch(r"/api/v1/identity/accounts/([0-9a-fA-F-]{36})(?:/password-reset)?", path)
    try:
        return UUID(match[1]) if match else None
    except ValueError:
        return None


def set_context_cookie(response, name, bearer, seconds, settings):
    """Issue host-only HttpOnly/Lax cookie, Secure under HTTPS and bounded by context lifetime."""
    response.set_cookie(name, bearer, max_age=max(0, int(seconds)), httponly=True, samesite="lax", path="/",
                        secure=settings.origin.startswith("https://"))


def erase_cookie(response, name, settings):
    """Delete a context cookie with the same scope/transport attributes used at issuance."""
    response.delete_cookie(name, path="/", httponly=True, samesite="lax", secure=settings.origin.startswith("https://"))


def session_view(identity, principal, bearer):
    """Project current self identity, approved actions and in-memory CSRF without any bearer/digest."""
    return SessionView(account=AccountIdentity(id=principal.account_id, email=principal.email, role=principal.role),
        session_state=principal.mode, must_change_password=principal.mode == "password_change_required",
        absolute_expires_at=principal.absolute_expires_at, idle_expires_at=principal.idle_expires_at,
        csrf_token=csrf(identity.settings, "session", bearer), permissions=sorted(permissions(principal)))


async def problem_response(request, problem):
    """Audit administrative denials once after rollback; if persistence fails return safe 503, never claim durability."""
    identity = request.app.state.identity
    problem.operation_ref = getattr(request.state, "operation_ref", problem.operation_ref)
    from ecs_ec.identity.permissions import ADMIN
    action = getattr(request.state, "identity_action", None) or route_action(request.method, request.url.path)
    if action in ADMIN and not problem.audited:
        principal = None
        try:
            if problem.code != "https_required":
                principal = await identity.resolve_session(request.cookies.get("ecs_ec_session"))
        except IdentityProblem:
            pass
        except SQLAlchemyError:
            unavailable = IdentityProblem("identity_unavailable", 503, operation_ref=problem.operation_ref)
            return JSONResponse(status_code=503, content=unavailable.body(), headers={"Cache-Control": "no-store"})
        try:
            await identity.rejection(actor=principal, action=action, target_id=target_reference(request.url.path),
                                     problem=problem, operation_ref=problem.operation_ref)
        except Exception:
            problem = IdentityProblem("identity_unavailable", 503, operation_ref=problem.operation_ref)
    response = JSONResponse(status_code=problem.status, content=problem.body(), headers={"Cache-Control": "no-store"})
    if problem.retry_after is not None:
        response.headers["Retry-After"] = str(problem.retry_after)
    if problem.status == 401:
        erase_cookie(response, "ecs_ec_session", identity.settings)
    return response


async def validation_response(request, error: RequestValidationError):
    """Return field paths/codes only; Pydantic input/context/message can contain submitted secrets."""
    names = {"body", "query", "path", "email", "password", "current_password", "new_password", "initial_password",
             "role", "status", "account_id", "limit", "cursor", "from", "to", "action", "result", "actor_id", "target_id"}
    fields = [{"path": ".".join(str(part) for part in item["loc"] if part in names) or "request",
               "code": "invalid", "message": "Revise este campo."} for item in error.errors()]
    return await problem_response(request, IdentityProblem("invalid_input", 422, field_errors=fields))


class IdentityMiddleware:
    """Validate transport/origin/CSRF and account policy before FastAPI parses private request bodies."""

    def __init__(self, app, identity):
        """Bind the installed identity service; no remote identity, consumers or technical auth."""
        self.app, self.identity = app, identity

    async def __call__(self, scope, receive, send):
        """Bind request-local007 instrumentation, never transporting identity in public headers."""
        from ecs_ec.identity.telemetry import emission_scope
        state = scope.setdefault('state', {})
        state['operation_ref'] = uuid4()
        app = scope.get('app')
        emitter = getattr(app.state, 'telemetry', None) if app else None
        with emission_scope(emitter, state['operation_ref']):
            return await self._dispatch(scope, receive, send)

    async def _dispatch(self, scope, receive, send):
        """Process API admission and no-store responses without logging or persisting request values."""
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith("/api/v1/") or path.startswith("/api/v1/health/"):
            return await self.app(scope, receive, send)
        request = StarletteRequest(scope, receive)
        scope.setdefault("state", {}).setdefault("operation_ref", uuid4())
        identity = self.identity

        async def no_store(message):
            """Apply no-store to API successes, framework validation and method/not-found errors alike."""
            if message["type"] == "http.response.start":
                headers = [(key, value) for key, value in message.get("headers", []) if key.lower() != b"cache-control"]
                message["headers"] = headers + [(b"cache-control", b"no-store")]
            await send(message)

        total = 0

        async def bounded_receive():
            """Reject oversized raw bodies before deserializing them; received text is never reflected."""
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > 8192:
                raise IdentityProblem("invalid_input", 422)
            return message

        try:
            action = route_action(request.method, path)
            request.state.identity_action = action
            request.state.origin_ip = request_context(request, identity.settings)
            if action:
                request.state.principal = await identity.resolve_session(request.cookies.get("ecs_ec_session"), action=action)
            mutating = request.method in {"POST", "PUT", "PATCH", "DELETE"}
            verify_origin(request, identity.settings, required=mutating)
            if mutating:
                if path == "/api/v1/auth/login":
                    await check_preauth(identity, request.cookies.get("ecs_ec_preauth"))
                    verify_csrf(identity.settings, "preauth", request.cookies.get("ecs_ec_preauth"), request.headers.get("x-csrf-token"))
                elif action:
                    verify_csrf(identity.settings, "session", request.cookies.get("ecs_ec_session"), request.headers.get("x-csrf-token"))
                if request.method in {"POST", "PUT", "PATCH"} and path != "/api/v1/auth/logout" and request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
                    raise IdentityProblem("invalid_input", 422)
                try:
                    if int(request.headers.get("content-length", "0")) > 8192:
                        raise IdentityProblem("invalid_input", 422)
                except ValueError:
                    raise IdentityProblem("invalid_input", 422) from None
            if action and request.method == "GET" and request.headers.get("x-session-activity") == "interactive":
                request.state.principal = await identity.resolve_session(request.cookies.get("ecs_ec_session"), action=action, activity="interactive")
            await self.app(scope, bounded_receive, no_store)
        except IdentityProblem as problem:
            response = await problem_response(request, problem)
            await response(scope, receive, no_store)
        except SQLAlchemyError:
            response = await problem_response(request, IdentityProblem("identity_unavailable", 503))
            await response(scope, receive, no_store)


@router.get("/auth/csrf")
async def get_csrf(request: Request, response: Response):
    """Create/reuse an unprivileged ten-minute CSRF precontext, never renew a human session."""
    identity = request.app.state.identity
    bearer, expires = await preauth_context(identity, request.cookies.get("ecs_ec_preauth"))
    set_context_cookie(response, "ecs_ec_preauth", bearer, (expires-identity.clock.now()).total_seconds(), identity.settings)
    return {"csrf_token": csrf(identity.settings, "preauth", bearer), "expires_at": expires}


@router.post("/auth/login", response_model=SessionView)
async def sign_in(body: LoginInput, request: Request, response: Response):
    """Consume preauth once, issue independent opaque session and return safe SessionView."""
    identity = request.app.state.identity
    bearer, principal = await identity.login(body.email, body.password.get_secret_value(),
        request.cookies.get("ecs_ec_preauth"), request.state.origin_ip)
    set_context_cookie(response, "ecs_ec_session", bearer, (principal.absolute_expires_at-identity.clock.now()).total_seconds(), identity.settings)
    erase_cookie(response, "ecs_ec_preauth", identity.settings)
    return session_view(identity, principal, bearer)


@router.get("/auth/session", response_model=SessionView)
async def inspect_session(request: Request):
    """Introspect current metadata without extending idle time, even if marked interactive."""
    return session_view(request.app.state.identity, request.state.principal, request.cookies["ecs_ec_session"])


@router.post("/auth/logout", status_code=204)
async def sign_out(request: Request):
    """Revoke the original session and delete its HttpOnly cookie."""
    from ecs_ec.identity.sessions import logout
    identity = request.app.state.identity
    await logout(identity, request.state.principal)
    response = Response(status_code=204)
    erase_cookie(response, "ecs_ec_session", identity.settings)
    return response


@router.post("/auth/password", status_code=204)
async def change_password(body: PasswordInput, request: Request):
    """Change only the caller's credential; all devices must authenticate again."""
    identity = request.app.state.identity
    await identity.change_password(request.state.principal, body.current_password.get_secret_value(),
        body.new_password.get_secret_value(), operation_ref=request.state.operation_ref)
    response = Response(status_code=204)
    erase_cookie(response, "ecs_ec_session", identity.settings)
    return response


def etag(account_id, revision):
    """Generate the strong account revision tag; it is not an authentication credential."""
    return f'"identity:{account_id}:{revision}"'


def expected_revision(value, account_id):
    """Require one exact strong tag; reject wildcard/weak/list syntax before the locked comparison."""
    if value is None:
        raise IdentityProblem("revision_required", 428)
    match = re.fullmatch(r'"identity:([0-9a-f-]{36}):([1-9][0-9]{0,18})"', value)
    if not match or match[1] != str(account_id) or int(match[2]) > 9223372036854775807:
        raise IdentityProblem("invalid_input", 422)
    return int(match[2])


@router.get("/identity/accounts", response_model=AccountPage)
async def list_accounts(request: Request, role: Role | None = None, status: Status | None = None,
                        cursor: str | None = Query(default=None, max_length=4096), limit: int = Query(default=25, ge=1, le=100)):
    """List current accounts only for a normal administrator, never accept permissions from query/body."""
    return await request.app.state.identity.list_accounts(request.state.principal, role=role, status=status, cursor=cursor, limit=limit)


@router.post("/identity/accounts", response_model=AccountView, status_code=201)
async def create_account(body: AccountCreate, request: Request, response: Response):
    """Create an account with mandatory renewal, returning Location/ETag and no credential."""
    row = await request.app.state.identity.create_account(request.state.principal, body, operation_ref=request.state.operation_ref)
    response.headers["ETag"] = etag(row.id, row.revision)
    response.headers["Location"] = "/api/v1/identity/accounts/"+str(row.id)
    return AccountView.model_validate(row)


@router.get("/identity/accounts/{account_id}", response_model=AccountView)
async def get_account(account_id: UUID, request: Request, response: Response):
    """Resolve the object only after the middleware has authenticated and authorized an administrator."""
    row = await request.app.state.identity.get_account(request.state.principal, account_id)
    response.headers["ETag"] = etag(row.id, row.revision)
    return row


@router.put("/identity/accounts/{account_id}", response_model=AccountView)
async def update_account(account_id: UUID, body: AccountUpdate, request: Request, response: Response,
                         if_match: str | None = Header(default=None)):
    """Replace editable attributes with locked revision/session checks; own effective edits delete the cookie."""
    identity = request.app.state.identity
    principal = request.state.principal
    row = await identity.update_account(principal, account_id, body, expected_revision(if_match, account_id), operation_ref=request.state.operation_ref)
    response.headers["ETag"] = etag(row.id, row.revision)
    if row.id == principal.account_id and row.auth_version != principal.auth_version:
        erase_cookie(response, "ecs_ec_session", identity.settings)
    return AccountView.model_validate(row)


@router.post("/identity/accounts/{account_id}/password-reset", response_model=AccountView)
async def reset_account(account_id: UUID, body: AccountReset, request: Request, response: Response,
                        if_match: str | None = Header(default=None)):
    """Reset another account without revealing its previous credential; require a fresh ETag."""
    row = await request.app.state.identity.reset_account(request.state.principal, account_id,
        body.new_password.get_secret_value(), expected_revision(if_match, account_id), operation_ref=request.state.operation_ref)
    response.headers["ETag"] = etag(row.id, row.revision)
    return AccountView.model_validate(row)


@router.get("/identity/administration-history", response_model=HistoryPage)
async def administration_history(request: Request, start: str | None = Query(default=None, alias="from"),
    end: str | None = Query(default=None, alias="to"), action: str | None = None,
    result: Literal["allowed", "denied", "rejected"] | None = None, actor_id: UUID | None = None,
    target_id: UUID | None = None, cursor: str | None = Query(default=None, max_length=4096),
    limit: int = Query(default=25, ge=1, le=100)):
    """Read fixed-cutoff administrative history from audit009; no edit/delete or original-payload response."""
    from ecs_ec.identity.history import read_history
    return await read_history(request.app.state.identity, request.state.principal, start=start, end=end,
        action=action, result=result, actor_id=actor_id, target_id=target_id, cursor=cursor, limit=limit)
