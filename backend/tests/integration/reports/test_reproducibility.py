"""005 functional equality is independent of extended operational retention metadata."""

import pytest
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from backend.tests.integration.reports.test_costs_pdf_end_to_end import emit

pytestmark = pytest.mark.integration


async def test_same_cutoff_after_source_retention_extension(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Two captures at one cutoff keep the same functional hash although the first protects older004 evidence."""
    env = costs_environment
    client = costs_client
    body = await prepared(env)
    headers = await authenticate(
        client, account_factory, session_factory, identity_settings
    )
    response = await client.post(
        "/api/v1/costs/calculations", json=body, headers=headers
    )
    assert response.status_code == 201, response.text
    env["clock"].advance(60)
    first = await emit(client, headers, env["database"])
    second = await emit(client, headers, env["database"])
    assert first[2]["cutoff_at"] == second[2]["cutoff_at"]
    assert first[2]["energy_rows"] == second[2]["energy_rows"]
    assert first[3] == second[3]
    assert (await client.get(first[0]["download_path"])).content == first[1]
