"""Deterministic interval generation using integer quantum indices and SHA-256."""
from datetime import UTC, timedelta
from decimal import localcontext
from pas600_simulator.calendar import interval_count, quantum_bounds
from pas600_simulator.identity import digest
from pas600_simulator.publication import ExpectedSample


def generate_samples(scenario):
    """Yield only measured categories, N intervals each; never calculate CAT-01.

    Decimal context precision derives from input coefficients plus count digits, so
    cumulative arithmetic does not silently round at the default 28 digits.
    """
    count = interval_count(scenario.start, scenario.end, scenario.timezone, scenario.sampling_minutes)
    for category in sorted(scenario.categories, key=lambda c: c.category_id):
        if not category.has_meter:
            continue
        meter, bounds = category.meter, category.expected_range
        first, last = quantum_bounds(bounds.min, bounds.max, meter.quantum)
        precision = max(len(str(abs(first))), len(str(abs(last))), len(meter.initial_counter.as_tuple().digits)) + abs(meter.quantum.as_tuple().exponent) + len(str(count)) + 20
        with localcontext() as context:
            context.prec = precision
            counter = meter.initial_counter
            for index in range(count):
                identity = [scenario.algorithm_version, scenario.seed, category.category_id, meter.device_local_id, meter.json_value_item_id, index, scenario.start.astimezone(UTC).isoformat()]
                key = digest('pas600-sample-v1', identity)
                energy = (first + int(digest('pas600-energy-v1', identity), 16) % (last - first + 1)) * meter.quantum
                start = scenario.start.astimezone(UTC) + timedelta(minutes=index * scenario.sampling_minutes)
                end = start + timedelta(minutes=scenario.sampling_minutes)
                previous = counter if meter.semantics == 'cumulative' else None
                counter += energy
                yield ExpectedSample(key, category.category_id, index, start, end, energy,
                    previous, counter if meter.semantics == 'cumulative' else None)


def readings(meter, samples):
    """Convert intervals to N+1 cumulative readings or N explicit interval readings."""
    if not samples:
        return []
    from pas600_simulator.anomalies import FormatDefect
    rows = []
    if meter.semantics == 'cumulative' and samples[0].index == 0:
        rows.append((samples[0].start, samples[0].counter_before))
    for sample in samples:
        if sample.state == 'missing':
            continue
        instant = sample.end if meter.semantics == 'cumulative' or meter.timestamp_role == 'interval_end' else sample.start
        value = sample.counter_after if meter.semantics == 'cumulative' else sample.energy
        if sample.state.startswith('format_'):
            value = FormatDefect(value, sample.state.removeprefix('format_'))
        rows.append((instant, value))
    return rows
