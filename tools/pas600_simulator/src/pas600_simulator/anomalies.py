"""Deterministic disjoint anomalies; original expected intervals remain immutable."""
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from fractions import Fraction
from pas600_simulator.identity import digest


@dataclass(frozen=True)
class AnomalyAssignment:
    """One deliberate sample alteration, distinct from its observable consequences."""
    category_id: str
    index: int
    kind: str
    sample_key: str
    before: str
    after: str | None
    affected_interval_indices: tuple[int, ...]
    scope: str = 'sample'


@dataclass(frozen=True)
class FormatDefect:
    """Internal instruction to a writer; never serialize these control field names."""
    original: Decimal
    mode: str


def select_positions(seed, category_id, count, rates):
    """Floor each percentage on original N and rank SHA-256 among unused positions."""
    result = {}
    reserved = [i for positions in rates.positions.values() for i in positions]
    if len(set(reserved)) != len(reserved):
        raise ValueError('overlapping explicit anomaly positions')
    for kind in ('missing', 'format', 'out_of_range'):
        amount = Fraction(getattr(rates, kind)) * count / 100
        amount = amount.numerator // amount.denominator
        explicit = rates.positions.get(kind)
        if amount == 0 and explicit is None:
            continue
        if explicit is not None:
            if len(explicit) != amount or len(set(explicit)) != amount or any(i < 0 or i >= count or i in result for i in explicit):
                raise ValueError('invalid explicit anomaly positions')
            chosen = explicit
        else:
            available = [i for i in range(count) if i not in result and i not in reserved]
            chosen = sorted(available, key=lambda index: digest('pas600-anomaly-' + kind + '-v1', [seed, category_id, index]))[:amount]
        result.update({index: kind for index in chosen})
    return result


def alter_sample(sample, category, kind, shift):
    """Return an altered copy and counter shift, preserving every unaffected increment."""
    if kind is None and shift == 0:
        return sample, shift
    meter, bounds = category.meter, category.expected_range
    with localcontext() as context:
        numbers = [sample.energy, meter.quantum, shift, sample.counter_after or Decimal(0)]
        context.prec = max(len(n.as_tuple().digits) + abs(n.as_tuple().exponent) for n in numbers) + 30
        energy = sample.energy
        if kind == 'out_of_range':
            energy = bounds.max + meter.quantum if category.rates.out_of_range_direction == 'above' else bounds.min - meter.quantum
        from pas600_simulator.calendar import representable
        if not representable(energy, meter.quantum):
            raise ValueError('outlier is not representable with channel quantum')
        before = sample.counter_before + shift if sample.counter_before is not None else None
        shift += energy - sample.energy
        after = sample.counter_after + shift if sample.counter_after is not None else None
        if after is not None and after < 0:
            raise ValueError('anomaly produces unrepresentable negative counter')
        state = 'normal' if kind is None else kind
        if kind == 'format':
            state = 'format_' + category.rates.format_mode
        return replace(sample, energy=energy, counter_before=before, counter_after=after, state=state), shift


def corrupt_publication(publication, selectors):
    """Alter only explicit frozen filenames, recording original and final hashes separately."""
    import hashlib
    selected = {s.filename: s.operation for s in selectors}
    files = []
    changes = []
    for name, original in publication.files:
        data = original
        if name in selected:
            operation = selected[name]
            if operation == 'truncate':
                data = original[:len(original) // 2]
            elif operation == 'remove_header':
                data = original.split(b'\r\n', 1)[1]
            changes.append({'scope': 'file', 'filename': name, 'operation': operation,
                'before_sha256': hashlib.sha256(original).hexdigest(), 'after_sha256': hashlib.sha256(data).hexdigest()})
        files.append((name, data))
    return replace(publication, files=tuple(files)), changes
