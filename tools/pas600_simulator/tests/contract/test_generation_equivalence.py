"""Independent stdlib/Decimal readers compare native files, never backend parsers."""
import csv
import io
import json
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from pathlib import Path
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.report import generate_run


def read_native(root, kind):
    """Recover topic/instant/value tuples directly from the contracted wire structure."""
    values = []
    for path in sorted((root / 'data').rglob('*.' + kind)):
        if kind == 'csv':
            data = path.read_bytes()
            assert b'\r\n' in data
            rows = list(csv.reader(io.StringIO(data.decode())))
            assert len(rows[0]) == 10 and int(rows[1][-1]) == len(rows) - 7
            assert rows[3][:3] == ['', '', '']
            assert rows[6][:3] == ['Error', 'UTC Offset (minutes)', 'Local Time Stamp']
            for row in rows[7:]:
                assert row[0] == '0'
                instant = datetime.fromisoformat(row[2]).replace(tzinfo=UTC) - timedelta(minutes=int(row[1]))
                values.append((rows[4][3].replace('SYNTHETIC.', 'synthetic/').replace('.energy', '/energy'), instant, Decimal(row[3])))
        else:
            assert len(path.read_bytes()) <= 256000
            doc = json.loads(path.read_text(), parse_float=Decimal)
            assert set(doc) == {'$schema', 'message'}
            message = doc['message']
            assert message['contentType'] == 'data' and message['cewsVersion'] == '3.0.0'
            for series in message['content']['data']['timeseries']:
                base = datetime.fromisoformat(series['timestamp'])
                for record in series['records']:
                    assert set(record) == {'v', 't'}
                    values.append((series['valueItemId'], base + timedelta(milliseconds=record['t']), Decimal(record['v'])))
    return sorted(values)


def test_formats_and_reproduction(tmp_path):
    """Seven independent channels produce equivalent readings and reproducible bytes."""
    scenario = SimulationScenario()
    generate_run(scenario, tmp_path / 'csv')
    scenario.format = 'json'
    generate_run(scenario, tmp_path / 'json')
    generate_run(scenario, tmp_path / 'again')
    assert read_native(tmp_path / 'csv', 'csv') == read_native(tmp_path / 'json', 'json')
    assert len(read_native(tmp_path / 'json', 'json')) == 7 * 97
    original = {p.relative_to(tmp_path / 'json/data'): p.read_bytes() for p in (tmp_path / 'json/data').rglob('*.json')}
    repeated = {p.relative_to(tmp_path / 'again/data'): p.read_bytes() for p in (tmp_path / 'again/data').rglob('*.json')}
    assert original == repeated


def test_fragmentation_and_decimal_precision(tmp_path):
    """Long exact counters force JSON fragmentation; both formats preserve all readings."""
    raw = SimulationScenario().model_dump(mode='json')
    raw.update(end='2026-01-03T00:00:00Z', samples_per_publication=192)
    for category in raw['categories']:
        category['meter']['initial_counter'] = '1' + '0' * 500
        category['meter']['quantum'] = '0.0000000000000000000000000000000001'
        category['expected_range'].update(min='4', max='4')
    scenario = SimulationScenario.model_validate(raw)
    generate_run(scenario, tmp_path / 'csv')
    scenario.format = 'json'
    result = generate_run(scenario, tmp_path / 'json')
    assert len(result['publications'][0]['files']) > 2
    assert read_native(tmp_path / 'csv', 'csv') == read_native(tmp_path / 'json', 'json')
    assert len(read_native(tmp_path / 'json', 'json')) == 7 * 193
