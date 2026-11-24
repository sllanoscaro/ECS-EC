"""005 HTTP contract uses real006 authorization and real001/002/004 snapshots on PostgreSQL."""

import asyncio
import hashlib
from uuid import uuid4
import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.support.pdf_assertions import read_a4_document

pytestmark = pytest.mark.integration


async def terminal(client, identifier):
    """Wait at most15s for the real in-process worker; never replace it with fixture PDF bytes."""
    for _ in range(150):
        response = await client.get("/api/v1/reports/" + identifier)
        assert response.status_code == 200, response.text
        if response.json()["state"] in {"generado", "fallido"}:
            return response.json()
        await asyncio.sleep(0.1)
    pytest.fail("report_worker_did_not_finish")


async def test_request_replay_download_and_revocation(
    costs_client, account_factory, session_factory, identity_settings
):
    """An operator generates an empty past report, replays once, downloads exact stored bytes and loses access on logout."""
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings, "operador"
    )
    body = {"scale": "anual", "year": 2024}
    admitted = await client.post("/api/v1/reports", json=body, headers=headers)
    assert admitted.status_code == 202, admitted.text
    identifier = admitted.json()["id"]
    assert admitted.json()["download_path"] is None
    assert (
        await client.post("/api/v1/reports", json=body, headers=headers)
    ).json() == admitted.json()
    assert (
        await client.post(
            "/api/v1/reports", json={"scale": "anual", "year": 2023}, headers=headers
        )
    ).status_code == 409
    status = await terminal(client, identifier)
    assert status["state"] == "generado", status
    download = await client.get(status["download_path"])
    assert (
        download.status_code == 200 and download.headers["cache-control"] == "no-store"
    )
    read_a4_document(
        download.content, required_text=("ECS-EC", "CAT-07", "Calidad", "2024")
    )
    assert hashlib.sha256(download.content).hexdigest() == status["sha256"]
    assert len(download.content) == status["byte_length"]
    assert (await client.get(status["download_path"])).content == download.content
    client.cookies.clear()
    assert (await client.get(status["download_path"])).status_code == 401
    assert (
        await client.post("/api/v1/reports", json=body, headers=headers)
    ).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"scale": "diario", "date": "2026-02-30"},
        {"scale": "anual", "year": 9998},
        {"scale": "mensual", "year": 2025, "month": 0},
    ],
)
async def test_invalid_selections_are_field_errors(
    costs_client, account_factory, session_factory, identity_settings, body
):
    """Invalid/calendar-future selections return sanitized422 with fields and never admit a generation."""
    client = costs_client
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    response = await client.post("/api/v1/reports", json=body, headers=headers)
    assert response.status_code == 422, response.text
    assert response.json()["field_errors"]


async def test_permission_origin_key_and_not_found(
    costs_client, account_factory, session_factory, identity_settings
):
    """Every operation requires current006 policy; request guards run before resource/body access."""
    client = costs_client
    body = {"scale": "anual", "year": 2024}
    assert (await client.post("/api/v1/reports", json=body)).status_code == 401
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    assert (
        await client.post(
            "/api/v1/reports",
            json=body,
            headers=headers | {"Origin": "https://invalid.test"},
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/reports",
            json=body,
            headers={
                "Origin": headers["Origin"],
                "X-CSRF-Token": headers["X-CSRF-Token"],
            },
        )
    ).status_code == 422
    assert (await client.get("/api/v1/reports/" + str(uuid4()))).status_code == 404
