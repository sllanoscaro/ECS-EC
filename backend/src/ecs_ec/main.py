"""Single FastAPI/Uvicorn composition root for API and exported Next assets."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ecs_ec.core.clock import Clock, SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.errors import PlatformError
from ecs_ec.core.lifecycle import Module, application_lifespan, require_schema
from ecs_ec.core.settings import Settings


def create_app(
    settings: Settings | None = None,
    modules: tuple[Module, ...] = (),
    clock: Clock | None = None,
    identity_service=None,
    consumption_bindings=None,
) -> FastAPI:
    """Compose installed modules explicitly; injected settings/clock are internal test seams.

    Startup fails if DB, migrations or export are missing. No credentials, business data,
    SMTP or telemetry are needed in the public export or health responses. Trusted
    consumption_bindings map internal process references to authorized building UUIDs;
    the recovery job uses the same in-process lifecycle and never runs from GET.
    """
    settings = settings or Settings()
    if len({module.name for module in modules}) != len(modules):
        raise ValueError("Module names must be unique")
    database = identity_service.database if identity_service else Database(settings.database_url.get_secret_value())
    clock = clock or SystemClock()
    from ecs_ec.observability.lifecycle import observability_module
    modules = modules + (observability_module(clock),)
    from ecs_ec.acquisition.lifecycle import acquisition_module
    modules = modules + (acquisition_module(clock),)
    if settings.identity_enabled or identity_service:
        from ecs_ec.identity.services import Identity
        identity_service = identity_service or Identity(database, settings.identity_options(), clock, settings.building_timezone, history_actions=("consumption.configuration.changed",))
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def identity_lifespan(app):
            """Prepare verification/rotation checks and supervise bounded technical cleanup in this process."""
            import asyncio
            from contextlib import suppress
            from ecs_ec.identity.maintenance import maintenance_loop, validate_rotation
            await validate_rotation(identity_service)
            await identity_service.credentials.prepare()
            job = asyncio.create_task(maintenance_loop(identity_service, app), name="identity-maintenance")
            try:
                yield
            finally:
                job.cancel()
                with suppress(asyncio.CancelledError):
                    await job

        modules = modules + (Module("identity", lifespan=identity_lifespan),)
    from ecs_ec.consumption.pending_totals import PendingTotals
    from ecs_ec.consumption.reception import Reception
    from ecs_ec.consumption.store import MeasurementStore
    pending_totals = PendingTotals(database, clock)
    modules = modules + (Module("consumption-history", lifespan=pending_totals.lifespan),)
    app = FastAPI(title="ECS-EC", lifespan=application_lifespan(database, modules))
    app.state.settings = settings
    app.state.database = database
    app.state.clock = clock
    #003 supplies explicit trusted process→building bindings at composition time. The
    #default empty map grants no reception capability; no public ingestion route exists.
    app.state.consumption_store = MeasurementStore()
    app.state.consumption_reception = Reception(database, clock, authorized_processes=consumption_bindings or {})
    app.state.consumption_pending_totals = pending_totals
    if identity_service:
        from fastapi.exceptions import RequestValidationError
        from ecs_ec.identity.api import IdentityMiddleware, router, problem_response, validation_response
        from ecs_ec.identity.errors import IdentityProblem
        from ecs_ec.consumption.queries import Consumption, FunctionalSummary
        from ecs_ec.consumption.router import router as consumption_router, ConsumptionProblem, problem_response as consumption_problem
        app.state.consumption = Consumption(database, clock, identity_service.settings.building_id, app.state.consumption_store)
        app.state.consumption_summary = FunctionalSummary(app.state.consumption)
        app.add_exception_handler(ConsumptionProblem, consumption_problem)
        app.include_router(consumption_router)
        identity_service.history_actions = identity_service.history_actions | {"consumption.configuration.changed"}
        from ecs_ec.costs.services import Costs
        from ecs_ec.costs.api import router as costs_router, problem_response as costs_problem
        from ecs_ec.costs.repository import CostsProblem
        app.state.costs = Costs(database, clock, identity_service, app.state.consumption)
        app.add_exception_handler(CostsProblem, costs_problem)
        app.include_router(costs_router)
        identity_service.history_actions = identity_service.history_actions | {
            "costs.supply.changed", "costs.profile.created", "costs.calculation.created", "costs.bill.created", "costs.comparison.created"}
        app.state.identity = identity_service
        app.add_middleware(IdentityMiddleware, identity=identity_service)
        app.add_exception_handler(IdentityProblem, problem_response)
        app.add_exception_handler(RequestValidationError, validation_response)
        app.include_router(router)
        from ecs_ec.identity.openapi import install_openapi
        install_openapi(app)

    @app.exception_handler(PlatformError)
    async def platform_error(request, error: PlatformError):
        """Expose only the fixed safe code/message; never stringify a database exception."""
        return JSONResponse(status_code=503, content={"code": error.code, "message": error.message})

    @app.get("/api/v1/health/live", include_in_schema=False)
    async def live():
        """Report process responsiveness without claiming functional readiness."""
        return {"status": "alive"}

    @app.get("/api/v1/health/ready", include_in_schema=False)
    async def ready():
        """Recheck PostgreSQL/revision/export so a dependency failure returns 503."""
        await require_schema(database)
        if not (settings.web_directory / "index.html").is_file():
            raise PlatformError()
        return {"status": "ready"}

    for module in modules:
        if module.router:
            app.include_router(module.router)
    # Register API first: a static 404 must never mask installed API routes.
    app.mount("/", StaticFiles(directory=settings.web_directory, html=True, check_dir=False), name="web")
    return app
