"""005 recognizes trusted003 simulation metadata, with the same temporal cutoff as functional sources."""

from uuid import UUID
import pytest
from sqlalchemy import text
from backend.tests.contract.costs.test_calculations_api import prepared, authenticate
from ecs_ec.acquisition.config import install_binding, AcquisitionSettings
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import instant
from ecs_ec.reports.snapshots import capture_snapshot

pytestmark = pytest.mark.integration


async def test_trusted_provenance_cannot_cross_the_snapshot_cutoff(
    costs_client,
    costs_environment,
    account_factory,
    session_factory,
    identity_settings,
    tmp_path,
):
    """New003 metadata is visible to a fresh report, never to an earlier cutoff or from private/native filenames."""
    env = costs_environment
    await prepared(env)
    await authenticate(
        costs_client, account_factory, session_factory, identity_settings
    )
    service = costs_client._transport.app.state.reports
    principal = await service.identity.resolve_session(
        costs_client.cookies["ecs_ec_session"]
    )
    cutoff = env["clock"].now()
    env["clock"].advance(60)
    settings = AcquisitionSettings(
        _env_file=None,
        storage=tmp_path / "bytes",
        maintenance_processes="process:report_fixture",
    )
    await install_binding(
        env["database"],
        env["clock"],
        settings,
        "process:report_fixture",
        dict(
            id=str(UUID(int=3003)),
            revision=1,
            building_id=str(env["building_id"]),
            username="pas600",
            publisher_serial="SIMULATED-PAS600-001",
            publisher_remote_id="urn:dev:cer:1111111111111111111111111111111111111111",
            timezone="America/Santiago",
            channels=[
                dict(
                    source_id=str(UUID(int=1)),
                    category_id="CAT-01",
                    device_local_id="modbus:1_mb_1",
                    reduced_id="1_mb",
                    device_name="iEM3150 CAT01",
                    csv_topic_id="modbus:1_mb_EaImport1",
                    json_value_item_id="modbus:1_mb_EaImport1",
                )
            ],
        ),
    )
    snapshots = []
    for at in (cutoff, env["clock"].now()):
        async with UnitOfWork(env["database"].sessions) as uow:
            await uow.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            snapshots.append(
                await capture_snapshot(
                    identity=service.identity,
                    consumption=service.consumption,
                    costs=service.costs,
                    building_id=env["building_id"],
                    start=instant("2025-01-01T03:00:00Z"),
                    end=instant("2026-01-01T03:00:00Z"),
                    scale="anual",
                    cutoff_at=at,
                    principal=principal,
                    unit_of_work=uow,
                )
            )
    assert snapshots[0].provenance == ()
    assert "simulado" in snapshots[1].provenance[0]
