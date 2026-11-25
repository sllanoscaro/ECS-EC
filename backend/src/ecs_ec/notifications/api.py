"""008 authenticated same-origin API;006 authorization precedes body/object parsing and no-store applies throughout."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from ecs_ec.core.security import require_action
from ecs_ec.notifications.catalog import catalog
from ecs_ec.notifications.repository import NotificationProblem
from ecs_ec.notifications.schemas import RuleInput, validate

router = APIRouter(prefix="/api/v1/notifications")
admin = require_action("notifications.rules.manage")


async def problem_response(request, error):
    """Serialize fixed functional reasons, never raw exception/SQL/SMTP inputs."""
    return JSONResponse(
        status_code=error.status,
        headers={"Cache-Control": "no-store"},
        content=dict(
            code=error.code,
            detail="No se pudo completar la operación de notificaciones. Revise los campos o vuelva a intentarlo.",
            operation_ref=str(getattr(request.state, "operation_ref", "")),
            field_errors=error.field_errors,
        ),
    )


def response(data, status=200):
    """Return protected JSON with explicit ETag for rules and zero cache lifetime."""
    headers = {"Cache-Control": "no-store"}
    if isinstance(data, dict) and "revision" in data:
        headers["ETag"] = '"' + str(data["revision"]) + '"'
    return JSONResponse(data, status_code=status, headers=headers)


async def invoke(awaitable, status=200):
    """Translate infrastructure failures to a fixed503 while preserving typed functional conflicts."""
    try:
        return response(await awaitable, status)
    except SQLAlchemyError:
        raise NotificationProblem("notifications_unavailable", 503) from None


@router.get("/catalog")
async def get_catalog(request: Request, principal=Depends(admin)):
    """Publish the fixed functional vocabulary only to current rule administrators."""
    return response(catalog())


@router.get("/recipients")
async def recipients(
    request: Request,
    principal=Depends(admin),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
    content_types: list[str] | None = Query(None),
):
    """List registered active accounts with current content eligibility, never accept free email addresses."""
    return await invoke(
        request.app.state.notifications.recipients(
            principal, limit, cursor, content_types
        )
    )


@router.post("/rules/preview")
async def preview(request: Request, body: RuleInput, principal=Depends(admin)):
    """Validate configuration/recipient context and return an expiring no-send preview."""
    return await invoke(request.app.state.notifications.preview(principal, body.root))


@router.get("/rules")
async def rules(
    request: Request,
    principal=Depends(admin),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
    status: str | None = None,
):
    """Page stable current rule heads after fresh006 authorization."""
    return await invoke(
        request.app.state.notifications.rules(principal, limit, cursor, status)
    )


@router.post("/rules", status_code=201)
async def create(
    request: Request,
    body: RuleInput,
    principal=Depends(admin),
    idempotency_key: str | None = Header(None),
):
    """Create one inactive rule/version with durable reference-only idempotency and audit."""
    return await invoke(
        request.app.state.notifications.mutate(
            principal, "created", body.root, idempotency_key
        ),
        201,
    )


@router.get("/rules/{rule_id}")
async def detail(request: Request, rule_id: UUID, principal=Depends(admin)):
    """Return a current authorized administrative projection or404 without foreign metadata."""
    return await invoke(request.app.state.notifications.get_rule(principal, rule_id))


@router.put("/rules/{rule_id}")
async def revise(
    request: Request,
    rule_id: UUID,
    body: RuleInput,
    principal=Depends(admin),
    idempotency_key: str | None = Header(None),
    if_match: str | None = Header(None),
):
    """Append an immutable version and pause/cancel pending work atomically; begun attempts remain."""
    return await invoke(
        request.app.state.notifications.mutate(
            principal,
            "revised",
            body.root,
            idempotency_key,
            identifier=rule_id,
            if_match=if_match,
        )
    )


@router.get("/rules/{rule_id}/versions")
async def versions(
    request: Request,
    rule_id: UUID,
    principal=Depends(admin),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
):
    """Page immutable historical versions using an authenticated filter-bound cursor."""
    return await invoke(
        request.app.state.notifications.versions(principal, rule_id, limit, cursor)
    )


@router.post("/rules/{rule_id}/activate")
async def activate(
    request: Request,
    rule_id: UUID,
    body: dict,
    principal=Depends(admin),
    idempotency_key: str | None = Header(None),
    if_match: str | None = Header(None),
):
    """Require a current preview after idempotent replay resolution; activation is always explicit."""
    try:
        validate("ActivateRequest", body)
    except ValueError:
        raise NotificationProblem("invalid_input") from None
    return await invoke(
        request.app.state.notifications.mutate(
            principal,
            "activated",
            body,
            idempotency_key,
            identifier=rule_id,
            if_match=if_match,
        )
    )


@router.post("/rules/{rule_id}/pause")
async def pause(
    request: Request,
    rule_id: UUID,
    principal=Depends(admin),
    idempotency_key: str | None = Header(None),
    if_match: str | None = Header(None),
):
    """Stop future/pending work with the shared rule→account→delivery protocol."""
    if await request.body():
        raise NotificationProblem("unexpected_body")
    return await invoke(
        request.app.state.notifications.mutate(
            principal,
            "paused",
            {},
            idempotency_key,
            identifier=rule_id,
            if_match=if_match,
        )
    )


@router.get("/deliveries")
async def deliveries(
    request: Request,
    principal=Depends(require_action("notifications.deliveries.read")),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = None,
    start: str | None = Query(None, alias="from"),
    end: str | None = Query(None, alias="to"),
    state: str | None = None,
    rule_id: UUID | None = None,
    recipient_id: UUID | None = None,
):
    """Page current authorized history; operator scope and administrative filters are enforced by server."""
    from ecs_ec.notifications.queries import deliveries as read

    return await invoke(
        read(
            request.app.state.notifications,
            principal,
            limit=limit,
            cursor=cursor,
            start=start,
            end=end,
            state=state,
            rule_id=rule_id,
            recipient_id=recipient_id,
        )
    )


@router.get("/deliveries/{delivery_id}")
async def delivery(
    request: Request,
    delivery_id: UUID,
    principal=Depends(require_action("notifications.deliveries.read")),
):
    """Read one authorized immutable content capture and its real attempt outcomes."""
    from ecs_ec.notifications.queries import delivery_detail

    return await invoke(
        delivery_detail(request.app.state.notifications, principal, delivery_id)
    )


@router.post("/deliveries/{delivery_id}/resends", status_code=201)
async def resend_delivery(
    request: Request,
    delivery_id: UUID,
    body: dict,
    principal=Depends(require_action("notifications.deliveries.resend")),
    idempotency_key: str | None = Header(None),
):
    """Authorize an explicit possible-duplicate decision, linked to immutable original evidence and current permissions."""
    from ecs_ec.notifications.resends import resend

    try:
        validate("ResendRequest", body)
    except ValueError:
        raise NotificationProblem("invalid_input") from None
    return await invoke(
        resend(
            request.app.state.notifications,
            principal,
            delivery_id,
            body,
            idempotency_key,
        ),
        201,
    )
