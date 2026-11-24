"""HTTP security dependencies exercise fixed actions without inventing missing business endpoints."""

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from ecs_ec.core.security import require_action
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.permissions import ACTIONS, BASIC, READ
from ecs_ec.identity.security import csrf


@pytest.mark.parametrize("role", ["operador", "administrador_tecnico"])
@pytest.mark.parametrize("renewal", [False, True])
async def test_real_request_policy(
    identity, account_factory, session_factory, role, renewal
):
    """Resolve every action from current PostgreSQL rows, ignoring a forged administrative header."""
    account = await account_factory(role=role, renewal=renewal)
    cookie, principal = await session_factory(account)
    for action in ACTIONS:
        headers = {
            "host": "localhost:8000",
            "cookie": "ecs_ec_session=" + cookie,
            "x-role": "administrador_tecnico",
            "origin": identity.settings.origin,
            "x-csrf-token": csrf(identity.settings, "session", cookie),
        }
        request = Request(
            {
                "type": "http",
                "method": "POST" if action == "reports.generate" else "GET",
                "scheme": "http",
                "server": ("localhost", 8000),
                "client": ("127.0.0.1", 12345),
                "path": "/api/v1/policy-contract",
                "query_string": b"",
                "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
                "app": SimpleNamespace(state=SimpleNamespace(identity=identity)),
            }
        )
        permitted = action in BASIC or (
            not renewal and (action in READ or role == "administrador_tecnico")
        )
        if permitted:
            result = await require_action(action)(request)
            assert result.account_id == account.id
        else:
            with pytest.raises(IdentityProblem) as failure:
                await require_action(action)(request)
            assert failure.value.status == 403


async def test_generated_openapi_and_installed_provider_guards(costs_client):
    """Review the actual composed schema and fixed006 dependencies, including005 POST's read grant."""
    from fastapi.routing import APIRoute, iter_route_contexts
    from ecs_ec.identity.api import route_action

    app = costs_client._transport.app
    schema = app.openapi()
    required = {
        "/api/v1/auth/login": {"post"},
        "/api/v1/auth/session": {"get"},
        "/api/v1/auth/logout": {"post"},
        "/api/v1/auth/password": {"post"},
        "/api/v1/identity/accounts": {"get", "post"},
        "/api/v1/identity/accounts/{account_id}": {"put"},
        "/api/v1/identity/administration-history": {"get"},
    }
    for path, methods in required.items():
        assert methods <= schema["paths"][path].keys()
    for name in ["LoginInput", "PasswordInput", "AccountCreate", "AccountUpdate"]:
        properties = schema["components"]["schemas"][name]["properties"]
        assert (
            not {
                "actor_ref",
                "permissions",
                "auth_version",
                "session_id",
                "operation_ref",
            }
            & properties.keys()
        )
    expected = {
        "/api/v1/consumption/configuration": {
            "consumption.configuration.read",
            "consumption.configuration.manage",
        },
        "/api/v1/costs/supply": {
            "costs.configuration.read",
            "costs.configuration.manage",
        },
        "/api/v1/reports": {"reports.generate"},
        "/api/v1/reports/{report_id}/download": {"reports.read"},
    }
    for path, actions in expected.items():
        registered = set()
        for route in iter_route_contexts(app.routes):
            if isinstance(route.original_route, APIRoute) and route.path == path:
                registered.update(
                    getattr(d.call, "identity_action", None)
                    for d in route.dependant.dependencies
                )
        assert actions <= registered
    assert route_action("POST", "/api/v1/reports") == "reports.generate"
