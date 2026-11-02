"""Synchronous exact aggregate writer; each immutable record contributes at most once per contained level."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from ecs_ec.consumption.calendar import containing_block, duration_us
from ecs_ec.consumption.models import AggregateContribution, ConsumptionAggregate
from ecs_ec.core.retention import anniversary


def energy_quanta(value):
    """Convert nonnegative Decimal kWh to integer10^-15 units without ambient-context arithmetic."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0: raise ValueError('invalid_energy')
    sign, digits, exponent = value.as_tuple()
    coefficient = int(''.join(map(str, digits)))
    exponent += 15
    if exponent >= 0: return coefficient * 10**exponent
    divisor = 10**(-exponent)
    if coefficient % divisor: raise ValueError('energy_below_quantum')
    return coefficient // divisor


def quanta_energy(coefficient):
    """Reconstruct exact Decimal through digits/scale, even for aggregates exceeding precision50."""
    if not isinstance(coefficient, int) or coefficient < 0: raise ValueError('invalid_quanta')
    if len(str(coefficient)) > 131072: raise ValueError('aggregate_out_of_numeric_range')
    return Decimal((0, tuple(map(int, str(coefficient))), -15))


async def contribute(uow, record, now):
    """Flush all fully containing levels and unique snapshots under caller's shared locks; never commit.

    Exclusion makes interval durations disjoint. Sum integer quanta/durations directly,
    never roll up hourly buckets, prorate crossings or subtract retired detail.
    """
    for granularity in ('hour', 'day', 'month', 'year'):
        block = containing_block(record.start, granularity, record.retention_timezone)
        if record.end > block.end: continue
        existing = (await uow.session.scalars(select(ConsumptionAggregate).where(
            ConsumptionAggregate.building_id == record.building_id,
            ConsumptionAggregate.category_id == record.category_id,
            ConsumptionAggregate.granularity == granularity,
            ConsumptionAggregate.timezone == block.timezone,
            ConsumptionAggregate.start < block.end, ConsumptionAggregate.end > block.start))).all()
        if any(row.start != block.start or row.end != block.end for row in existing):
            raise ValueError('tzdata_reconciliation_required')
        aggregate = existing[0] if existing else None
        if aggregate and await uow.session.get(AggregateContribution, (aggregate.id, record.id)): continue
        deadline = anniversary(now, block.timezone)
        if aggregate is None:
            aggregate = ConsumptionAggregate(id=uuid4(), building_id=record.building_id, category_id=record.category_id,
                granularity=granularity, start=block.start, end=block.end, timezone=block.timezone,
                start_offset=block.start_offset, end_offset=block.end_offset, tzdata_version=block.tzdata_version,
                energy_quanta=int(record.energy_quanta), covered_duration_us=duration_us(record.start, record.end),
                contribution_count=1, created_at=now, last_new_data_at=now, revision=1, retain_until=deadline)
            uow.session.add(aggregate)
        else:
            # Numeric is read as Decimal, but addition always happens as Python int.
            total = int(aggregate.energy_quanta) + int(record.energy_quanta)
            quanta_energy(total)  # Check PostgreSQL's unconstrained numeric digit ceiling before flush.
            aggregate.energy_quanta = total
            aggregate.covered_duration_us = int(aggregate.covered_duration_us) + duration_us(record.start, record.end)
            aggregate.contribution_count += 1
            aggregate.revision += 1
            aggregate.last_new_data_at = now
            aggregate.retain_until = max(aggregate.retain_until, deadline)
        await uow.session.flush()
        snapshot = dict(start=record.start.isoformat(), end=record.end.isoformat(),
            energy_quanta=str(int(record.energy_quanta)), kind=record.kind,
            configuration_revision=record.configuration_revision, category_revision=record.category_revision,
            provenance=record.provenance_snapshot)
        uow.session.add(AggregateContribution(aggregate_id=aggregate.id, record_id=record.id,
            record_revision=record.revision, snapshot=snapshot, incorporated_at=now))
        await uow.session.flush()
