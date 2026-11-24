"""005 monthly/annual mixed-source reports use real001 configuration and002 durable totals."""

from uuid import UUID
from io import BytesIO
import pytest
from pypdf import PdfReader
from sqlalchemy import select
from backend.tests.unit.consumption.test_validation import record
from backend.tests.unit.consumption.test_catalog import installation
from backend.tests.contract.consumption.test_reception_contract import publish
from backend.tests.integration.reports.test_snapshot_foundations import request_report
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.consumption.models import instant
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.reports.models import Capture

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "selection",
    [{"scale": "mensual", "year": 2025, "month": 12}, {"scale": "anual", "year": 2025}],
)
async def test_thirty_kwh_preserves_measured_and_calculated_segments(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    selection,
):
    """Ten physical plus twenty calculated kWh stays30 withCAT-03/05 provenance, never an invented physical tariff input."""
    env = costs_environment
    await publish(
        env["reception"],
        [record(category_id="CAT-01", source_id=UUID(int=1), value="10")],
    )
    env["clock"].advance(3600)
    async with UnitOfWork(env["database"].sessions) as uow:
        await ConfigurationService(env["clock"], MeasurementStore()).apply(
            uow,
            building_id=env["building_id"],
            request=installation().model_copy(
                update={
                    "expected_revision": 1,
                    "effective_from": instant("2026-01-01T01:00:00Z"),
                }
            ),
            actor_ref="process:report_fixture",
        )
        await uow.commit()
    outcome = await publish(
        env["reception"],
        [
            record(
                category_id="CAT-03",
                source_id=UUID(int=3),
                value="8",
                start="2026-01-01T01:00:00Z",
                end="2026-01-01T02:00:00Z",
            ),
            record(
                category_id="CAT-05",
                source_id=UUID(int=5),
                value="12",
                start="2026-01-01T01:00:00Z",
                end="2026-01-01T02:00:00Z",
            ),
        ],
    )
    assert all(r.status == "accepted" for r in outcome.results)
    identifier, _, status = await request_report(
        costs_client, account_factory, session_factory, identity_settings, selection
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        capture = await uow.session.scalar(
            select(Capture).where(Capture.request_id == identifier)
        )
        row = capture.data["energy_rows"][0]
        assert row["energy_kwh"] == "30" and row["source_mode"] == "mixed"
        assert row["provenance_segments"][-1]["base_categories"] == ["CAT-03", "CAT-05"]
    text = (
        PdfReader(BytesIO((await costs_client.get(status["download_path"])).content))
        .pages[0]
        .extract_text()
    )
    assert (
        "30" in text
        and "Origen mixto" in text
        and "CAT-03/" in text
        and "CAT-05/" in text
    )


@pytest.mark.parametrize("calculated", [False, True])
async def test_same_mode_source_or_basis_changes_remain_visible(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    calculated,
):
    """Changing a physical source or a calculated basis preserves both segments and their exact30kWh total."""
    env = costs_environment

    async def configure(config, revision):
        """Use001's actual mutation coordinator and002's bounds, never inject provenance rows."""
        async with UnitOfWork(env["database"].sessions) as uow:
            await ConfigurationService(env["clock"], MeasurementStore()).apply(
                uow,
                building_id=env["building_id"],
                request=config.model_copy(
                    update={
                        "expected_revision": revision,
                        "effective_from": env["clock"].now(),
                    }
                ),
                actor_ref="process:report_fixture",
            )
            await uow.commit()

    if calculated:
        await configure(installation(), 1)
        await publish(
            env["reception"],
            [
                record(category_id="CAT-03", source_id=UUID(int=3), value="8"),
                record(category_id="CAT-05", source_id=UUID(int=5), value="12"),
            ],
        )
    else:
        await publish(
            env["reception"],
            [record(category_id="CAT-01", source_id=UUID(int=1), value="10")],
        )
    env["clock"].advance(3600)
    await configure(
        installation((3,))
        if calculated
        else installation(tuple(range(1, 8)), **{"1": UUID(int=11)}),
        2 if calculated else 1,
    )
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-03" if calculated else "CAT-01",
                source_id=UUID(int=3 if calculated else 11),
                value="10" if calculated else "20",
                start="2026-01-01T01:00:00Z",
                end="2026-01-01T02:00:00Z",
            )
        ],
    )
    _, _, status = await request_report(
        costs_client,
        account_factory,
        session_factory,
        identity_settings,
        {"scale": "mensual", "year": 2025, "month": 12},
    )
    text = (
        PdfReader(BytesIO((await costs_client.get(status["download_path"])).content))
        .pages[0]
        .extract_text()
    )
    assert "30" in text and "revisión 2" in text and "revisión 1" in text
    assert (
        ("CAT-05/" in text)
        if calculated
        else (str(UUID(int=1)) in text and str(UUID(int=11)) in text)
    )


async def test_configuration_crossing_is_nonnumeric_not_zero(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """A calculated interval crossing a real basis change retains its producer diagnostic and no fabricated energy."""
    env = costs_environment
    async with UnitOfWork(env["database"].sessions) as uow:
        await ConfigurationService(env["clock"], MeasurementStore()).apply(
            uow,
            building_id=env["building_id"],
            request=installation().model_copy(
                update={"expected_revision": 1, "effective_from": None}
            ),
            actor_ref="process:report_fixture",
        )
        await uow.commit()
    env["clock"].advance(3600)
    async with UnitOfWork(env["database"].sessions) as uow:
        await ConfigurationService(env["clock"], MeasurementStore()).apply(
            uow,
            building_id=env["building_id"],
            request=installation((3,)).model_copy(
                update={"expected_revision": 2, "effective_from": None}
            ),
            actor_ref="process:report_fixture",
        )
        await uow.commit()
    await publish(
        env["reception"],
        [
            record(
                category_id="CAT-03",
                source_id=UUID(int=3),
                value="10",
                start="2026-01-01T00:30:00Z",
                end="2026-01-01T01:30:00Z",
            )
        ],
    )
    rid, _, status = await request_report(
        costs_client,
        account_factory,
        session_factory,
        identity_settings,
        {"scale": "mensual", "year": 2025, "month": 12},
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        capture = await uow.session.scalar(
            select(Capture).where(Capture.request_id == rid)
        )
        row = capture.data["energy_rows"][0]
        assert row["energy_kwh"] is None
        assert "calculation_configuration_changed" in row["reason_codes"]
    text = (
        PdfReader(BytesIO((await costs_client.get(status["download_path"])).content))
        .pages[0]
        .extract_text()
    )
    assert "sin valor numérico" in text


async def test_calculated_general_cannot_be_presented_as_complete_physical_cost(
    costs_client, costs_environment, account_factory, session_factory, identity_settings
):
    """A real004 calculation over calculatedCAT-01 retains its noncomplete state in the PDF financial capture."""
    from backend.tests.costs_fixtures import seed_supply
    from backend.tests.contract.costs.test_calculations_api import authenticate

    env = costs_environment
    async with UnitOfWork(env["database"].sessions) as uow:
        await ConfigurationService(env["clock"], MeasurementStore()).apply(
            uow,
            building_id=env["building_id"],
            request=installation().model_copy(
                update={"expected_revision": 1, "effective_from": None}
            ),
            actor_ref="process:report_fixture",
        )
        await uow.commit()
    await publish(
        env["reception"],
        [
            record(category_id="CAT-03", source_id=UUID(int=3), value="8"),
            record(category_id="CAT-05", source_id=UUID(int=5), value="12"),
        ],
    )
    env["clock"].advance(7200)
    supply = await seed_supply(env["database"], env["clock"])
    headers = await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    result = await costs_client.post(
        "/api/v1/costs/calculations",
        json=dict(
            supply_id=str(supply.id),
            start_at="2026-01-01T00:00:00Z",
            end_at="2026-01-01T01:00:00Z",
            timezone="America/Santiago",
            boundary_criterion="synthetic:exact",
        ),
        headers=headers,
    )
    assert result.status_code == 201, result.text
    assert result.json()["complete_total"] is None
    rid, _, status = await request_report(
        costs_client,
        account_factory,
        session_factory,
        identity_settings,
        {"scale": "mensual", "year": 2025, "month": 12},
    )
    async with UnitOfWork(env["database"].sessions) as uow:
        captured = await uow.session.scalar(
            select(Capture).where(Capture.request_id == rid)
        )
        assert captured.data["energy_rows"][0]["energy_kwh"] == "20"
        assert (
            captured.data["financial_snapshot"]["cycles"][0]["calculation"][
                "complete_total"
            ]
            is None
        )
    assert (await costs_client.get(status["download_path"])).status_code == 200
