"""005 independent requests preserve source state and accept provisional/current or empty historical periods."""

from uuid import uuid4
import pytest
from sqlalchemy import select, func
from backend.tests.contract.costs.test_calculations_api import authenticate
from backend.tests.contract.reports.test_reports_api import terminal
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Capture
from ecs_ec.consumption.models import IncorporatedRecord

pytestmark = pytest.mark.integration


async def test_current_and_empty_reports_have_no_reception_gate(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """Two new requests at the same clock need no15minute wait and cannot write a consumption measurement."""
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    states = []
    for year in (2025, 2024):
        result = await costs_client.post(
            "/api/v1/reports",
            json={"scale": "anual", "year": year},
            headers=headers | {"Idempotency-Key": uuid4().hex},
        )
        assert result.status_code == 202, result.text
        states.append(await terminal(costs_client, result.json()["id"]))
    assert (
        all(s["state"] == "generado" for s in states)
        and states[0]["id"] != states[1]["id"]
    )
    async with UnitOfWork(costs_environment["database"].sessions) as uow:
        captures = (await uow.session.scalars(select(Capture))).all()
        assert sorted(s.data["provisional"] for s in captures) == [False, True]
        assert (
            await uow.session.scalar(
                select(func.count()).select_from(IncorporatedRecord)
            )
            == 0
        )
