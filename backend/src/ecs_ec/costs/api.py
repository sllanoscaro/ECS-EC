"""004 same-origin financial API;006 middleware enforces live session, role, origin and CSRF before bodies."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from ecs_ec.core.security import require_action
from ecs_ec.costs.repository import CostsProblem
from ecs_ec.costs.schemas import CalculateRequest, CalculationDetail, SupplyDetail, BillInput, ComparisonRequest, SupplyInput, ProfileInput, BillDetail, ComparisonDetail, ProfileDetail, CyclePage, BillPage, ProfilePage
from ecs_ec.identity.schemas import ProblemView

router = APIRouter(prefix='/api/v1/costs', responses={status: {'model': ProblemView} for status in (401,403,404,409,412,422,428,503)})


async def problem_response(request, problem):
    """Expose only trusted codes and a fixed explanation, never SQL, amounts or engine exception details."""
    return JSONResponse(status_code=problem.status, headers={'Cache-Control': 'no-store'}, content=dict(
        code=problem.code, detail='No se pudo completar la operación de costos. Revise los datos y la revisión actual.',
        operation_ref=str(request.state.operation_ref), field_errors=[]))


def etag(kind, data):
    """Return the strong resource identity/revision tag; it is not a credential or editable field."""
    return f'"costs:{kind}:{data["id"]}:{data["revision"]}"'


def resource_response(data, status, *, kind, location=None):
    """Return persisted response/status with stable ETag and optional resource location."""
    headers = {'Cache-Control': 'no-store', 'ETag': etag(kind, data)}
    if location:
        headers['Location'] = location + '/' + data['id']
    return JSONResponse(content=data, status_code=status, headers=headers)


@router.get('/supply', response_model=SupplyDetail, dependencies=[Depends(require_action('costs.configuration.read'))])
async def supply(request: Request, response: Response):
    """Read administrative supply configuration or404 without creating it."""
    data = await request.app.state.costs.get_supply(request.state.principal)
    response.headers['ETag'] = etag('supply', data)
    return data


@router.post('/calculations', response_model=CalculationDetail, status_code=201, dependencies=[Depends(require_action('costs.calculations.create'))])
async def calculate(request: Request, body: CalculateRequest, idempotency_key: str | None = Header(default=None)):
    """Persist one explicit calculation/recalculation; same authorized key/body replays the original revision."""
    data, status = await request.app.state.costs.calculate(request.state.principal, body, idempotency_key)
    return resource_response(data, status, kind='calculation', location='/api/v1/costs/calculations')


@router.get('/calculations/{calculation_id}', response_model=CalculationDetail)
async def calculation(request: Request, calculation_id: UUID):
    """Read immutable captured calculation evidence through current functional permission."""
    return await request.app.state.costs.get_calculation(request.state.principal, calculation_id)


@router.get('/cycles', response_model=CyclePage)
async def cycles(request: Request, start: str | None = Query(default=None, alias='from'), end: str | None = Query(default=None, alias='to'),
        cutoff_at: str | None = None, limit: int = Query(default=25, ge=1, le=100), cursor: str | None = Query(default=None, max_length=4096)):
    """Read a bounded deterministic cycle page; filters and a fixed cutoff travel in its signed cursor."""
    from ecs_ec.consumption.models import instant
    try:
        lower, upper, cutoff = (instant(value) if value else None for value in (start, end, cutoff_at))
        if lower and upper and lower >= upper:
            raise ValueError('invalid_period')
    except ValueError:
        raise CostsProblem('invalid_period', 422) from None
    return await request.app.state.costs.cycles(request.state.principal, start=lower, end=upper, cutoff_at=cutoff, limit=limit, cursor=cursor)


@router.get('/bills', response_model=BillPage)
async def bills(request: Request, limit: int = Query(default=25, ge=1, le=100), cursor: str | None = Query(default=None, max_length=4096), cycle_id: UUID | None = None):
    """List immutable document revisions for an explicit current or historical comparison selection."""
    return await request.app.state.costs.bills(request.state.principal, limit=limit, cursor=cursor, cycle_id=cycle_id)


@router.get('/bills/{bill_id}', response_model=BillDetail)
async def bill(request: Request, bill_id: UUID, response: Response, revision: int | None = Query(default=None, ge=1)):
    """Read one current/numbered historical document and its strong revision tag."""
    data = await request.app.state.costs.get_bill(request.state.principal, bill_id, revision)
    response.headers['ETag'] = etag('bill', data)
    return data


@router.post('/bills', response_model=BillDetail, status_code=201, dependencies=[Depends(require_action('costs.bills.manage'))])
async def create_bill(request: Request, body: 'BillInput', idempotency_key: str | None = Header(default=None)):
    """Register a manual document; repeated identity/body reuses its immutable resource without changing sources."""
    data, status = await request.app.state.costs.save_bill(request.state.principal, body, idempotency_key)
    return resource_response(data, status, kind='bill', location='/api/v1/costs/bills')


@router.put('/bills/{bill_id}', response_model=BillDetail, dependencies=[Depends(require_action('costs.bills.manage'))])
async def correct_bill(request: Request, bill_id: UUID, body: 'BillInput', idempotency_key: str | None = Header(default=None), if_match: str | None = Header(default=None)):
    """Append an explicit document correction, preserving its previous revision and every comparison of it."""
    data, status = await request.app.state.costs.save_bill(request.state.principal, body, idempotency_key, bill_id=bill_id, if_match=if_match)
    return resource_response(data, status, kind='bill')


@router.post('/comparisons', response_model=ComparisonDetail, status_code=201, dependencies=[Depends(require_action('costs.comparisons.create'))])
async def create_comparison(request: Request, body: 'ComparisonRequest', idempotency_key: str | None = Header(default=None)):
    """Confirm a comparison of explicit immutable references; no read path generates this resource."""
    data, status = await request.app.state.costs.create_comparison(request.state.principal, body, idempotency_key)
    return resource_response(data, status, kind='comparison', location='/api/v1/costs/comparisons')


@router.get('/comparisons/{comparison_id}', response_model=ComparisonDetail)
async def comparison(request: Request, comparison_id: UUID):
    """Read a persisted pair result including signed exclusions and a nullable zero-denominator percentage."""
    return await request.app.state.costs.get_comparison(request.state.principal, comparison_id)


@router.put('/supply', response_model=SupplyDetail, dependencies=[Depends(require_action('costs.configuration.manage'))])
async def configure_supply(request: Request, body: SupplyInput, idempotency_key: str | None = Header(default=None),
        if_match: str | None = Header(default=None), if_none_match: str | None = Header(default=None)):
    """Create/update actual physical-supply configuration with explicit strong revision preconditions."""
    data, status = await request.app.state.costs.put_supply(request.state.principal, body, idempotency_key,
        if_match=if_match, if_none_match=if_none_match)
    return resource_response(data, status, kind='supply')


@router.get('/profiles', response_model=ProfilePage, dependencies=[Depends(require_action('costs.configuration.read'))])
async def profiles(request: Request, limit: int = Query(default=25, ge=1, le=100), cursor: str | None = Query(default=None, max_length=4096)):
    """Read administrative full-calendar revisions, distinguishing saved drafts from the selected publication."""
    return await request.app.state.costs.profiles(request.state.principal, limit=limit, cursor=cursor)


@router.post('/profiles', response_model=ProfileDetail, status_code=201, dependencies=[Depends(require_action('costs.configuration.manage'))])
async def create_profile(request: Request, body: ProfileInput, idempotency_key: str | None = Header(default=None)):
    """Publish/store an immutable full-calendar revision against an explicit latest-saved base."""
    data, status = await request.app.state.costs.create_profile(request.state.principal, body, idempotency_key)
    return resource_response(data, status, kind='profile')


@router.get('/history', response_model=CyclePage)
async def history(request: Request, start: str | None = Query(default=None, alias='from'), end: str | None = Query(default=None, alias='to'),
        cutoff_at: str | None = None, limit: int = Query(default=25, ge=1, le=100), cursor: str | None = Query(default=None, max_length=4096)):
    """Read all retained financial history through the same bounded fixed-cutoff cycle resolver."""
    return await cycles(request, start=start, end=end, cutoff_at=cutoff_at, limit=limit, cursor=cursor)
