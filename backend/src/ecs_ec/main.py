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
) -> FastAPI:
    """Compose installed modules explicitly; injected settings/clock are internal test seams.

    Startup fails if DB, migrations or export are missing. No credentials, business data,
    SMTP or telemetry are needed in the public export or health responses.
    """
    settings = settings or Settings()
    if len({module.name for module in modules}) != len(modules):
        raise ValueError("Module names must be unique")
    database = Database(settings.database_url.get_secret_value())
    app = FastAPI(title="ECS-EC", lifespan=application_lifespan(database, modules))
    app.state.settings = settings
    app.state.database = database
    app.state.clock = clock or SystemClock()

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
