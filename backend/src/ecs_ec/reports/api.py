"""005 same-origin report API: current006 authorization, CSRF/origin, no-store and exact private bytes."""

from uuid import UUID
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from ecs_ec.core.security import require_action
from ecs_ec.reports.schemas import Selection
from ecs_ec.reports.repository import ReportsProblem

router = APIRouter(prefix="/api/v1/reports")


async def problem_response(request, error):
    """Map trusted report reasons to a fixed safe Problem; never expose renderer/SQL/input exceptions."""
    if request.method == "POST":
        service = request.app.state.reports
        handle = service.signal("begin", "report.generate", "reports")
        outcome = "expected_rejection" if error.status < 500 else "unexpected_error"
        code = "invalid_input" if error.status < 500 else "database_unavailable"
        service.signal("stage", handle, "validate", outcome=outcome, code=code)
        service.signal("release", handle, outcome=outcome, code=code)
    return JSONResponse(
        status_code=error.status,
        headers={"Cache-Control": "no-store"},
        content=dict(
            code=error.code,
            detail="No se pudo completar el reporte. Revise la selección o vuelva a intentarlo.",
            operation_ref=str(getattr(request.state, "operation_ref", "")),
            field_errors=error.field_errors,
        ),
    )


@router.post("", status_code=202)
async def create(
    request: Request,
    body: Selection,
    principal=Depends(require_action("reports.generate")),
    idempotency_key: str | None = Header(default=None),
):
    """Admit exactly one calendar selection and immutable capture; retries reuse their original response."""
    try:
        return JSONResponse(
            await request.app.state.reports.admit(principal, body, idempotency_key),
            status_code=202,
            headers={"Cache-Control": "no-store"},
        )
    except SQLAlchemyError:
        raise ReportsProblem("reports_unavailable", 503) from None


@router.get("/{report_id}")
async def status(
    request: Request, report_id: UUID, principal=Depends(require_action("reports.read"))
):
    """Return scoped metadata only after current permission; no raw snapshot or private binary fields."""
    try:
        return JSONResponse(
            await request.app.state.reports.status(principal, report_id),
            headers={"Cache-Control": "no-store"},
        )
    except SQLAlchemyError:
        raise ReportsProblem("reports_unavailable", 503) from None


@router.get("/{report_id}/download")
async def download(
    request: Request, report_id: UUID, principal=Depends(require_action("reports.read"))
):
    """Download stored bytes repeatedly without regeneration, public URLs or bearer links."""
    try:
        content, filename = await request.app.state.reports.download(
            principal, report_id
        )
    except SQLAlchemyError:
        raise ReportsProblem("reports_unavailable", 503) from None
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
