"""007 technical failures cannot condition actual001/002/004/005 commits or006 permissions."""

from backend.tests.integration.reports.test_observability import (
    test_technical_failure_cannot_change_pdf as test_technical_failure_cannot_change_pdf,
)
from backend.tests.integration.identity.test_telemetry import (
    test_mutation_and_authorization_survive_technical_failure as test_mutation_and_authorization_survive_technical_failure,
)
from backend.tests.integration.consumption.test_telemetry import (
    test_technical_failure_does_not_change_detail as test_technical_failure_does_not_change_detail,
)
from backend.tests.integration.consumption.test_history_telemetry import (
    test_unavailable_emitter_cannot_prevent_admission as test_unavailable_emitter_cannot_prevent_admission,
)

import pytest
from backend.tests.contract.costs.test_calculations_api import authenticate, prepared
from ecs_ec.observability.lifecycle import Policy, Telemetry


@pytest.mark.parametrize("fault", ["admission", "queue", "spool"])
async def test_real_costs_commit_under_technical_failures(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
    monkeypatch,
    fault,
):
    """A100000CLP immutable calculation still commits; safe failures/losses remain on the actual emitter."""
    telemetry = Telemetry(
        Policy(environment="test", spool=tmp_path / "isolated"), autostart=False
    )
    costs_client._transport.app.state.telemetry = telemetry

    def fail(*args, **kwargs):
        """Break only a technical boundary without exposing raw internal input."""
        raise RuntimeError("PRIVATE_TECHNICAL_ISOLATION")

    try:
        if fault == "admission":
            monkeypatch.setattr(telemetry, "begin", fail)
        if fault == "queue":
            for _ in range(1100):
                telemetry.complete(telemetry.begin("cost.query", "costs"))
        if fault == "spool":
            telemetry.logs._writer = fail
        body = await prepared(costs_environment)
        headers = await authenticate(
            costs_client, account_factory, session_factory, identity_settings
        )
        response = await costs_client.post(
            "/api/v1/costs/calculations", json=body, headers=headers
        )
        assert (
            response.status_code == 201
            and response.json()["complete_total"] == "100000"
        )
        assert (
            await costs_client.get(
                "/api/v1/costs/calculations/" + response.json()["id"]
            )
        ).json() == response.json()
        if fault == "queue":
            assert telemetry.logs.dropped > 0 and telemetry.logs.depth <= 1024
        if fault == "spool":
            while telemetry.logs.drain_one():
                pass
            assert telemetry.logs.spool_dropped > 0
        assert "PRIVATE_TECHNICAL_ISOLATION" not in response.text
    finally:
        telemetry.shutdown()
