"""Historical generation uses calendar bounds, bounded cycles and no network."""
import json
import socket
from unittest.mock import patch
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.report import generate_run


def test_year_without_network(tmp_path):
    """A calendar year contains 35040 intervals per measured category in 2026."""
    scenario = SimulationScenario(end='2027-01-01T00:00:00Z', format='json')
    with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
        result = generate_run(scenario, tmp_path / 'year')
    assert len(result['publications']) == 365
    assert all(c['expected'] == 35040 for c in result['counts'].values())
    with (tmp_path / 'year/control/expected.jsonl').open() as stream:
        assert sum(1 for _ in stream) == 245280
    assert json.loads((tmp_path / 'year/control/run.json').read_text())['state'] == 'generated'
