"""Five auth routes enforce transport, CSRF, safe response contracts and restricted renewal."""

import pytest


async def test_login_session_logout(client, login, account_factory, identity_settings):
    """Real cookies authenticate; introspection exposes only SessionView and logout revokes the bearer."""
    account = await account_factory()
    response = await login(account.email)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"account", "session_state", "must_change_password", "absolute_expires_at", "idle_expires_at", "csrf_token", "permissions"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    assert (await client.get("/api/v1/auth/session")).status_code == 200
    failure = await client.post("/api/v1/auth/logout")
    assert failure.status_code == 403
    response = await client.post("/api/v1/auth/logout", headers={"Origin": identity_settings.origin, "X-CSRF-Token": body["csrf_token"]})
    assert response.status_code == 204
    assert (await client.get("/api/v1/auth/session")).status_code == 401


async def test_renewal_revokes_every_session(client, login, account_factory, identity_settings):
    """Restricted login allows only self renewal/logout and requires a new login after changing password."""
    account = await account_factory(renewal=True)
    response = await login(account.email)
    assert response.status_code == 200
    body = response.json()
    assert body["session_state"] == "password_change_required"
    assert set(body["permissions"]) == {"session.read", "session.logout", "account.password.change"}
    assert (await client.get("/api/v1/identity/accounts")).status_code == 403
    changed = await client.post("/api/v1/auth/password", json={"current_password": "Synthetic password 006", "new_password": "New synthetic password 006"},
        headers={"Origin": identity_settings.origin, "X-CSRF-Token": body["csrf_token"]})
    assert changed.status_code == 204, changed.text
    assert (await client.get("/api/v1/auth/session")).status_code == 401
    assert (await login(account.email, "New synthetic password 006")).json()["session_state"] == "normal"


async def test_csrf_origin_and_safe_validation(client, identity_settings):
    """Cross-origin and unbound login fail before credentials; malformed bodies never echo values."""
    context = (await client.get("/api/v1/auth/csrf")).json()
    response = await client.post("/api/v1/auth/login", json={"email": "nobody@example.test", "password": "Synthetic password 006"})
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    response = await client.post("/api/v1/auth/login", json={"email": "nobody@example.test", "password": "Sensitive synthetic value", "role": "administrador_tecnico"},
        headers={"Origin": identity_settings.origin, "X-CSRF-Token": context["csrf_token"]})
    assert response.status_code == 422
    assert "Sensitive synthetic value" not in response.text
    assert set(response.json()) == {"code", "detail", "operation_ref", "field_errors"}
