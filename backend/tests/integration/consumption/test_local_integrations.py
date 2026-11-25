"""001:T056 follows actual003 files through002/001,008 SMTP and007 local stores.

Only explicitly provisioned test resources are allowed. The business clock is injected
internally to select closed windows without waiting an hour; SSH, HTTP, SMTP, TLS,
Alloy/Loki and OTLP/Jaeger are actual transports. This is not a cadence, latency,
physical-meter, external-relay or retention acceptance test.
"""

import asyncio
import json
import os
import socket
import ssl
import subprocess
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import asyncssh
import httpx
import pytest
import uvicorn
from ecs_ec.acquisition.sftp_server import start_listener
from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.consumption.models import ReceptionAttempt
from ecs_ec.notifications.calendar import stamp
from ecs_ec.notifications.dispatcher import Dispatcher
from ecs_ec.notifications.episodes import Evaluator
from ecs_ec.notifications.models import Attempt, Delivery, Message
from ecs_ec.notifications.scheduler import Scheduler
from ecs_ec.notifications.settings import NotificationSettings
from ecs_ec.observability.lifecycle import Policy, Telemetry
from sqlalchemy import func, select
from starlette.staticfiles import StaticFiles

from backend.tests.contract.notifications.test_rules_api import config
from backend.tests.integration.acquisition.conftest import (  # noqa: F401
    acquisition_environment as acquisition_environment,
)
from backend.tests.integration.acquisition.conftest import (
    sftp_environment as sftp_environment,
)
from backend.tests.integration.acquisition.test_recovery import (
    service as acquisition_service,
)
from backend.tests.integration.notifications.conftest import (  # noqa: F401
    notification_database_reset as notification_database_reset,
)
from backend.tests.integration.observability.conftest import (  # noqa: F401
    deliver_telemetry as deliver_telemetry,
)
from backend.tests.integration.observability.conftest import (
    gateway_client as gateway_client,
)
from backend.tests.integration.observability.conftest import (
    gateway_image as gateway_image,
)
from backend.tests.integration.observability.conftest import (
    gateway_project as gateway_project,
)
from backend.tests.integration.observability.conftest import (
    gateway_root as gateway_root,
)
from backend.tests.support.source_sftp import (
    evaluations,
    generated_publication,
    publish_generated,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("CONSUMPTION_LOCAL_INTEGRATIONS") != "1",
        reason="Explicit001:T056 PostgreSQL/Mailpit/007/browser resources required",
    ),
]


@pytest.fixture
def live_telemetry(gateway_root):
    """Reuse007's actual emitter with the exclusive stack's explicit24h test policy; never test TTL here."""
    telemetry = Telemetry(
        Policy(environment="test", spool=gateway_root / "spool", retention_hours=24),
        autostart=False,
    )
    try:
        yield telemetry
    finally:
        telemetry.shutdown()


@pytest.fixture
def identity_settings(identity_settings):
    """Use the real001/002 fixture building, preserving006's test-only keys and policy."""
    return identity_settings.model_copy(update={"building_id": UUID(int=99)})


async def enter(http, origin, email):
    """Authenticate through006's ordinary CSRF/password flow; return the current CSRF header."""
    response = await http.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    response = await http.post(
        "/api/v1/auth/login",
        headers={"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]},
        json={"email": email, "password": "Synthetic password 006"},
    )
    assert response.status_code == 200
    return {"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]}


async def activate(http, body, headers):
    """Create, preview and explicitly activate an immutable rule using actual008 HTTP contracts."""
    created = await http.post(
        "/api/v1/notifications/rules",
        json=body,
        headers=headers | {"Idempotency-Key": str(uuid4())},
    )
    assert created.status_code == 201, created.text
    preview = await http.post(
        "/api/v1/notifications/rules/preview", json=body, headers=headers
    )
    assert preview.status_code == 200, preview.text
    response = await http.post(
        "/api/v1/notifications/rules/" + created.json()["id"] + "/activate",
        json={"preview_token": preview.json()["preview_token"]},
        headers=headers | {"Idempotency-Key": str(uuid4()), "If-Match": '"1"'},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def local_chain(
    notification_database_reset,
    sftp_environment,
    client,
    gateway_root,
    live_telemetry,
    tmp_path,
):
    """Expose the actual composed app/listener on loopback, using only private fixture setup.

    Existing owners supply persistence, accounts, parsers, rendering and transports.
    The fixture replaces no business operation and adds no HTTP fixture/fault route.
    It closes only its own listeners and leaves the caller's technical stack running.
    """
    env = sftp_environment
    app = client._transport.app
    web = Path(os.environ["CONSUMPTION_LOCAL_BROWSER_WEB"]).resolve()
    assert (web / "index.html").is_file(), "Build the actual static export first"
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    app.state.identity.settings = app.state.identity.settings.model_copy(
        update={"public_url": origin}
    )
    app.state.settings.web_directory = web
    for route in app.routes:
        if getattr(route, "name", None) == "web":
            route.app = StaticFiles(directory=web, html=True)
    app.state.telemetry = live_telemetry
    notifications = app.state.notifications
    notifications.telemetry = live_telemetry
    notifications.settings = NotificationSettings(
        _env_file=None,
        environment="test",
        smtp_host="127.0.0.1",
        smtp_port=int(os.environ["CONSUMPTION_LOCAL_SMTP_PORT"]),
        app_public_base_url=origin,
    )
    # Restart only this ephemeral fixture listener to attach the installed007 emitter.
    env["listener"].close()
    await env["listener"].wait_closed()
    options = env["settings"].model_copy(
        update={
            "host_key_file": env["private"].parent / "host",
            "auth_file": env["private"].parent / "auth",
        }
    )
    listener = await start_listener(
        env["database"], env["clock"], options, live_telemetry
    )
    env["port"] = listener.get_port()
    env["known"].write_bytes(
        f"[127.0.0.1]:{env['port']} ".encode()
        + asyncssh.read_private_key(options.host_key_file).export_public_key()
    )
    acquisition = acquisition_service(env)
    acquisition.telemetry = acquisition.reception.telemetry = live_telemetry
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            access_log=False,
            log_level="critical",
        )
    )
    job = asyncio.create_task(server.serve())
    try:
        async with httpx.AsyncClient(
            base_url=origin, trust_env=False, timeout=10
        ) as http:
            for _ in range(100):
                try:
                    if (await http.get("/api/v1/health/ready")).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if job.done():
                    await job
                    pytest.fail("Private monolith exited before readiness")
                await asyncio.sleep(0.1)
            else:
                pytest.fail("Private monolith readiness timeout")
            async with httpx.AsyncClient(
                base_url=os.environ["CONSUMPTION_LOCAL_MAILPIT_URL"], trust_env=False
            ) as mail:
                earlier_mail = {
                    item["ID"]
                    for item in (await mail.get("/api/v1/messages")).json()["messages"]
                }
            yield dict(
                env=env,
                app=app,
                http=http,
                origin=origin,
                notifications=notifications,
                acquisition=acquisition,
                earlier_mail=earlier_mail,
            )
    finally:
        server.should_exit = True
        await asyncio.wait_for(job, 15)
        listener.close()
        await listener.wait_closed()
        notifications.telemetry = None
        app.state.telemetry = None
        # Clean only008 fixture evidence before002 tears down its protected history.
        from sqlalchemy import text

        async with env["database"].engine.begin() as connection:
            await connection.execute(
                text("TRUNCATE notification_rule, notification_evidence CASCADE")
            )


async def browser(chain, tmp_path, expected, native_format):
    """Run real UI/HTTP assertions using a private expected-data file and synthetic password."""
    artifacts = Path(os.environ["CONSUMPTION_LOCAL_ARTIFACTS"])
    artifacts.mkdir(parents=True, exist_ok=True)
    password = tmp_path / "browser-password"
    password.write_text("Synthetic password 006")
    password.chmod(0o600)
    source = tmp_path / "browser-expected.json"
    source.write_text(json.dumps(expected))
    source.chmod(0o600)
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "node",
            "--jitless",
            "node_modules/@playwright/test/cli.js",
            "test",
            "tests/e2e/consumption-local-integrations.spec.ts",
            "--workers=1",
        ],
        cwd="frontend",
        env=os.environ
        | {
            "E2E_BASE_URL": chain["origin"],
            "IDENTITY_E2E_PASSWORD_FILE": str(password),
            "CONSUMPTION_LOCAL_BROWSER_EXPECTED": str(source),
            "CONSUMPTION_LOCAL_BROWSER_FORMAT": native_format,
            "CONSUMPTION_LOCAL_BROWSER_ARTIFACTS": str(artifacts),
        },
        capture_output=True,
        text=True,
        timeout=100,
    )
    (artifacts / f"browser-{native_format}.log").write_text(
        result.stdout + result.stderr
    )
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-500:]


@pytest.mark.parametrize("native_format", ["csv", "json"])
async def test_sftp_query_mail_and_local_signals(
    local_chain,
    account_factory,
    gateway_root,
    gateway_client,
    deliver_telemetry,
    live_telemetry,
    tmp_path,
    native_format,
):
    """Two native4kWh intervals remain identical in001 API/UI,008 evidence and real local007 stores."""
    chain = local_chain
    env, http = chain["env"], chain["http"]
    admin = await account_factory(
        role="administrador_tecnico", email="local-chain-admin@example.test"
    )
    recipient = await account_factory(email="local-chain-operator@example.test")
    headers = await enter(http, chain["origin"], admin.email)
    periodic = await activate(
        http,
        config(
            recipient.id,
            name="Recepción SFTP " + native_format,
            content_types=["recepcion", "calidad"],
            schedule=dict(
                kind="intervalo",
                interval_value=1,
                interval_unit="horas",
                starts_at=stamp(env["clock"].now()),
            ),
        ),
        headers,
    )
    urgent_body = config(
        recipient.id,
        name="Consumo SFTP " + native_format,
        mode="urgente",
        condition=dict(
            kind="consumo",
            category_id="CAT-03",
            unit="kWh",
            window=dict(kind="intervalo", measurement_interval_seconds=900),
            comparison="gt",
            threshold_kwh="3",
        ),
    )
    urgent_body.pop("content_types")
    urgent_body.pop("schedule")
    urgent = await activate(http, urgent_body, headers)
    env["clock"].advance(1801)
    run = await generated_publication(env, tmp_path, native_format)
    await publish_generated(env, tmp_path, run)
    assert await chain["acquisition"].recover() == 1
    (evaluation,) = await evaluations(env)
    assert evaluation.state == "completed"
    assert [row["status"] for row in evaluation.outcome["results"]] == [
        "accepted",
        "accepted",
    ]
    assert evaluation.outcome["updates"][0]["accepted_count"] == 2
    assert await chain["acquisition"].recover() == 0
    evaluator = Evaluator(chain["notifications"])
    assert await evaluator.tick() == 1
    env["clock"].advance(1799)
    scheduler = Scheduler(chain["notifications"])
    try:
        assert await scheduler.acquire()
        assert await scheduler.tick() == 1
        assert await scheduler.tick() == 0
    finally:
        await scheduler.close()
    dispatcher = Dispatcher(chain["notifications"])
    try:
        assert await dispatcher.dispatch_once() == 2
        assert await dispatcher.dispatch_once() == 0
    finally:
        await dispatcher.close()
    await http.aclose()
    # The injected hour exceeds006's idle timeout. Obtain a normal fresh session;
    # never lengthen session limits to accommodate a test clock.
    async with httpx.AsyncClient(
        base_url=chain["origin"], trust_env=False, timeout=10
    ) as operator:
        await enter(operator, chain["origin"], recipient.email)
        params = dict(
            start="2025-12-31T21:00:00-03:00",
            end="2025-12-31T21:30:00-03:00",
            timezone="America/Santiago",
        )
        wrong_offset = await operator.get(
            "/api/v1/consumption/categories/CAT-03/detail",
            params=params | {"start": "2026-01-01T00:00:00Z"},
        )
        assert wrong_offset.status_code == 422
        detail_response = await operator.get(
            "/api/v1/consumption/categories/CAT-03/detail", params=params
        )
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.headers["cache-control"] == "no-store"
        detail = detail_response.json()
        assert detail["state"] == "available" and len(detail["rows"]) == 2
        assert [Decimal(row["energy_kwh"]) for row in detail["rows"]] == [
            Decimal("4"),
            Decimal("4"),
        ]
        assert [(row["start"], row["end"]) for row in detail["rows"]] == [
            ("2025-12-31T21:00:00-03:00", "2025-12-31T21:15:00-03:00"),
            ("2025-12-31T21:15:00-03:00", "2025-12-31T21:30:00-03:00"),
        ]
        for category in ["CAT-01", "CAT-05"]:
            missing = await operator.get(
                f"/api/v1/consumption/categories/{category}/detail", params=params
            )
            assert missing.status_code == 200
            assert missing.json()["state"] == "no_data" and missing.json()["rows"] == []
        assert (
            await operator.get("/api/v1/consumption/configuration")
        ).status_code == 403
        cookie = operator.cookies.get("ecs_ec_session")
    async with env["database"].sessions() as session:
        deliveries = list((await session.scalars(select(Delivery))).all())
        messages = {
            str(m.id): m.functional_content
            for m in (await session.scalars(select(Message))).all()
        }
        attempts = list((await session.scalars(select(Attempt))).all())
        assert len(deliveries) == len(attempts) == 2
        assert all(d.state == "aceptada" for d in deliveries)
        assert all(
            a.outcome == "aceptada" and a.effective_email == recipient.email
            for a in attempts
        )
        event_count = await session.scalar(
            select(func.count())
            .select_from(FunctionalEvent)
            .where(FunctionalEvent.source_module == "consumption")
        )
        captures = {content["rule_id"]: content for content in messages.values()}
        summary = captures[periodic["id"]]
        items = {item["kind"]: item for item in summary["summary_items"]}
        assert items["recepcion"]["count"] == 1 and items["calidad"]["count"] == 0
        assert all(item["coverage"] == "completa" for item in items.values())
        assert summary["data_status"] == "disponible"
        alert = captures[urgent["id"]]
        assert alert["evidence"][0]["value_kwh"] == "4"
        assert alert["evidence"][0]["origin"] == "medido"
        assert {ref["entity_id"] for ref in alert["evidence"][0]["source_refs"]} == {
            evaluation.outcome["results"][-1]["measurement_id"]
        }
        links = {
            d.id: chain["origin"] + "/notificaciones?entrega=" + str(d.id)
            for d in deliveries
        }
        delivery_ids = [str(d.id) for d in deliveries]
    async with httpx.AsyncClient(
        base_url=os.environ["CONSUMPTION_LOCAL_MAILPIT_URL"], trust_env=False
    ) as mail:
        listing = (await mail.get("/api/v1/messages")).json()
        own = [
            m
            for m in listing["messages"]
            if m["To"][0]["Address"] == recipient.email
            and m["ID"] not in chain["earlier_mail"]
        ]
        assert len(own) == 2
        captured = [(await mail.get("/api/v1/message/" + m["ID"])).json() for m in own]
        assert all(len(m["To"]) == 1 and not m["Cc"] and not m["Bcc"] for m in captured)
        for link in links.values():
            assert any(link in m["Text"] for m in captured)
        assert any("4 kWh" in m["Text"] and urgent["id"] in m["Text"] for m in captured)
        assert any(
            "recepcion:" in m["Text"] and periodic["id"] in m["Text"] for m in captured
        )
        assert all("Correo local de prueba" in m["Text"] for m in captured)
    await browser(
        chain,
        tmp_path,
        dict(
            rows=detail["rows"],
            delivery_links=list(links.values()),
            delivery_ids=delivery_ids,
            business_now=stamp(env["clock"].now()),
        ),
        native_format,
    )
    async with httpx.AsyncClient(
        base_url=chain["origin"], trust_env=False
    ) as anonymous:
        assert (await anonymous.get("/api/v1/consumption/catalog")).status_code == 401
        assert (
            await anonymous.get(
                "/api/v1/consumption/catalog",
                auth=("prog-test-01", "Synthetic technical password 007"),
            )
        ).status_code == 401
        assert (
            await anonymous.get("/api/v1/notifications/deliveries/" + delivery_ids[0])
        ).status_code == 401
    tls = ssl.create_default_context(cafile=str(gateway_root / "ca.crt"))
    async with httpx.AsyncClient(verify=tls, trust_env=False) as functional:
        denied = await functional.get(
            os.environ["OBS_TEST_URL"] + "/grafana/api/frontend/settings",
            headers={"Cookie": "ecs_ec_session=" + cookie},
        )
        assert denied.status_code == 401
    emitted, observed = await deliver_telemetry(live_telemetry)
    terminals = [e for e in observed if e["event"] == "reception.completed"]
    assert len(terminals) == 1 and terminals[0]["counts"]["records_accepted"] == 2
    async with env["database"].sessions() as session:
        reception = await session.get(ReceptionAttempt, evaluation.attempt_id)
        technical_context = dict(reception.technical_context)
    assert terminals[0]["attempt_ref"] == technical_context["attempt_ref"]
    assert (
        terminals[0]["publication_ref"]
        == evaluation.technical_context["publication_ref"]
    )
    assert (
        terminals[0]["parent_operation_ref"]
        == evaluation.technical_context["operation_ref"]
    )
    assert any(
        e["operation"] == "acquisition.receive" and e["outcome"] == "success"
        for e in observed
    )
    assert any(
        e["operation"] == "consumption.query_detail" and e["outcome"] == "success"
        for e in observed
    )
    smtp = [
        e for e in observed if e["event"] == "notification.delivery.attempt.completed"
    ]
    assert len(smtp) == 2
    assert {event["operation_ref"] for event in smtp} == set(delivery_ids)
    for event in smtp:
        trace = await gateway_client.get("/jaeger/api/v3/traces/" + event["trace_id"])
        assert trace.status_code == 200
    assert (
        await gateway_client.get("/grafana/api/dashboards/uid/ecs-platform")
    ).status_code == 200
    assert (
        await gateway_client.get("/grafana/api/dashboards/uid/ecs-notifications")
    ).status_code == 200
    # This controlled cohort has one logical reception, without replay. This is
    # a real LogQL query, not an exact-count guarantee under loss or replay.
    expression = (
        'sum(count_over_time({service_name="ecs-ec",environment="test"}'
        ' | json boot="boot_id", kind="event" | boot="'
        + live_telemetry.logs.boot_id
        + '" | kind="reception.completed" [5m]))'
    )
    metric = await gateway_client.get(
        "/logs/loki/api/v1/query", params={"query": expression}
    )
    assert metric.status_code == 200, metric.text[:200]
    assert Decimal(metric.json()["data"]["result"][0]["value"][1]) == 1
    signals = json.dumps(observed)
    assert recipient.email not in signals and admin.email not in signals
    assert (
        "SIMULATED-PAS600" not in signals and "20260101003000000_1.json" not in signals
    )
    for native_file in (run / "data").rglob("*"):
        if native_file.is_file():
            assert native_file.name not in signals
    async with env["database"].sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Delivery)) == 2
        assert await session.scalar(select(func.count()).select_from(Attempt)) == 2
        assert (
            await session.scalar(
                select(func.count())
                .select_from(FunctionalEvent)
                .where(FunctionalEvent.source_module == "consumption")
            )
            == event_count
        )
    result = dict(
        native_format=native_format,
        publication_id=str(evaluation.publication_id),
        attempt_id=str(evaluation.attempt_id),
        expected_energy_kwh=["4", "4"],
        record_refs=[r["measurement_id"] for r in evaluation.outcome["results"]],
        delivery_ids=delivery_ids,
        local_smtp_accepted=2,
        reception_summary_count=1,
        quality_rejections_count=0,
        technical_events=len(emitted),
        technical_reception_context=technical_context,
        logql_receptions="1",
        loki_unique_events=len({e["event_id"] for e in observed}),
        trace_ids=sorted({e["trace_id"] for e in observed if e.get("trace_id")}),
        browser="passed",
        business_clock="privately controlled; no latency/cadence claim",
        technical_transport="actual local Alloy/Loki and OTLP/Jaeger with TLS/Basic",
    )
    (
        Path(os.environ["CONSUMPTION_LOCAL_ARTIFACTS"])
        / f"results-{native_format}.json"
    ).write_text(json.dumps(result, indent=2) + "\n")
