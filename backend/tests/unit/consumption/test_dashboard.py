"""Exact daily and quarter-hour projections use source evidence, never synthetic zero or prorating."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
import pytest
from ecs_ec.consumption.dashboard import summarize
from ecs_ec.consumption.calendar import containing_block

START = datetime(2026, 1, 1, tzinfo=UTC)


def row(start=0, end=15, energy='1'):
    """Build a public synthetic contained interval, with no database or hidden installation data."""
    return SimpleNamespace(start=START + timedelta(minutes=start), end=START + timedelta(minutes=end), energy_kwh=Decimal(energy))


def test_zero_absence_and_partial_coverage():
    """Zero is present; a missing interval is null; elapsed coverage does not include future day hours."""
    assert summarize([], START, START + timedelta(minutes=15))['energy_kwh'] is None
    value = summarize([row(energy='0')], START, START + timedelta(minutes=30))
    assert value['energy_kwh'] == '0'
    assert value['coverage_percent'] == '50.00'
    assert value['last_reading_at'] == START + timedelta(minutes=15)


def test_exact_large_sum_and_no_prorating():
    """Summation survives Decimal's ambient28 digits; a crossing contributes only to the daily scope."""
    records = [row(0, 15, '999999999999999999999999999999.999999999999999'), row(15, 30, '0.000000000000001')]
    assert summarize(records, START, START + timedelta(minutes=30))['energy_kwh'] == '1000000000000000000000000000000'
    crossing = row(0, 60, '4')
    assert summarize([crossing], START, START + timedelta(minutes=15))['energy_kwh'] is None
    assert summarize([crossing], START, START + timedelta(hours=1))['energy_kwh'] == '4'


def test_rejects_overlapping_evidence_and_uses_real_day_duration():
    """Never double-count overlaps; Santiago DST dates retain actual23/25-hour bounds."""
    with pytest.raises(ValueError, match='overlapping'):
        summarize([row(), row(10, 20)], START, START + timedelta(minutes=30))
    short_day = containing_block(datetime(2026, 9, 6, 12, tzinfo=UTC), 'day', 'America/Santiago')
    assert short_day.end - short_day.start == timedelta(hours=23)


@pytest.mark.asyncio
async def test_daily_capture_shares_cutoff_and_never_adds_partial_categories(monkeypatch):
    """A single read transaction feeds seven categories; future bins and crossed intervals are absent."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock
    import ecs_ec.consumption.dashboard as module
    from ecs_ec.consumption.schemas import DashboardView
    cutoff = START + timedelta(hours=14, minutes=32)
    session = SimpleNamespace(execute=AsyncMock())
    uow = SimpleNamespace(session=session)

    @asynccontextmanager
    async def capture(_):
        """Provide one read-only synthetic UoW, retaining the actual service orchestration."""
        yield uow

    async def read(building_id, category_id, start, end, at, transaction):
        """Each category reads at the exact same cutoff and transaction; no mocked business sums."""
        assert at == end == cutoff and transaction is uow
        records = [row(0, 15, '1'), row(15, 30, '0'), row(30, 90, '4')] if category_id == 'CAT-01' else [row(0, 15, '100')]
        return SimpleNamespace(rows=records, diagnostics=(), crossing_diagnostic_ids=(), withdrawn_record_ids=(), crossing_record_ids=())

    monkeypatch.setattr(module, 'UnitOfWork', capture)
    service = SimpleNamespace(database=SimpleNamespace(sessions=None), building_id='synthetic',
        clock=SimpleNamespace(now=lambda: cutoff), _context=AsyncMock(return_value=(SimpleNamespace(timezone='Etc/UTC'), ())),
        source_status=AsyncMock(side_effect=lambda *args, **kwargs: dict(source_mode='measured', base_categories=[])),
        store=SimpleNamespace(read_detail=read))
    data = DashboardView.model_validate(await module.read_dashboard(service))
    assert data.categories[0].energy_kwh == '5'  # Never605 from six100kWh partials.
    assert data.categories[1].energy_kwh == '100'
    assert data.categories[0].series == data.series
    assert data.categories[0].chart_excluded_count == 1
    for category in data.categories[1:]:
        assert len(category.series) == 58
        assert category.series[0].energy_kwh == '100'
        assert category.series[1].energy_kwh is None
        assert category.chart_excluded_count == 0
    assert data.coverage_end_at == '2026-01-01T14:30:00+00:00'
    assert data.categories[0].elapsed_duration_us == str(870 * 60 * 1000000)
    assert len(data.series) == 58
    assert data.series[1].energy_kwh == '0'
    assert data.series[2].energy_kwh is None  # One-hour crossing is not divided into fake quarter-hours.
    assert data.chart_excluded_count == 1
    assert data.series[-1].end == '2026-01-01T14:30:00+00:00'
    session.execute.assert_awaited_once()


def test_closed_quarters_are_stable_between_refreshes_without_hiding_missing_data():
    """Full evidence through18:15 stays100% at18:20/18:29; a missing closed quarter stays partial."""
    records = [row(i, i+15) for i in range(0, 18*60+15, 15)]
    closed = START + timedelta(hours=18, minutes=15)
    first = summarize(records, START, START+timedelta(hours=18, minutes=20), coverage_end=closed)
    later = summarize(records, START, START+timedelta(hours=18, minutes=29, seconds=59), coverage_end=closed)
    assert first == later
    assert first['coverage_percent'] == '100.00'
    next_close = START + timedelta(hours=18, minutes=30)
    missing = summarize(records, START, next_close, coverage_end=next_close)
    assert Decimal(missing['coverage_percent']) < 100
    records.append(row(18*60+15, 18*60+30))
    assert summarize(records, START, next_close, coverage_end=next_close)['coverage_percent'] == '100.00'
    assert Decimal(summarize(records[1:], START, next_close, coverage_end=next_close)['coverage_percent']) < 100


def test_no_closed_quarters_and_crossing_evidence_preserve_exact_energy():
    """Before00:15 coverage has no denominator; clipping covered time never prorates energy."""
    early = summarize([], START, START+timedelta(minutes=7), coverage_end=START)
    assert early['elapsed_duration_us'] == '0'
    assert early['energy_kwh'] is None
    crossing = summarize([row(0, 20, '4')], START, START+timedelta(minutes=23), coverage_end=START+timedelta(minutes=15))
    assert crossing['energy_kwh'] == '4'
    assert crossing['coverage_percent'] == '100.00'
