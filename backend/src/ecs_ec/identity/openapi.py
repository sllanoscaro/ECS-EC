"""Document manual middleware security explicitly; no authentication secret appears in generated schemas."""

from fastapi.openapi.utils import get_openapi


def install_openapi(app):
    """Publish the installed identity cookie/CSRF requirements alongside typed Problem responses."""
    def schema():
        """Generate once from real routes, then describe middleware-enforced cookie/header contexts."""
        if app.openapi_schema:
            return app.openapi_schema
        document = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schemes = document.setdefault("components", {}).setdefault("securitySchemes", {})
        schemes.update({"SessionCookie": {"type": "apiKey", "in": "cookie", "name": "ecs_ec_session"},
                        "PreauthCookie": {"type": "apiKey", "in": "cookie", "name": "ecs_ec_preauth"},
                        "CsrfToken": {"type": "apiKey", "in": "header", "name": "X-CSRF-Token"}})
        for path, methods in document["paths"].items():
            if not path.startswith(("/api/v1/auth/", "/api/v1/identity/", "/api/v1/consumption/")):
                continue
            for method, operation in methods.items():
                if path == "/api/v1/auth/csrf":
                    operation["security"] = []
                else:
                    requirement = {"PreauthCookie" if path == "/api/v1/auth/login" else "SessionCookie": []}
                    if method in {"post", "put", "patch", "delete"}:
                        requirement["CsrfToken"] = []
                    operation["security"] = [requirement]
        app.openapi_schema = document
        return document
    app.openapi = schema
