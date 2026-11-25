"""008 actual composedAPI plus006 sessions: strict body, preview, immutable revision and original idempotent receipts."""

from uuid import uuid4

import pytest


def config(account_id, **changes):
    """Reference daily06:00 rule uses registered synthetic identity, never a free email."""
    return (
        dict(
            name="Resumen diario",
            timezone="America/Santiago",
            recipient_ids=[str(account_id)],
            mode="periodica",
            content_types=["recepcion"],
            schedule=dict(
                kind="diaria", starts_at="2025-01-01T00:00:00Z", local_time="06:00"
            ),
        )
        | changes
    )


async def authenticated(
    client,
    account_factory,
    session_factory,
    identity_settings,
    role="administrador_tecnico",
):
    """Use a real durable006 session; internalfixture creates credentials without a public bypass."""
    from ecs_ec.identity.security import csrf

    account = await account_factory(role=role)
    bearer, principal = await session_factory(account)
    client.cookies.set("ecs_ec_session", bearer)
    return account, dict(
        Origin=identity_settings.origin,
        **{"X-CSRF-Token": csrf(identity_settings, "session", bearer)},
    )


async def test_rule_full_lifecycle_and_exact_replays(
    client, account_factory, session_factory, identity_settings
):
    """Create→preview→activate→revise→pause uses ETags and replay before stale preconditions; never sends."""
    account, headers = await authenticated(
        client, account_factory, session_factory, identity_settings
    )
    body = config(account.id)
    response = await client.post(
        "/api/v1/notifications/rules",
        json=body,
        headers=headers | {"Idempotency-Key": "create-one"},
    )
    assert response.status_code == 201, response.text
    first = response.json()
    identifier = first["id"]
    assert first["status"] == "desactivada" and response.headers["etag"] == '"1"'
    preview = await client.post(
        "/api/v1/notifications/rules/preview", json=body, headers=headers
    )
    assert preview.status_code == 200, preview.text
    assert len(preview.json()["next_occurrences"]) == 3
    activate_body = {"preview_token": preview.json()["preview_token"]}
    active = await client.post(
        f"/api/v1/notifications/rules/{identifier}/activate",
        json=activate_body,
        headers=headers | {"Idempotency-Key": "activate-one", "If-Match": '"1"'},
    )
    assert active.status_code == 200, active.text
    assert active.json()["revision"] == 2 and active.json()["status"] == "activa"
    replay = await client.post(
        f"/api/v1/notifications/rules/{identifier}/activate",
        json=activate_body,
        headers=headers | {"Idempotency-Key": "activate-one", "If-Match": '"1"'},
    )
    assert replay.json() == active.json()
    changed = await client.put(
        f"/api/v1/notifications/rules/{identifier}",
        json=body | {"name": "Revisión"},
        headers=headers | {"Idempotency-Key": "revision-one", "If-Match": '"2"'},
    )
    assert changed.status_code == 200, changed.text
    assert (
        changed.json()["status"] == "pausada" and changed.json()["version_number"] == 2
    )
    replay = await client.post(
        "/api/v1/notifications/rules",
        json=body,
        headers=headers | {"Idempotency-Key": "create-one"},
    )
    assert replay.json() == first
    versions = await client.get(f"/api/v1/notifications/rules/{identifier}/versions")
    assert len(versions.json()["items"]) == 2
    missing = await client.post(
        f"/api/v1/notifications/rules/{identifier}/pause",
        headers=headers | {"Idempotency-Key": "pause-one"},
    )
    assert missing.status_code == 428
    wrong = await client.put(
        f"/api/v1/notifications/rules/{identifier}",
        json=body,
        headers=headers | {"Idempotency-Key": "revision-one", "If-Match": '"3"'},
    )
    assert wrong.status_code == 409
    stale = await client.post(
        f"/api/v1/notifications/rules/{identifier}/pause",
        headers=headers | {"Idempotency-Key": "pause-one", "If-Match": '"1"'},
    )
    assert stale.status_code == 412


@pytest.mark.parametrize("role,status", [("operador", 403), (None, 401)])
async def test_permissions_precede_invalid_body(
    client, account_factory, session_factory, identity_settings, role, status
):
    """Anonymous/operator do not get schema/object metadata by submitting malformed unauthorized mutations."""
    headers = {}
    if role:
        _, headers = await authenticated(
            client, account_factory, session_factory, identity_settings, role
        )
    response = await client.post(
        "/api/v1/notifications/rules", json={"password": "PRIVATE008"}, headers=headers
    )
    assert response.status_code == status and "PRIVATE008" not in response.text


@pytest.mark.parametrize(
    "invalid",
    [
        {"name": "  "},
        {"timezone": "+03:00"},
        {
            "schedule": {
                "kind": "diaria",
                "starts_at": "2026-01-01",
                "local_time": "99:00",
            }
        },
        {"recipient_ids": []},
        {"html": "<private>"},
        {
            "mode": "urgente",
            "condition": {
                "kind": "consumo",
                "category_id": "CAT-01",
                "threshold_kwh": 0.1,
            },
        },
    ],
)
async def test_closed_input_validation(
    client, account_factory, session_factory, identity_settings, invalid
):
    """No coercion of naive times, binary floats, extra fields, absent recipients or invalid names/zones."""
    account, headers = await authenticated(
        client, account_factory, session_factory, identity_settings
    )
    response = await client.post(
        "/api/v1/notifications/rules",
        json=config(account.id) | invalid,
        headers=headers | {"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422, response.text


async def test_audit_content_rejects_operator_recipient(
    client, account_factory, session_factory, identity_settings
):
    """An administrator cannot target administrative history to an operator through a notification."""
    _, headers = await authenticated(
        client, account_factory, session_factory, identity_settings
    )
    recipient = await account_factory(role="operador")
    response = await client.post(
        "/api/v1/notifications/rules",
        json=config(recipient.id, content_types=["cambios_administrativos"]),
        headers=headers | {"Idempotency-Key": "private-audit"},
    )
    assert response.status_code == 422


async def test_catalog_scoped_recipients_and_request_boundaries(
    client, account_factory, session_factory, identity_settings
):
    """All reads are no-store; cross-origin/invalidCSRF, missing objects, invalid limits and mixed-idempotency bodies fail safely."""
    account, headers = await authenticated(
        client, account_factory, session_factory, identity_settings
    )
    operator = await account_factory(role="operador")
    types = await client.get("/api/v1/notifications/catalog")
    assert types.status_code == 200 and types.headers["cache-control"] == "no-store"
    recipients = await client.get(
        "/api/v1/notifications/recipients",
        params={"content_types": "cambios_administrativos"},
    )
    assert recipients.status_code == 200
    assert (
        next(
            row for row in recipients.json()["items"] if row["id"] == str(operator.id)
        )["eligible"]
        is False
    )
    assert (
        await client.get("/api/v1/notifications/rules", params={"limit": 101})
    ).status_code == 422
    assert (
        await client.get("/api/v1/notifications/rules/" + str(uuid4()))
    ).status_code == 404
    for bad in [
        headers | {"Origin": "http://foreign.test"},
        headers | {"X-CSRF-Token": "invalid"},
    ]:
        assert (
            await client.post(
                "/api/v1/notifications/rules",
                json=config(account.id),
                headers=bad | {"Idempotency-Key": "bad-boundary"},
            )
        ).status_code == 403
