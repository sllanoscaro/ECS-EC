"""CLI validation rejects effects before configuration is known to be valid."""
import json
import subprocess
import sys
from pas600_simulator.scenario import SimulationScenario


def test_cli(tmp_path):
    """Generate selectable JSON, protect existing output and reject invalid input."""
    config = tmp_path / 'scenario.json'
    config.write_text(SimulationScenario().model_dump_json())
    output = tmp_path / 'run'
    command = [sys.executable, '-c', 'from pas600_simulator.cli import main; raise SystemExit(main())', 'generate', '--scenario', str(config), '--output', str(output), '--format', 'json']
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['status'] == 'generated'
    assert list(output.rglob('*.json'))
    assert subprocess.run(command, capture_output=True).returncode == 5
    config.write_text('{"unknown": "secret-value"}')
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 2 and b'secret-value' not in result.stderr


def test_absence_and_invalid_input_without_effects(tmp_path):
    """Absent meters are not missing samples; invalid ranges never reserve output."""
    from pas600_simulator.report import generate_run
    raw = SimulationScenario().model_dump(mode='json')
    raw['categories'] = [{'category_id': c['category_id'], 'has_meter': False} for c in raw['categories']]
    result = generate_run(SimulationScenario.model_validate(raw), tmp_path / 'none')
    assert result['publications'] == []
    assert all(c == {'state': 'not_configured', 'expected': 0} for c in result['counts'].values())
    config = tmp_path / 'invalid.json'
    config.write_text('{"sampling_minutes": 0}')
    output = tmp_path / 'must-not-exist'
    command = [sys.executable, '-c', 'from pas600_simulator.cli import main; raise SystemExit(main())', 'generate', '--scenario', str(config), '--output', str(output)]
    assert subprocess.run(command, capture_output=True).returncode == 2
    assert not output.exists()
