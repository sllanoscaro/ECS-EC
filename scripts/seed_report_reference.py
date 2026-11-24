"""Prepare synthetic005 real-source references in an EMPTY separate *_test database.

Uses the guarded004/006 seed and actual001 configuration/002 reception. It never
ships in the runtime image, generates pre-recorded PDFs or overwrites an installation.
March2026 contains10 measured plus20 calculated kWh. The1000physical kWh belong
to daily2025-12-31/monthly2025-12/annual2025 in Santiago. Optional --financial
creates a selected pending pair through004; --extremes adds April2026 intervals.
"""

import argparse, asyncio, os, sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed_costs_reference import seed as seed_costs
from backend.tests.unit.consumption.test_catalog import installation
from ecs_ec.core.database import Database
from ecs_ec.core.clock import FrozenClock
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.reception import Reception
from ecs_ec.consumption.configuration import ConfigurationService
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.consumption.models import instant


async def seed(password_file, *, extremes=False):
    """Validate/provision through the existing guarded seed before appending disjoint mixed-source intervals."""
    clock = FrozenClock(instant("2026-01-01T02:00:00Z"))
    await seed_costs(
        password_file,
        clock=clock,
        building_name=("Edificio de referencia eléctrica " + "áreas comunes " * 7)[:120]
        if extremes
        else "Synthetic004 building",
    )
    database = Database(os.environ["TEST_DATABASE_URL"])
    building = UUID(int=99)
    receiver = Reception(
        database, clock, authorized_processes={"process:reports_fixture": {building}}
    )

    async def publish(rows):
        """Keep all synthetic measurements on the real002 validation/incorporation path."""
        result = await receiver.accept(
            uuid4(),
            building,
            "synthetic005",
            "process:reports_fixture",
            rows,
            "synthetic:005",
        )
        if any(r.status != "accepted" for r in result.results):
            raise ValueError("synthetic_report_reception_failed")

    def row(category, value, start, end):
        """Declare bounded synthetic native inputs, never technical envelopes or credentials."""
        return dict(
            building_id=building,
            category_id=f"CAT-{category:02}",
            source_id=UUID(int=category),
            value=value,
            unit="kWh",
            start=start,
            end=end,
            source_evidence_ref="synthetic:005:measurement",
            correlation_ref="synthetic:005",
        )

    try:
        clock.advance((instant("2026-03-01T05:00:00Z") - clock.now()).total_seconds())
        await publish([row(1, "10", "2026-03-01T04:00:00Z", "2026-03-01T05:00:00Z")])
        async with UnitOfWork(database.sessions) as uow:
            await ConfigurationService(clock, MeasurementStore()).apply(
                uow,
                building_id=building,
                request=installation().model_copy(
                    update={
                        "expected_revision": 1,
                        "effective_from": instant("2026-03-01T05:00:00Z"),
                    }
                ),
                actor_ref="process:reports_fixture",
            )
            await uow.commit()
        await publish(
            [
                row(3, "8", "2026-03-01T05:00:00Z", "2026-03-01T06:00:00Z"),
                row(5, "12", "2026-03-01T05:00:00Z", "2026-03-01T06:00:00Z"),
            ]
        )
        clock.advance(900)
        from ecs_ec.consumption.pending_totals import PendingTotals

        await PendingTotals(database, clock).run_due(building)
        if extremes:
            clock.advance(
                (instant("2026-04-01T06:00:00Z") - clock.now()).total_seconds()
            )
            await publish(
                [
                    row(3, "0", "2026-04-01T04:00:00Z", "2026-04-01T05:00:00Z"),
                    row(5, "0.000001", "2026-04-01T04:00:00Z", "2026-04-01T05:00:00Z"),
                    row(
                        3,
                        "1000000000000",
                        "2026-04-01T05:00:00Z",
                        "2026-04-01T06:00:00Z",
                    ),
                    row(5, "0", "2026-04-01T05:00:00Z", "2026-04-01T06:00:00Z"),
                ]
            )
            clock.advance(900)
            await PendingTotals(database, clock).run_due(building)
            print(
                "Synthetic005 extremes added: April2026 contains0,0.000001 and1000000000000kWh through real002; building label120characters. March mixed30 stays unchanged."
            )
        await validate_reference_totals(database, clock, building, extremes)
        print(
            "Synthetic005 references ready: daily2025-12-31/monthly2025-12=1000physical; monthly2026-03=30mixed(CAT-03/05); annual2026=30mixed without --extremes; April extrema increase that annual total. Financial revision/extreme cases: documented executable integration fixtures."
        )

    finally:
        await database.close()


def main():
    """Accept a protected fixture credential file only; inherited guards reject nonempty/production databases."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password-file", required=True)
    parser.add_argument(
        "--financial",
        action="store_true",
        help="Also prepare real C1/B1/K1 followed by B2 pending; requires ordinary identity test configuration",
    )
    parser.add_argument(
        "--extremes",
        action="store_true",
        help="Add actual002 zero/small/large reference intervals and a120-character building label",
    )
    options = parser.parse_args()
    asyncio.run(seed(options.password_file, extremes=options.extremes))
    if options.financial:
        asyncio.run(seed_financial_reference(options.password_file))


async def validate_reference_totals(database, clock, building, extremes):
    """Read actual002 aggregates and reject a seed whose known totals were not durably incorporated."""
    from ecs_ec.consumption.queries import Consumption
    from ecs_ec.consumption.ports import AggregateSelection
    from ecs_ec.reports.calendar import window
    from ecs_ec.reports.schemas import Selection
    from decimal import Decimal

    service = Consumption(database, clock, building, MeasurementStore())
    for year, month, expected in [(2025, 12, "1000"), (2026, 3, "30")] + (
        [(2026, 4, "1000000000000.000001")] if extremes else []
    ):
        start, end = window(
            Selection(scale="mensual", year=year, month=month),
            "America/Santiago",
            clock.now(),
        )
        result = await service.query_aggregates(
            AggregateSelection(
                building_id=building,
                category_id="CAT-01",
                granularity="month",
                start=start,
                end=end,
                timezone="America/Santiago",
            ),
            None,
        )
        if len(result.blocks) != 1 or Decimal(result.blocks[0].energy_kwh) != Decimal(
            expected
        ):
            raise ValueError("synthetic_reference_total_mismatch")


async def seed_financial_reference(password_file):
    """Append C1/B1/K1 thenB2 through real006/004 HTTP, leaving the selected pair explicitly pending.

    Called only after this script's guarded empty-database provisioning. Credentials
    remain in the protected input file; no fixture endpoint or fabricated result is used.
    """
    import httpx
    from pydantic import SecretStr
    from ecs_ec.core.settings import Settings
    from ecs_ec.main import create_app
    from backend.tests.contract.costs.test_bills_comparisons_api import invoice

    settings = Settings().model_copy(
        update={
            "database_url": SecretStr(os.environ["TEST_DATABASE_URL"]),
            "identity_enabled": True,
        }
    )
    password = Path(password_file).read_text().removesuffix("\n")
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=settings.public_url
        ) as client:

            async def login(value):
                """Obtain ordinary preauth/session cookies and a CSRF-bound human principal."""
                preauth = (await client.get("/api/v1/auth/csrf")).json()
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin-active@example.test", "password": value},
                    headers={
                        "Origin": settings.public_url,
                        "X-CSRF-Token": preauth["csrf_token"],
                    },
                )
                if response.status_code != 200:
                    raise ValueError("synthetic_login_failed")
                return {
                    "Origin": settings.public_url,
                    "X-CSRF-Token": response.json()["csrf_token"],
                }

            headers = await login(password)
            changed = await client.post(
                "/api/v1/auth/password",
                json={
                    "current_password": password,
                    "new_password": password + " renewed",
                },
                headers=headers,
            )
            if changed.status_code != 204:
                raise ValueError("synthetic_renewal_failed")
            headers = await login(password + " renewed")
            supply = (await client.get("/api/v1/costs/supply")).json()

            async def post(path, body):
                """Require the real producer's committed response; never continue after a fixture mutation fails."""
                response = await client.post(
                    "/api/v1/costs/" + path,
                    json=body,
                    headers=headers | {"Idempotency-Key": uuid4().hex},
                )
                if response.status_code != 201:
                    raise ValueError("synthetic_financial_fixture_failed")
                return response

            body = {
                "supply_id": supply["id"],
                "start_at": "2026-01-01T00:00:00Z",
                "end_at": "2026-01-01T01:00:00Z",
                "timezone": "America/Santiago",
                "boundary_criterion": "synthetic:exact",
            }
            calculation = (await post("calculations", body)).json()
            first = await post("bills", invoice(body))
            bill = first.json()
            await post(
                "comparisons",
                {
                    "calculation_id": calculation["id"],
                    "bill_revision_id": bill["bill_revision_id"],
                },
            )
            corrected = await client.put(
                "/api/v1/costs/bills/" + bill["id"],
                json=invoice(body, amount="90000"),
                headers=headers
                | {"Idempotency-Key": uuid4().hex, "If-Match": first.headers["etag"]},
            )
            if corrected.status_code != 200:
                raise ValueError("synthetic_bill_correction_failed")
            cycles = (await client.get("/api/v1/costs/cycles")).json()["items"]
            if not any(
                c["comparison_status"] == "missing_for_selected_revisions"
                for c in cycles
            ):
                raise ValueError("synthetic_pair_not_pending")
            print(
                "Synthetic005 financial reference ready: C1/B1/K1 retained; selectedC1/B2 pending. Admin fixture renewed; operator keeps its initial renewal requirement."
            )


if __name__ == "__main__":
    main()
