"""Read-only shared administrative evidence with stable actor references, cutoffs and no secrets."""


async def test_history_allowed_denied_and_unauthenticated(client, login, account_factory, identity_settings, clock):
    """Real changes and early denials appear in the same audit009 source, with server-trusted actors."""
    admin = await account_factory(role="administrador_tecnico")
    session = (await login(admin.email)).json()
    created = await client.post("/api/v1/identity/accounts", json={"email": "history@example.test", "role": "operador", "status": "active", "initial_password": "Synthetic initial password"},
        headers={"Origin": identity_settings.origin, "X-CSRF-Token": session["csrf_token"]})
    assert created.status_code == 201
    operator = await account_factory()
    assert (await login(operator.email)).status_code == 200
    assert (await client.get("/api/v1/identity/accounts")).status_code == 403
    assert (await client.get("/api/v1/identity/administration-history")).status_code == 403
    client.cookies.clear()
    assert (await client.get("/api/v1/identity/accounts")).status_code == 401
    assert (await login(admin.email)).status_code == 200
    clock.advance(1)
    response = await client.get("/api/v1/identity/administration-history", params={"limit": 1})
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["next_cursor"]
    items = list(first["items"])
    cursor = first["next_cursor"]
    while cursor:
        page = (await client.get("/api/v1/identity/administration-history", params={"limit": 1, "cursor": cursor})).json()
        assert page["cutoff_at"] == first["cutoff_at"]
        items.extend(page["items"])
        cursor = page["next_cursor"]
    assert {entry["actor"]["kind"] for entry in items} == {"account", "unauthenticated"}
    assert {entry["result"] for entry in items} >= {"allowed", "denied"}
    assert len({entry["id"] for entry in items}) == len(items)
    assert "Synthetic initial password" not in response.text
    assert all(set(entry) == {"id", "occurred_at", "actor", "action", "target", "result", "reason_code", "operation_ref"} for entry in items)
    tampered = await client.get("/api/v1/identity/administration-history", params={"cursor": first["next_cursor"], "result": "denied"})
    assert tampered.status_code == 422


async def test_history_range_cursor_and_permissions(client, login, account_factory):
    """Unauthorized callers cannot probe filters; invalid/reversed ranges and cursors fail safely."""
    assert (await client.get("/api/v1/identity/administration-history", params={"limit": 0})).status_code == 401
    admin = await account_factory(role="administrador_tecnico")
    assert (await login(admin.email)).status_code == 200
    for params in ({"limit": 101}, {"cursor": "invalid"}, {"from": "2026-02-01T00:00:00Z", "to": "2026-01-01T00:00:00Z"}, {"from": "2026-01-01"}, {"result": "unknown"}):
        response = await client.get("/api/v1/identity/administration-history", params=params)
        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
