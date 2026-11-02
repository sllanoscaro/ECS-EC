"""Local control evidence and generation orchestration; no network or backend imports."""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from itertools import zip_longest
from pathlib import Path
import json
import os
from pas600_simulator.generator import generate_samples
from pas600_simulator.identity import scenario_hashes
from pas600_simulator.journal import LocalRun, atomic_json
from pas600_simulator.publication import build_publication


@dataclass
class ControlReport:
    """Versioned generation facts; absence is explicit and transfers imply no acceptance."""
    profile_id: str
    seed: str
    logical_hash: str
    complete_hash: str
    publications: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    schema_version: int = 1


def json_value(value):
    """Encode exact control decimals as strings and instants as ISO8601."""
    if isinstance(value, (Decimal, datetime)):
        return str(value) if isinstance(value, Decimal) else value.isoformat()
    raise TypeError('unsupported control value')


def generate_run(scenario, output: Path):
    """Stream one cycle of all measured channels at a time and freeze its evidence.

    Validate unsupported anomalies and name collisions before reserving output.
    Failures preserve a failed journal and never present partial data as generated.
    """
    from pas600_simulator.anomalies import alter_sample, AnomalyAssignment
    from pas600_simulator.calendar import interval_count
    measured = [c for c in scenario.categories if c.has_meter]
    categories = {c.category_id: c for c in measured}
    total = interval_count(scenario.start, scenario.end, scenario.timezone, scenario.sampling_minutes)
    assignments = validate_generation(scenario)
    logical, complete = scenario_hashes(scenario)
    run = LocalRun.create(output, logical)
    manifest = asdict(ControlReport(profile_id=scenario.profile_id, seed=scenario.seed, logical_hash=logical, complete_hash=complete))
    counts = {c.category_id: {'state': 'measured' if c.has_meter else 'not_configured', 'expected': 0} for c in scenario.categories}
    try:
        atomic_json(output / 'control/scenario.safe.json', scenario.model_dump(mode='json'))
        iterators = [generate_samples(scenario.model_copy(update={'categories': [c]})) for c in measured]
        grouped = {}
        cycle = 0
        shifts = {c.category_id: Decimal(0) for c in measured}
        with (output / 'control/expected.jsonl').open('x', encoding='utf-8') as expected, (output / 'control/anomalies.jsonl').open('x', encoding='utf-8') as anomalies:
            for batch in zip_longest(*iterators):
                for sample in batch:
                    if sample is None:
                        continue
                    expected.write(json.dumps(asdict(sample), default=json_value, sort_keys=True) + '\n')
                    counts[sample.category_id]['expected'] += 1
                    kind = assignments[sample.category_id].get(sample.index)
                    altered, shifts[sample.category_id] = alter_sample(sample, categories[sample.category_id], kind, shifts[sample.category_id])
                    if kind:
                        affected = (sample.index,)
                        if kind in ('missing', 'format') and categories[sample.category_id].meter.semantics == 'cumulative' and sample.index + 1 < total:
                            affected += (sample.index + 1,)
                        assignment = AnomalyAssignment(sample.category_id, sample.index, kind, sample.key, str(sample.energy), None if kind == 'missing' else (('invalid-value' if categories[sample.category_id].rates.format_mode == 'type' else 'invalid-date') if kind == 'format' else str(altered.energy)), affected)
                        anomalies.write(json.dumps(asdict(assignment), sort_keys=True) + '\n')
                    grouped.setdefault(sample.category_id, []).append(altered)
                if grouped and max(len(v) for v in grouped.values()) >= scenario.samples_per_publication:
                    persist_publication(scenario, output, cycle, grouped, manifest)
                    grouped = {}; cycle += 1
            if grouped:
                persist_publication(scenario, output, cycle, grouped, manifest)
            expected.flush(); os.fsync(expected.fileno())
            anomalies.flush(); os.fsync(anomalies.fileno())
        for category_id, selected in assignments.items():
            counts[category_id]['assignments'] = {kind: list(selected.values()).count(kind) for kind in ('missing', 'format', 'out_of_range')}
        manifest['counts'] = counts
        atomic_json(output / 'control/manifest.json', manifest)
        run.state = 'generated'; run.save()
        return manifest
    except Exception:
        run.state = 'failed'; run.save()
        raise


def persist_publication(scenario, output, cycle, grouped, manifest):
    """Write immutable native files and fsync the cycle before adding its manifest."""
    publication = build_publication(scenario, cycle, grouped)
    from pas600_simulator.anomalies import corrupt_publication
    publication, corruptions = corrupt_publication(publication, scenario.structural_corruptions)
    manifest.setdefault('structural_corruptions', []).extend(corruptions)
    root = output / 'data' / publication.key
    root.mkdir()
    for name, data in publication.files:
        with (root / name).open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    directory = os.open(output / 'data', os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    manifest['publications'].append(publication.manifest())


def validate_structural_selectors(scenario, assignments):
    """Resolve every selected native file before output effects, using bounded cycles."""
    from pas600_simulator.anomalies import alter_sample
    measured = [c for c in scenario.categories if c.has_meter]
    categories = {c.category_id: c for c in measured}
    iterators = [generate_samples(scenario.model_copy(update={'categories': [c]})) for c in measured]
    shifts = {c.category_id: Decimal(0) for c in measured}
    selected = {s.filename for s in scenario.structural_corruptions}
    if len(selected) != len(scenario.structural_corruptions):
        raise ValueError('ambiguous structural selector')
    matches = {name: 0 for name in selected}
    grouped = {}
    cycle = 0
    for batch in zip_longest(*iterators):
        for sample in batch:
            if sample is None:
                continue
            altered, shifts[sample.category_id] = alter_sample(sample, categories[sample.category_id], assignments[sample.category_id].get(sample.index), shifts[sample.category_id])
            grouped.setdefault(sample.category_id, []).append(altered)
        if grouped and max(len(v) for v in grouped.values()) >= scenario.samples_per_publication:
            publication = build_publication(scenario, cycle, grouped)
            for name, _ in publication.files:
                if name in matches:
                    matches[name] += 1
            grouped = {}; cycle += 1
    if grouped:
        publication = build_publication(scenario, cycle, grouped)
        for name, _ in publication.files:
            if name in matches:
                matches[name] += 1
    if any(n != 1 for n in matches.values()):
        raise ValueError('structural selector must identify exactly one native file')
    if any(s.operation == 'remove_header' and not s.filename.endswith('.csv') for s in scenario.structural_corruptions):
        raise ValueError('remove_header requires CSV')


def validate_generation(scenario):
    """Validate selection, exact outliers, filenames and structural targets without writes."""
    from pas600_simulator.publication import safe_name
    measured = [c for c in scenario.categories if c.has_meter]
    from pas600_simulator.anomalies import select_positions, alter_sample, AnomalyAssignment
    from pas600_simulator.calendar import interval_count
    total = interval_count(scenario.start, scenario.end, scenario.timezone, scenario.sampling_minutes)
    assignments = {c.category_id: select_positions(scenario.seed, c.category_id, total, c.rates) for c in measured}
    categories = {c.category_id: c for c in measured}
    for category in measured:
        if category.rates.out_of_range:
            shift = Decimal(0)
            for sample in generate_samples(scenario.model_copy(update={'categories': [category]})):
                _, shift = alter_sample(sample, category, assignments[category.category_id].get(sample.index), shift)
    names = [safe_name(c.meter.reduced_id) + '_' + safe_name(c.meter.device_name) for c in measured]
    if len(set(names)) != len(names):
        raise ValueError('native filename collision after sanitizing')
    if scenario.structural_corruptions:
        validate_structural_selectors(scenario, assignments)
    return assignments
