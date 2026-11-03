"""005 capture adapter over real002/004 readers; no energy or tariff calculations.

This captures raw producer evidence, not the final report_snapshot projection.
The caller owns persistence and must commit a typed immutable projection before
rendering. The transaction is never retained by a renderer or executor.
"""

from sqlalchemy import text

from ecs_ec.reports.ports import ConsumptionPort, CostsPort, IdentityPort

# Calendar labels belong to005; producer granularities belong to002.
GRANULARITIES = {'diario': ('day', 'hour'), 'mensual': ('month', 'day'), 'anual': ('year', 'month')}


async def capture_sources(*, identity: IdentityPort, consumption: ConsumptionPort,
                          costs: CostsPort, building_id, start, end, scale,
                          cutoff_at, principal, unit_of_work):
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
    isolation = await unit_of_work.session.scalar(text('SHOW transaction_isolation'))
    if isolation not in {'repeatable read', 'serializable'}:
        raise ValueError('snapshot_isolation_required')
    totals = await consumption.read_report_snapshot(building_id, start, end, total_scale,
        cutoff_at, principal, unit_of_work=unit_of_work)
    chart = await consumption.read_report_snapshot(building_id, start, end, chart_scale,
        cutoff_at, principal, unit_of_work=unit_of_work)
    financial = await costs.read_snapshot(building_id, start, end, cutoff_at, principal,
        unit_of_work=unit_of_work)
    return dict(totals=totals, chart=chart, financial=financial)
