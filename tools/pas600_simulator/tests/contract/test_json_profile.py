"""Local JSON contract checks; independently fixed 100/104 arithmetic, no backend."""
import json
from datetime import datetime, UTC
from decimal import Decimal
from pas600_simulator.json_writer import encode_json
from pas600_simulator.scenario import SimulationScenario


def test_known_json():
    """Only native properties occur; energy uses numeric tokens and t milliseconds."""
    scenario = SimulationScenario()
    meter = scenario.categories[2].meter
    data = encode_json(scenario, scenario.publication_time, [(meter, [(datetime(2026, 1, 1, tzinfo=UTC), Decimal('100')), (datetime(2026, 1, 1, 0, 15, tzinfo=UTC), Decimal('104'))])])
    doc = json.loads(data, parse_float=Decimal)
    assert doc['$schema'].endswith('/CewsMessage')
    message = doc['message']
    assert message['remoteId'] == scenario.publisher.publisher_remote_id
    series = message['content']['data']['timeseries'][0]
    assert series['records'] == [{'v': 100, 't': 0}, {'v': 104, 't': 900000}]
    assert series['timestamp'] == '2026-01-01T00:00:00.000Z'
    assert set(series) == {'valueItemId', 'timestamp', 'records'}
