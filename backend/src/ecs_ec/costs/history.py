"""004 coherent cycle selection and basis-separated financial aggregates; no recalculation or older-pair fallback."""

from decimal import Decimal, localcontext
from sqlalchemy import select

from ecs_ec.costs.models import Comparison, Calculation
from ecs_ec.costs.repository import selected_pair
from ecs_ec.costs.schemas import CycleDetail
from ecs_ec.costs.money import number, decimal_text
from ecs_ec.costs.comparison import percentage


async def cycle_view(service, uow, cycle, cutoff):
    """Detach the selected calculation, bill and exact comparison plus stable historical references."""
    calculation, bill, comparison, status = await selected_pair(uow, cycle.id, cutoff)
    old = (await uow.session.scalars(select(Comparison).join(Calculation).where(
        Calculation.cycle_id == cycle.id, Comparison.created_at <= cutoff).order_by(Comparison.created_at, Comparison.id))).all()
    value = dict(id=cycle.id, supply_id=cycle.supply_id, start_at=cycle.start_at, end_at=cycle.end_at, timezone=cycle.timezone,
        calculation=await service._calculation_view(uow, calculation) if calculation else None,
        bill=service._bill_view(bill) if bill else None, comparison=service._comparison_view(comparison) if comparison else None,
        comparison_status=status, delta_amount=comparison.data['delta_amount'] if comparison else None,
        delta_percent=comparison.data['delta_percent'] if comparison else None,
        historical_comparisons=[dict(id=row.id, calculation_id=row.calculation_id, bill_revision_id=row.bill_revision_id, revision=row.revision) for row in old])
    return CycleDetail.model_validate(value)


def aggregates(cycles):
    """Sum available components and exact comparable pairs only within currency/concept/tax-basis groups."""
    available, comparable = {}, {}
    with localcontext() as context:
        context.prec = 256
        for cycle in cycles:
            if cycle.calculation:
                for component in cycle.calculation.components:
                    if component.presented_amount is not None:
                        key = (cycle.calculation.currency, component.code, component.tax_basis)
                        available[key] = available.get(key, Decimal(0)) + number(component.presented_amount)
            if cycle.comparison_status == 'available' and cycle.comparison:
                for pair in cycle.comparison.pairs:
                    key = (cycle.comparison.currency, pair.code, pair.tax_basis)
                    calculated, billed, count = comparable.get(key, (Decimal(0), Decimal(0), 0))
                    comparable[key] = (calculated + number(pair.calculated_amount), billed + number(pair.billed_amount), count + 1)
        totals = [dict(currency=key[0], code=key[1], tax_basis=key[2], amount=decimal_text(value)) for key, value in sorted(available.items())]
        pairs = [dict(currency=key[0], code=key[1], tax_basis=key[2], calculated=decimal_text(calculated), billed=decimal_text(billed),
            delta_amount=decimal_text(calculated-billed), delta_percent=percentage(calculated-billed, billed), cycle_count=count)
            for key, (calculated, billed, count) in sorted(comparable.items())]
        return totals, pairs
