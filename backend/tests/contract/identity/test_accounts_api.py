"""Account administration: live admin permission, exact DTOs, ETags and absence of credential disclosure."""

from uuid import uuid4


async def test_accounts_create_edit_and_conflicts(client, login, account_factory, identity_settings):
    """Admin creates and revises through real endpoints; duplicates/stale writes leave known state intact."""
    admin = await account_factory(role="administrador_tecnico")
    session = (await login(admin.email)).json()
    headers = {"Origin": identity_settings.origin, "X-CSRF-Token": session["csrf_token"]}
    body = {"email": "new@example.test", "role": "operador", "status": "active", "initial_password": "Synthetic initial password"}
    created = await client.post("/api/v1/identity/accounts", json=body, headers=headers)
    assert created.status_code == 201, created.text
    account = created.json()
    assert set(account) == {"id", "email", "role", "status", "must_change_password", "revision", "created_at", "updated_at"}
    assert account["must_change_password"] is True
    assert created.headers["etag"] == f'"identity:{account["id"]}:1"'
    assert (await client.post("/api/v1/identity/accounts", json=body | {"email": " NEW@EXAMPLE.TEST "}, headers=headers)).status_code == 409
    path = "/api/v1/identity/accounts/"+account["id"]
    editable = {key: account[key] for key in ("email", "role", "status")}
    assert (await client.put(path, json=editable, headers=headers)).status_code == 428
    unchanged = await client.put(path, json=editable, headers=headers | {"If-Match": created.headers["etag"]})
    assert unchanged.status_code == 200 and unchanged.json()["revision"] == 1
    changed = await client.put(path, json=editable | {"status": "inactive"}, headers=headers | {"If-Match": created.headers["etag"]})
    assert changed.status_code == 200 and changed.json()["revision"] == 2
    assert (await client.put(path, json=editable, headers=headers | {"If-Match": created.headers["etag"]})).status_code == 412
    assert (await client.get(path)).json()["status"] == "inactive"


async def test_no_admin_object_disclosure(client, login, account_factory):
    """Operator/anonymous denial precedes object UUID/query/body validation and existence checks."""
    assert (await client.get("/api/v1/identity/accounts/not-a-uuid")).status_code == 401
    operator = await account_factory()
    assert (await login(operator.email)).status_code == 200
    for path in ("/api/v1/identity/accounts", "/api/v1/identity/accounts/not-a-uuid", "/api/v1/identity/accounts/"+str(uuid4())):
        response = await client.get(path, headers={"X-Role": "administrador_tecnico"})
        assert response.status_code == 403
        assert "password_hash" not in response.text
