"""005 capture adapter over real002/004 readers; no energy or tariff calculations.

This captures raw producer evidence, not the final report_snapshot projection.
The caller owns persistence and must commit a typed immutable projection before
rendering. The transaction is never retained by a renderer or executor.
"""

from sqlalchemy import text

from ecs_ec.reports.ports import ConsumptionPort, CostsPort, IdentityPort

# Calendar labels belong to005; producer granularities belong to002.
GRANULARITIES = {
    "diario": ("day", "hour"),
    "mensual": ("month", "day"),
    "anual": ("year", "month"),
}


async def capture_sources(
    *,
    identity: IdentityPort,
    consumption: ConsumptionPort,
    costs: CostsPort,
    building_id,
    start,
    end,
    scale,
    cutoff_at,
    principal,
    unit_of_work,
):
    """Copy total, chart and financial evidence in one already-open repeatable transaction.

    Reject unsupported isolation before reading data. Exceptions propagate to the
    future admission service, which owns durable failure handling. Authorize before
    any read; do not infer generation permission from read permission.
    Total and chart use separate producer queries so retired detail cannot replace
    a retained yearly total. No flattening, rounding or provenance reconstruction
    occurs here. Returned Pydantic objects remain typed producer outputs.
    """
    identity.require_report_access(principal, building_id)
    total_scale, chart_scale = GRANULARITIES[scale]
    isolation = await unit_of_work.session.scalar(text("SHOW transaction_isolation"))
    if isolation not in {"repeatable read", "serializable"}:
        raise ValueError("snapshot_isolation_required")
    totals = await consumption.read_report_snapshot(
        building_id,
        start,
        end,
        total_scale,
        cutoff_at,
        principal,
        unit_of_work=unit_of_work,
    )
    chart = await consumption.read_report_snapshot(
        building_id,
        start,
        end,
        chart_scale,
        cutoff_at,
        principal,
        unit_of_work=unit_of_work,
    )
    financial = await costs.read_snapshot(
        building_id, start, end, cutoff_at, principal, unit_of_work=unit_of_work
    )
    return dict(totals=totals, chart=chart, financial=financial)


async def capture_snapshot(
    *,
    identity,
    consumption,
    costs,
    building_id,
    start,
    end,
    scale,
    cutoff_at,
    principal,
    unit_of_work,
):
    """Copy typed seven-row aggregate/financial evidence into005 without recomputing source provenance or tariffs."""
    from decimal import Decimal, localcontext
    from sqlalchemy import select
    from ecs_ec.consumption.catalog_storage import BuildingRow
    from ecs_ec.reports.schemas import Snapshot, EnergyRow

    raw = await capture_sources(
        identity=identity,
        consumption=consumption,
        costs=costs,
        building_id=building_id,
        start=start,
        end=end,
        scale=scale,
        cutoff_at=cutoff_at,
        principal=principal,
        unit_of_work=unit_of_work,
    )
    building = await unit_of_work.session.get(BuildingRow, building_id)
    rows = []
    notes = []
    refs = []
    for item in raw["totals"]["categories"]:
        aggregate = item["aggregates"]
        blocks = aggregate.blocks
        # Blocks are nonoverlapping disjoint buckets returned by002, never reconstructed from detail.
        with localcontext() as context:
            context.prec = 200
            values = [Decimal(b.energy_kwh) for b in blocks if b.energy_kwh is not None]
            energy = format(sum(values, Decimal(0)), "f") if values else None
            covered = sum(int(b.covered_duration_us) for b in blocks)
            duration = int((end - start).total_seconds() * 1000000)
            coverage = format(Decimal(100) * covered / Decimal(duration), "f")
        reason_codes = tuple(
            sorted(
                {w.code for w in aggregate.warnings}
                | {d.reason_code for d in aggregate.diagnostics}
            )
        )
        notes.extend(f"{item['category']['id']}: {r}" for r in reason_codes)
        refs.extend(str(r.record_id) for r in item["detail"].rows)
        rows.append(
            EnergyRow(
                category_id=item["category"]["id"],
                name=item["category"]["name"],
                energy_kwh=energy,
                coverage_percent=coverage,
                state=aggregate.state,
                source_mode=aggregate.source_mode,
                provenance_segments=item["provenance_segments"],
                reason_codes=reason_codes,
            )
        )
    chart = raw["chart"]["categories"][0]["aggregates"]
    provenance = []
    # Binding metadata is already trusted configuration003, never inferred from native filenames or private oracle files.
    from ecs_ec.acquisition.models import AcquisitionBinding

    bindings = (
        await unit_of_work.session.scalars(
            select(AcquisitionBinding).where(
                AcquisitionBinding.building_id == building_id,
                AcquisitionBinding.recorded_at <= cutoff_at,
            )
        )
    ).all()
    if any(
        c.get("provenance") == "synthetic"
        for b in bindings
        for c in b.data.get("channels", [])
    ):
        provenance.append(
            "Origen simulado identificado en la configuración de fuentes."
        )
    return Snapshot(
        schema_version=1,
        building_id=building_id,
        building_name=building.name,
        scale=scale,
        start=start,
        end=end,
        timezone=building.timezone,
        cutoff_at=cutoff_at,
        provisional=end > cutoff_at,
        energy_rows=rows,
        chart_blocks=chart.blocks,
        financial_snapshot=raw["financial"],
        source_revisions={
            i["category"]["id"]: i["evidence_revision"]
            for i in raw["totals"]["categories"]
        },
        source_refs=tuple(sorted(set(refs))),
        quality_notes=tuple(sorted(set(notes))),
        provenance=tuple(provenance),
    )
