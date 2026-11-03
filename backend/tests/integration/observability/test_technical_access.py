"""Real external access/revocation and existing functional006 separation; no simulated roles."""

import pytest


async def test_tls_basic_and_revocation_next_keepalive_request(gateway_client, gateway_provision):
    """Revoke the mounted htpasswd file without reload; same client/cookies cannot query again."""
    response = await gateway_client.get("/grafana/api/frontend/settings")
    assert response.status_code == 200
    assert (await gateway_client.get("/jaeger/api/v3/services")).status_code == 200
    gateway_provision("revoke")
    assert (await gateway_client.get("/grafana/api/frontend/settings")).status_code == 401
    assert (await gateway_client.get("/jaeger/api/v3/services")).status_code == 401
    gateway_provision("grant")


async def test_only_technical_basic_never_grants_functional_account(client):
    """Existing real006 endpoints reject technical credentials and role declarations without a session."""
    for path in ("/api/v1/auth/session", "/api/v1/identity/accounts", "/api/v1/identity/administration-history"):
        response = await client.get(path, auth=("prog-test-01", "Synthetic technical password 007"),
                                    headers={"X-Role": "programador", "X-WEBAUTH-USER": "prog-test-01"})
        assert response.status_code in {401, 403}


async def test_functional_session_never_grants_technical_access(client, account_factory, login, gateway_client):
    """Actual006 administrator cookies confer no Basic authorization to the technical listener."""
    admin = await account_factory(role="administrador_tecnico")
    assert (await login(admin.email)).status_code == 200
    assert (await client.get("/api/v1/identity/administration-history")).status_code == 200
    response = await gateway_client.get("/grafana/", auth=None, headers={"Cookie": "; ".join(f"{k}={v}" for k, v in client.cookies.items())})
    assert response.status_code == 401


async def test_other_environment_never_accepts_test_basic(gateway_client):
    """A second actual stack has independent credentials; client filters cannot authorize it."""
    import os
    import ssl
    from pathlib import Path
    import httpx
    other = os.environ.get("OBS_TEST_OTHER_ROOT")
    if not other:
        pytest.skip("Second isolated stack/CA required for cross-environment acceptance")
    tls = ssl.create_default_context(cafile=str(Path(other) / "ca.crt"))
    async with httpx.AsyncClient(verify=tls, trust_env=False, base_url="https://localhost:3445") as client:
        response = await client.get("/jaeger/api/v3/services", auth=("prog-test-01", "Synthetic technical password 007"),
                                    headers={"X-WEBAUTH-USER": "prog-test-01", "X-Environment": "test"})
        assert response.status_code == 401
        assert (await client.get("/jaeger/api/v3/services", auth=("prog-other-01", "Synthetic other environment 007"))).status_code == 200


def test_process_mtls_identities_have_no_human_query_scope(gateway_root):
    """Real private listeners separate app/Alloy/health certificates and never accept Basic as mTLS."""
    import json
    import os
    import subprocess
    code = '''
import ssl,httpx,json
out={}
for identity in ['app','alloy','health']:
 ctx=ssl.create_default_context(cafile='/tls/'+identity+'/ca.crt')
 ctx.load_cert_chain('/tls/'+identity+'/'+identity+'.crt','/tls/'+identity+'/'+identity+'.key')
 with httpx.Client(verify=ctx,trust_env=False,timeout=8) as client:
  out[identity+'_human']=client.get('https://technical-gateway:8443/jaeger/api/v3/services',headers={'Host':'localhost'}).status_code
  out[identity+'_trace']=client.post('https://technical-gateway:8444/v1/traces',content=b'',headers={'Content-Type':'application/x-protobuf'}).status_code
  out[identity+'_health']=client.get('https://technical-gateway:8446/collector-health').status_code
  out[identity+'_trace_read']=client.get('https://technical-gateway:8444/v1/traces').status_code
ctx=ssl.create_default_context(cafile='/tls/app/ca.crt')
with httpx.Client(verify=ctx,trust_env=False,timeout=8) as client:
 out['basic_ingest']=client.post('https://technical-gateway:8444/v1/traces',auth=('prog-test-01','Synthetic technical password 007')).status_code
print(json.dumps(out))
'''
    command = ["docker", "run", "--rm", "-i", "--user", str(os.getuid()), "--network", "ecs007-validation_technical_ingest"]
    for name in ("app", "alloy", "health"):
        command += ["-v", f"{gateway_root}/clients/{name}:/tls/{name}:ro"]
    command += ["ecs007-validation-app:local", "/app/.venv/bin/python", "-"]
    result = subprocess.run(command, input=code, text=True, capture_output=True, timeout=40, check=True)
    statuses = json.loads(result.stdout)
    assert statuses["app_trace"] == 200
    assert statuses["health_health"] == 200
    assert statuses["basic_ingest"] in {400, 401, 403}
    for name in ("app", "alloy", "health"):
        assert statuses[name + "_human"] == 401
        assert statuses[name + "_trace_read"] == 403
    assert statuses["app_health"] == 403
    assert statuses["alloy_health"] == 403
    assert statuses["alloy_trace"] == 403
    assert statuses["health_trace"] == 403


async def test_operator_keeps_functional_history_denial(client, account_factory, login, gateway_client):
    """Actual006 operator can have a session while both administrative history and technical reads deny."""
    account = await account_factory(role="operador")
    assert (await login(account.email)).status_code == 200
    assert (await client.get("/api/v1/identity/administration-history")).status_code == 403
    response = await gateway_client.get("/logs/loki/api/v1/labels", auth=None,
                                        headers={"Cookie": "; ".join(f"{k}={v}" for k, v in client.cookies.items())})
    assert response.status_code == 401


async def test_pdf_permission_matrix_requires_real005():
    """Do not credit PDF permissions from missing routes;005's real generation/download is prerequisite."""
    pytest.skip("005 has only snapshot/ports; no real PDF API provider for SC-001 yet")


async def test_private_source_addresses_and_host_ports_cannot_bypass(gateway_root):
    """Actual source IPs have no host route; only the Basic listener publishes a loopback host port.

    Internal Docker bridges inhibit IPv4 gateway assignment as well as NAT/port
    publication. A host operator with network-administration privileges remains an
    infrastructure operator; those privileges are never conferred by Programador.
    """
    import asyncio
    import json
    import subprocess
    import httpx
    sources = {"loki": (3100, "technical_store"), "jaeger": (16686, "technical_store"),
               "grafana": (3000, "technical_store"), "alloy": (12345, "technical_ingest")}
    async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
        async def check(service, port, network):
            """Require absence of both published ports and direct source responses from the host."""
            details = json.loads(subprocess.check_output(["docker", "inspect", f"ecs007-validation-{service}-1"]))[0]
            assert details["State"]["Running"]
            assert not details["HostConfig"].get("PortBindings")
            address = details["NetworkSettings"]["Networks"]["ecs007-validation_" + network]["IPAddress"]
            with pytest.raises(httpx.TransportError):
                await client.get(f"http://{address}:{port}/")
        await asyncio.gather(*(check(name, *values) for name, values in sources.items()))
    details = json.loads(subprocess.check_output(["docker", "inspect", "ecs007-validation-technical-gateway-1"]))[0]
    assert set(details["HostConfig"]["PortBindings"]) == {"8443/tcp"}
    assert details["HostConfig"]["PortBindings"]["8443/tcp"][0]["HostIp"] == "127.0.0.1"


async def test_missing_authorization_file_denies_without_fallback(gateway_client, gateway_root):
    """Removing the mounted file immediately denies even valid Basic/cookie without reloading."""
    authorized = gateway_root / "credentials/authorized"
    temporary = gateway_root / "credentials/.authorization-test-backup"
    authorized.rename(temporary)
    try:
        response = await gateway_client.get("/jaeger/api/v3/services", headers={"Cookie": "grafana_session=previous"})
        assert response.status_code in {401, 403, 500}
    finally:
        temporary.rename(authorized)
    assert (await gateway_client.get("/jaeger/api/v3/services")).status_code == 200
