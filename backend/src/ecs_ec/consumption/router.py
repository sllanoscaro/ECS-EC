"""001 authenticated detail/configuration routes; no public reception or measurement mutation API."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from ecs_ec.consumption.telemetry import observe
from ecs_ec.consumption.catalog_storage import read_revisions
from ecs_ec.consumption.configuration import ConfigurationError, ConfigurationService
from ecs_ec.consumption.models import ConfigurationInput
from ecs_ec.consumption.queries import InvalidSelection
from ecs_ec.consumption.schemas import AggregateResponse, Catalog, Configuration, DetailResult, configuration_view
from ecs_ec.consumption.ports import AggregateSelection, Granularity
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account, Session
from ecs_ec.identity.schemas import Principal, ProblemView

router = APIRouter(prefix='/api/v1/consumption', responses={
    status: {'model': ProblemView} for status in (401, 403, 404, 409, 422, 503)})


class ConsumptionProblem(Exception):
    """Closed functional error code/status; messages never include inputs, SQL or exception text."""

    def __init__(self, code, status):
        """Keep only a trusted domain code and status, with no reflected error context."""
        self.code, self.status = code, status


async def problem_response(request, error):
    """Return safe001 Problem structure and no-store, including configuration dependency failures."""
    return JSONResponse(status_code=error.status, headers={'Cache-Control': 'no-store'}, content={
        'code': error.code, 'detail': 'No se pudo completar la consulta o el cambio. Revise la selección y recargue.',
        'operation_ref': str(request.state.operation_ref), 'field_errors': []})


@router.get('/catalog', response_model=Catalog)
@observe('administration.query', 'read')
async def catalog(request: Request):
    """Read current category states/global period after middleware has checked the current session."""
    try:
        return await request.app.state.consumption.catalog()
    except ValueError:
        raise ConsumptionProblem('consumption_unavailable', 503) from None


@router.get('/categories/{category_id}/detail', response_model=DetailResult)
@observe('consumption.query_detail', 'read')
async def detail(request: Request, category_id: str, start: str, end: str, timezone: str):
    """Return full contained detail; malformed periods are explicit422 and unknown categories404."""
    from ecs_ec.consumption.catalog import CATEGORY_IDS
    if category_id not in CATEGORY_IDS:
        raise ConsumptionProblem('category_not_found', 404)
    try:
        return await request.app.state.consumption.detail(category_id, start, end, timezone)
    except InvalidSelection:
        raise ConsumptionProblem('invalid_period', 422) from None
    except ValueError:
        raise ConsumptionProblem('consumption_unavailable', 503) from None


@router.get('/configuration', response_model=Configuration)
@observe('administration.query', 'read')
async def configuration(request: Request):
    """Read latest immutable administrative revision; do not bootstrap missing configuration."""
    service = request.app.state.consumption
    async with UnitOfWork(service.database.sessions) as uow:
        revisions = await read_revisions(uow, service.building_id)
        if not revisions:
            raise ConsumptionProblem('configuration_missing', 404)
        return configuration_view(revisions[-1])


@router.put('/configuration', response_model=Configuration)
@observe('administration.change', 'commit')
async def configure(request: Request, body: ConfigurationInput):
    """Revalidate actor/session under locks, then commit revision and functional evidence together."""
    service, identity = request.app.state.consumption, request.app.state.identity
    principal = request.state.principal
    try:
        async with UnitOfWork(service.database.sessions) as uow:
            account = await uow.session.scalar(select(Account).where(Account.id == principal.account_id).with_for_update())
            session = await uow.session.scalar(select(Session).where(Session.id == principal.session_id).with_for_update())
            if not identity.session_valid(account, session, identity.clock.now()):
                raise IdentityProblem('session_required', 401)
            current = Principal.from_rows(account, session, identity.settings.building_id)
            identity.authorize(current, 'consumption.configuration.manage', identity.settings.building_id)
            revision = await ConfigurationService(service.clock, service.store).apply(uow,
                building_id=service.building_id, request=body, actor_ref=f'account:{current.account_id}')
            #006 defines successful authorized mutations, including no-ops, as activity.
            from datetime import timedelta
            session.last_activity_at = max(session.last_activity_at, identity.clock.now())
            session.idle_expires_at = min(session.absolute_expires_at, session.last_activity_at + timedelta(minutes=30))
            await uow.commit()
            return configuration_view(revision)
    except ConfigurationError as error:
        status = 503 if error.code in {'reconfiguration_bounds_unavailable', 'building_context_missing'} else 409
        raise ConsumptionProblem(error.code, status) from None


@router.get('/categories/{category_id}/aggregates', response_model=AggregateResponse)
async def aggregates(request: Request, category_id: str, start: str, end: str, timezone: str, granularity: Granularity):
    """Validate exact offset selection and return the002 capture under the current006 read grant."""
    from ecs_ec.consumption.catalog import CATEGORY_IDS
    from ecs_ec.consumption.periods import resolve_period
    if category_id not in CATEGORY_IDS:
        raise ConsumptionProblem('category_not_found', 404)
    service = request.app.state.consumption
    try:
        async with UnitOfWork(service.database.sessions) as uow:
            from sqlalchemy import text
            await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
            building, _ = await service._context(uow)
            try:
                period = resolve_period(start, end, timezone, building.timezone)
                selection = AggregateSelection(building_id=service.building_id, category_id=category_id,
                    start=period.start, end=period.end, timezone=timezone, granularity=granularity)
            except (ValueError, TypeError, OverflowError):
                raise InvalidSelection('invalid_aggregate_selection') from None
            result = await service.query_aggregates(selection, request.state.principal, uow)
            return AggregateResponse.model_validate(result.model_dump())
    except InvalidSelection:
        raise ConsumptionProblem('invalid_aggregate_selection', 422) from None
    except ValueError as error:
        if error.args == ('building_context_missing',):
            raise ConsumptionProblem('building_not_found', 404) from None
        raise ConsumptionProblem('consumption_unavailable', 503) from None
