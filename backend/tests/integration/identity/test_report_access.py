"""006 access matrix uses actual005 capture, worker, binary and current identity versions."""

import pytest
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.models import Account
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("role", ["operador", "administrador_tecnico"])
@pytest.mark.parametrize("revocation", ["logout", "inactive", "version"])
async def test_pdf_read_permission_and_current_replay_authorization(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    role,
    revocation,
):
    """PDF POST is a read permission with CSRF; revocation denies status, bytes and the exact idempotent replay."""
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings, role
    )
    body = {"scale": "anual", "year": 2024}
    assert (
        await client.post(
            "/api/v1/reports", json=body, headers={"Origin": identity_settings.origin}
        )
    ).status_code == 403
    request = await client.post("/api/v1/reports", json=body, headers=headers)
    assert request.status_code == 202, request.text
    identifier = request.json()["id"]
    result = await terminal(client, identifier)
    assert result["state"] == "generado"
    assert (await client.get(result["download_path"])).content.startswith(b"%PDF-")
    assert (
        await client.post("/api/v1/reports", json=body, headers=headers)
    ).json() == request.json()
    if revocation == "logout":
        assert (
            await client.post("/api/v1/auth/logout", headers=headers)
        ).status_code == 204
    else:
        current = (await client.get("/api/v1/auth/session")).json()["account"]["id"]
        from uuid import UUID

        # Identity ownership changes are injected privately, never through a fixture HTTP route.
        async with UnitOfWork(costs_environment["database"].sessions) as uow:
            row = await uow.session.get(Account, UUID(current))
            if revocation == "inactive":
                # Keep the database's last-active-administrator invariant valid.
                if role == "administrador_tecnico":
                    await account_factory(role=role)
                row.status = "inactive"
            row.auth_version += 1
            row.revision += 1
            await uow.commit()
    responses = [
        await client.get("/api/v1/reports/" + identifier),
        await client.get(result["download_path"]),
        await client.post("/api/v1/reports", json=body, headers=headers),
    ]
    for response in responses:
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
        assert not response.content.startswith(b"%PDF-")
        assert (
            not {"filename", "sha256", "snapshot", "download_path"}
            & response.json().keys()
        )


async def test_repeatable_read_rechecks_stale_principal_before_replay(costs_client, costs_environment, account_factory, session_factory):
    """A005 RR transaction cannot replay under a principal captured before006's current auth version."""
    from uuid import UUID
    from ecs_ec.reports.schemas import Selection
    from ecs_ec.identity.errors import IdentityProblem
    account = await account_factory()
    _, principal = await session_factory(account)
    from dataclasses import replace
    principal = replace(principal, building_id=UUID(int=99))
    service = costs_client._transport.app.state.reports
    selection = Selection(scale='anual', year=2024)
    first = await service.admit(principal, selection, 'stale-principal-fixture')
    assert first['state'] == 'pendiente'
    async with UnitOfWork(costs_environment['database'].sessions) as uow:
        row = await uow.session.get(Account, account.id)
        row.auth_version += 1
        row.revision += 1
        await uow.commit()
    with pytest.raises(IdentityProblem) as failure:
        await service._admit_locked(principal, selection, 'stale-principal-fixture', UUID(int=99))
    assert failure.value.status == 401
