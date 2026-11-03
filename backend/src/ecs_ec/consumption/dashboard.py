"""Daily read projection: exact sums and disjoint coverage, no storage writes or forecasts."""

from datetime import timedelta

from ecs_ec.consumption.aggregates import energy_quanta, quanta_energy
from ecs_ec.consumption.calendar import containing_block, duration_us
from ecs_ec.consumption.catalog import CATEGORIES
from ecs_ec.consumption.catalog_storage import configuration_segments
from ecs_ec.consumption.periods import timestamp
from ecs_ec.consumption.queries import decimal_text
from ecs_ec.core.unit_of_work import UnitOfWork
from sqlalchemy import text


def summarize(rows, start, end):
    """Sum only fully contained disjoint rows; keep missing energy null and coverage exact.

    Integer quanta preserve every decimal. Reject overlapping evidence rather than
    double counting. The caller's end is captured now, never the future end of day.
    """
    selected = sorted((r for r in rows if start <= r.start < r.end <= end), key=lambda r: r.start)
    if any(a.end > b.start for a, b in zip(selected, selected[1:])):
        raise ValueError('overlapping_dashboard_evidence')
    covered = sum(duration_us(r.start, r.end) for r in selected)
    total = sum(energy_quanta(r.energy_kwh) for r in selected)
    elapsed = duration_us(start, end) if start < end else 0
    # Floor the displayed percentage so a genuine small gap cannot round to100.
    hundredths = min(10000, covered * 10000 // elapsed) if elapsed else 0
    return dict(energy_kwh=decimal_text(quanta_energy(total)) if selected else None,
        coverage_percent=f'{hundredths // 100}.{hundredths % 100:02d}',
        covered_duration_us=str(covered), elapsed_duration_us=str(elapsed),
        last_reading_at=selected[-1].end if selected else None)


async def read_dashboard(service):
    """Read all seven categories in one authorized repeatable-read snapshot and cutoff.

    Fifteen-minute chart bins never prorate crossings. A shorter row may contribute
    wholly to a bin; its incomplete coverage stays explicit. Daily sums remain based
    on all contained measurements, even when a crossing cannot be charted at15min.
    """
    async with UnitOfWork(service.database.sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        building, revisions = await service._context(uow)
        cutoff = service.clock.now()
        day = containing_block(cutoff, 'day', building.timezone)
        categories, series, chart_excluded_count = [], [], 0
        for category in CATEGORIES:
            source = await service.source_status(category.id, cutoff_at=cutoff, unit_of_work=uow)
            segments = configuration_segments(tuple(r for r in revisions if r.recorded_at <= cutoff), category.id, day.start, cutoff) if day.start < cutoff else ()
            modes = {segment.source_mode for segment in segments}
            if modes:
                source['source_mode'] = next(iter(modes)) if len(modes) == 1 else 'mixed'
                source['base_categories'] = sorted({item for segment in segments for item in segment.base_categories})
            if day.start < cutoff:
                stored = await service.store.read_detail(service.building_id, category.id, day.start, cutoff, cutoff, uow)
                rows = stored.rows
                limited = bool(stored.diagnostics or stored.crossing_diagnostic_ids or stored.withdrawn_record_ids or stored.crossing_record_ids)
            else:
                rows, limited = (), False
            summary = summarize(rows, day.start, cutoff)
            if summary['last_reading_at'] is not None:
                summary['last_reading_at'] = timestamp(summary['last_reading_at'], building.timezone)
            categories.append(dict(id=category.id, name=category.name, source_mode=source['source_mode'],
                base_categories=source['base_categories'], **summary,
                state='no_meter' if source['source_mode'] == 'unavailable' and not rows else
                    'no_data' if not rows else 'incomplete' if limited or summary['covered_duration_us'] != summary['elapsed_duration_us'] else 'available'))
            if category.id == 'CAT-01':
                chart_rows = 0
                cursor = day.start
                while cursor + timedelta(minutes=15) <= cutoff:
                    end = cursor + timedelta(minutes=15)
                    bin_value = summarize(rows, cursor, end)
                    chart_rows += sum(cursor <= r.start < r.end <= end for r in rows)
                    series.append(dict(start=timestamp(cursor, building.timezone), end=timestamp(end, building.timezone),
                        energy_kwh=bin_value['energy_kwh'], coverage_percent=bin_value['coverage_percent']))
                    cursor = end
                chart_excluded_count = len(rows) - chart_rows
        return dict(timezone=building.timezone, cutoff_at=timestamp(cutoff, building.timezone),
            period=dict(start=timestamp(day.start, building.timezone), end=timestamp(day.end, building.timezone), timezone=building.timezone),
            categories=categories, series=series,
            chart_excluded_count=chart_excluded_count)
