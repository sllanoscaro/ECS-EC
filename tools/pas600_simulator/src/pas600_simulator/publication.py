"""Local immutable sample/publication identities; never trusted server identifiers."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import re


@dataclass(frozen=True)
class ExpectedSample:
    """One unaltered interval and its exact optional cumulative endpoints."""
    key: str
    category_id: str
    index: int
    start: datetime
    end: datetime
    energy: Decimal
    counter_before: Decimal | None
    counter_after: Decimal | None
    state: str = 'normal'


@dataclass(frozen=True)
class LocalPublication:
    """Frozen native bytes for one simulated cycle; retries may never reserialize."""
    key: str
    publication_time: datetime
    categories: tuple[str, ...]
    files: tuple[tuple[str, bytes], ...]
    profile_id: str

    def manifest(self) -> dict:
        """Describe the complete immutable set with name, size and SHA-256."""
        return {'key': self.key, 'publication_time': self.publication_time.isoformat(),
            'categories': list(self.categories), 'profile_id': self.profile_id,
            'files': [{'name': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in self.files]}


def safe_name(value: str) -> str:
    """Replace forbidden native filename characters and controls, without traversal."""
    return re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', '~', value)


def build_publication(scenario, cycle, grouped):
    """Freeze a cycle, fragmenting at 24h and 256000 JSON bytes without splitting records."""
    from datetime import timedelta
    from pas600_simulator.csv_writer import encode_csv
    from pas600_simulator.json_writer import encode_json
    from pas600_simulator.generator import readings
    from pas600_simulator.identity import digest, scenario_hashes
    logical, _ = scenario_hashes(scenario)
    key = digest('pas600-publication-v1', [logical, cycle])
    publication_time = scenario.publication_time + timedelta(minutes=cycle * scenario.samples_per_publication * scenario.sampling_minutes)
    stamp = publication_time.strftime('%Y%m%d%H%M%S') + f'{publication_time.microsecond // 1000:03d}'
    channels = []
    for category in sorted(scenario.categories, key=lambda c: c.category_id):
        if category.has_meter and grouped.get(category.category_id):
            native_rows = readings(category.meter, grouped[category.category_id])
            if native_rows:
                channels.append((category.meter, native_rows))
    files = []
    if scenario.format == 'csv':
        for meter, rows in channels:
            chunks = []
            current = []
            for row in rows:
                if current and row[0] - current[0][0] > timedelta(hours=24):
                    chunks.append(current); current = []
                current.append(row)
            if current:
                chunks.append(current)
            for index, chunk in enumerate(chunks, 1):
                name = f'{safe_name(meter.reduced_id)}_{safe_name(meter.device_name)}_{stamp}_{index}.csv'
                files.append((name, encode_csv(scenario, meter, chunk)))
    else:
        flat = sorted([(instant, meter.json_value_item_id, meter, value) for meter, rows in channels for instant, value in rows], key=lambda r: (r[0], r[1]))
        chunks = []
        current = []
        for row in flat:
            if current and row[0] - current[0][0] > timedelta(hours=24):
                chunks.append(current); current = []
            current.append(row)
        if current:
            chunks.append(current)
        pending = list(reversed(chunks))
        while pending:
            chunk = pending.pop()
            series = {}
            for instant, topic, meter, value in chunk:
                if topic not in series:
                    series[topic] = (meter, [])
                series[topic][1].append((instant, value))
            data = encode_json(scenario, publication_time, list(series.values()))
            if len(data) > 256000:
                if len(chunk) == 1:
                    raise ValueError('single record exceeds JSON size limit')
                midpoint = len(chunk) // 2
                pending.extend([chunk[midpoint:], chunk[:midpoint]])
            else:
                files.append((f'{stamp}_{len(files) + 1}.json', data))
    names = [name for name, _ in files]
    if len(set(names)) != len(names):
        raise ValueError('native filename collision after sanitizing')
    return LocalPublication(key, publication_time, tuple(sorted(grouped)), tuple(files), scenario.profile_id)
