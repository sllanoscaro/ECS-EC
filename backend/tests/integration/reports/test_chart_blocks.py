"""005 uses actual002 calendar buckets and prints both local occurrences at a DST fold."""

from io import BytesIO
from uuid import UUID
import pytest
from pypdf import PdfReader
from sqlalchemy import select
from backend.tests.unit.consumption.test_catalog import installation
from backend.tests.unit.consumption.test_validation import record
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.reports.test_snapshot_foundations import request_report
from ecs_ec.consumption.models import instant
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Capture

pytestmark = pytest.mark.integration


async def test_dst_day_has_twenty_five_blocks_and_two_offsets(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """The two01:00 hours keep distinct positions and explicit offsets, even when other axis labels are thinned."""
    env = costs_environment
    async with UnitOfWork(env["database"].sessions) as uow:
        await ConfigurationService(env["clock"], MeasurementStore()).apply(
            uow,
            building_id=env["building_id"],
            request=installation(
                tuple(range(1, 8)), timezone="America/New_York"
            ).model_copy(update={"expected_revision": 1, "effective_from": None}),
            actor_ref="process:report_fixture",
        )
        await uow.commit()
    env["clock"].advance(
        (instant("2026-11-02T06:00:00Z") - env["clock"].now()).total_seconds()
    )
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                value="1",
                start="2026-11-01T05:00:00Z",
                end="2026-11-01T06:00:00Z",
            ),
            record(
                category_id="CAT-01",
                source_id=UUID(int=1),
                value="2",
                start="2026-11-01T06:00:00Z",
                end="2026-11-01T07:00:00Z",
            ),
        ],
    )
    rid, _, status = await request_report(
        costs_client,
        account_factory,
        session_factory,
        identity_settings,
        {"scale": "diario", "date": "2026-11-01"},
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        capture = await uow.session.scalar(
            select(Capture).where(Capture.request_id == rid)
        )
        assert len(capture.data["chart_blocks"]) == 25
    text = (
        PdfReader(BytesIO((await costs_client.get(status["download_path"])).content))
        .pages[0]
        .extract_text()
    )
    from pypdf.generic import ContentStream

    content = (await costs_client.get(status["download_path"])).content
    reader = PdfReader(BytesIO(content))
    operations = ContentStream(reader.pages[0]["/Contents"], reader).operations
    assert sum(op == b"re" for _, op in operations) == 25
    assert "01:00 -0400" in text and "01:00 -0500" in text and "Horas repetidas" in text
