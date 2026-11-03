"""Gateway contract vectors exercised against the actual TLS/Nginx stack when configured."""

import pytest

HUMAN_READS = ["/grafana/", "/grafana/api/frontend/settings", "/grafana/api/dashboards/uid/ecs-platform",
               "/logs/loki/api/v1/query?query=%7Bservice_name%3D%22ecs-ec%22%7D", "/jaeger/",
               "/jaeger/api/v3/services"]
DENIED = ["/grafana/api/admin/users", "/grafana/api/live/ws", "/grafana/api/datasources/proxy/1/http://evil/",
          "/logs/loki/api/v1/tail", "/logs/loki/api/v1/push", "/logs/loki/api/v1/delete", "/v1/traces",
          "/jaeger/api/sampling", "/jaeger/api/v3/traces/../../admin", "/grafana//api/admin/users",
          "/grafana/%2e%2e/logs/loki/api/v1/query", "/grafana/api/serviceaccounts", "/grafana/api/auth/keys"]


@pytest.mark.parametrize("path", DENIED)
async def test_non_allowlisted_routes_never_deliver(gateway_client, path):
    """Even valid human credentials do not grant administration, ingestion, streams or arbitrary proxies."""
    response = await gateway_client.get(path)
    assert response.status_code in {400, 401, 403, 404}
    assert b"ecs-ec technical log" not in response.content


@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH", "POST"])
async def test_write_methods_denied(gateway_client, method):
    """POST is denied everywhere except finite provisioned-datasource query endpoint."""
    response = await gateway_client.request(method, "/grafana/api/dashboards/uid/ecs-platform", json={})
    assert response.status_code in {400, 401, 403, 405}


async def test_limits_and_forged_identity(gateway_client):
    """Source row limits and body64KiB are enforced; public identity/cookies never replace Basic."""
    response = await gateway_client.get("/logs/loki/api/v1/query_range", params={"query": '{service_name="ecs-ec"}', "limit": "10001"})
    assert response.status_code == 400
    response = await gateway_client.post("/grafana/api/ds/query", content=b"x" * 65537)
    assert response.status_code in {400, 413}
    response = await gateway_client.get("/grafana/", auth=None,
                                        headers={"X-WEBAUTH-USER": "prog-test-01", "X-WEBAUTH-ROLE": "Admin", "Cookie": "grafana_session=fake"})
    assert response.status_code == 401


async def test_jaeger_v3_search_bounds_match_pinned_source(gateway_client):
    """Versioned searchDepth and time bounds cannot bypass finite Jaeger query limits."""
    response = await gateway_client.get("/jaeger/api/v3/traces", params={"query.serviceName": "ecs-ec", "query.searchDepth": "10001"})
    assert response.status_code == 400
    response = await gateway_client.get("/jaeger/api/v3/traces", params={"query.serviceName": "ecs-ec", "query.searchDepth": "10"})
    assert response.status_code in {200, 404}  # Jaeger returns404 for a valid empty search window.
    if response.status_code == 404:
        assert response.json()["error"] == {"httpCode": 404, "message": "No traces found"}
    else:
        assert response.headers["content-type"].startswith("application/json")
    # Pagination options from newer IDL are unsupported by2.22; never forward unknown controls.
    response = await gateway_client.get("/jaeger/api/v3/traces", params={"query.serviceName": "ecs-ec", "query.pagination.pageSize": "100000"})
    assert response.status_code == 400


async def test_host_encoding_duplicate_params_and_foreign_datasource(gateway_client):
    """Header/path/query ambiguity and arbitrary datasource selection fail before source delivery."""
    assert (await gateway_client.get("/jaeger/api/v3/services", headers={"Host": "foreign.test"})).status_code == 403
    for path in ("/grafana/%61pi/frontend/settings", "/logs//loki/api/v1/query?query=x", "/logs/loki/api/v1/query?query=x&limit=1&limit=10001"):
        assert (await gateway_client.get(path)).status_code in {400, 403}
    response = await gateway_client.post("/grafana/api/ds/query", json={"from": "1793670000000", "to": "1793670100000", "queries": [{"refId": "A", "datasource": {"uid": "foreign", "type": "loki"}}]})
    assert response.status_code == 400
