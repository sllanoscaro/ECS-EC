"""Strict005 synthetic snapshots for pure composition tests, never used as API acceptance outputs."""
from uuid import UUID
from ecs_ec.consumption.models import instant
from ecs_ec.costs.schemas import CostsSnapshot
from ecs_ec.reports.schemas import Snapshot,EnergyRow


def snapshot(*,scale='anual',value='0',building_name='Edificio de referencia',category_name=None):
    """Provide seven schema-valid rows and an empty typed financial scope for renderer boundary tests."""
    start=instant('2025-01-01T03:00:00Z');end=instant('2026-01-01T03:00:00Z');cutoff=end
    financial=CostsSnapshot(building_id=UUID(int=99),supply_id=None,start=start,end=end,timezone='America/Santiago',cutoff_at=cutoff,
        cycles=(),available_totals=(),comparison_totals=(),complete_cycle_count=0,partial_cycle_count=0,uncalculable_cycle_count=0,failed_cycle_count=0,reason_codes=('no_closed_cycles',))
    return Snapshot(building_id=UUID(int=99),building_name=building_name,scale=scale,start=start,end=end,timezone='America/Santiago',cutoff_at=cutoff,provisional=False,
        energy_rows=tuple(EnergyRow(category_id=f'CAT-{i:02}',name=category_name or f'Categoría {i}',energy_kwh=value if i<4 else None,coverage_percent='25',state='incomplete' if i<4 else 'no_meter',source_mode='measured' if i<4 else 'unavailable',provenance_segments=()) for i in range(1,8)),
        chart_blocks=(),financial_snapshot=financial,source_revisions={},source_refs=(),quality_notes=(),provenance=())
