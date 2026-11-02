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
async def test_real_request_policy(identity, account_factory, session_factory, role, renewal):
    """Resolve every action from current PostgreSQL rows, ignoring a forged administrative header."""
    account = await account_factory(role=role, renewal=renewal)
    cookie, principal = await session_factory(account)
    for action in ACTIONS:
        headers = {"host": "localhost:8000", "cookie": "ecs_ec_session="+cookie,
                   "x-role": "administrador_tecnico", "origin": identity.settings.origin,
                   "x-csrf-token": csrf(identity.settings, "session", cookie)}
        request = Request({"type": "http", "method": "POST" if action == "reports.generate" else "GET",
            "scheme": "http", "server": ("localhost", 8000), "client": ("127.0.0.1", 12345),
            "path": "/api/v1/policy-contract", "query_string": b"", "headers": [(k.encode(),v.encode()) for k,v in headers.items()],
            "app": SimpleNamespace(state=SimpleNamespace(identity=identity))})
        permitted = action in BASIC or (not renewal and (action in READ or role == "administrador_tecnico"))
        if permitted:
            result = await require_action(action)(request)
            assert result.account_id == account.id
        else:
            with pytest.raises(IdentityProblem) as failure:
                await require_action(action)(request)
            assert failure.value.status == 403
