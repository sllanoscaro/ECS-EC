"""005 retains actual002 annual aggregate after authorized original-detail withdrawal."""

from io import BytesIO
from uuid import UUID
import pytest
from pypdf import PdfReader
from sqlalchemy import select
from backend.tests.unit.consumption.test_validation import record
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.reports.test_snapshot_foundations import request_report
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.consumption.retention import Retention
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Capture

pytestmark = pytest.mark.integration


async def test_year_1200_survives_real_withdrawal_without_monthly_points(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """A year-contained interval has no month-contained points; withdrawal cannot replace its real1200 total by zero."""
    env = costs_environment
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                value="1200",
                start="2025-01-01T03:00:00Z",
                end="2026-01-01T03:00:00Z",
            )
        ],
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        row = await uow.session.scalar(select(IncorporatedRecord))
        identifier = row.id
        deadline = row.retain_until
    env["clock"].advance((deadline - env["clock"].now()).total_seconds())
    result = await Retention(
        env["database"],
        env["clock"],
        authorized_processes={"process:report_fixture": {env["building_id"]}},
    ).withdraw_detail(
        building_id=env["building_id"],
        record_ids=(identifier,),
        process="process:report_fixture",
        reason="expired_detail",
    )
    assert result[0]["status"] == "withdrawn", result
    rid, _, status = await request_report(
        costs_client,
        account_factory,
        session_factory,
        identity_settings,
        {"scale": "anual", "year": 2025},
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        snapshot = await uow.session.scalar(
            select(Capture).where(Capture.request_id == rid)
        )
        assert snapshot.data["energy_rows"][0]["energy_kwh"] == "1200"
        assert not any(
            b["energy_kwh"] is not None for b in snapshot.data["chart_blocks"]
        )
    text = (
        PdfReader(BytesIO((await costs_client.get(status["download_path"])).content))
        .pages[0]
        .extract_text()
    )
    assert "1200" in text and "no se recalcula" in text
