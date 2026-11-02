"""File-level corruption is explicit and separate from per-sample assignments."""
import pytest
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.report import generate_run


def test_selected_file_and_no_effect_on_other_files(tmp_path):
    """Only the selected CSV loses its header; unknown selectors have no output effects."""
    raw = SimulationScenario().model_dump(mode='json')
    filename = '1_mb_iEM3150 CAT01_20260102000000000_1.csv'
    raw['structural_corruptions'] = [{'filename': filename, 'operation': 'remove_header'}]
    scenario = SimulationScenario.model_validate(raw)
    manifest = generate_run(scenario, tmp_path / 'broken')
    assert len(manifest['structural_corruptions']) == 1
    assert (tmp_path / 'broken/control/anomalies.jsonl').read_text() == ''
    raw['structural_corruptions'][0]['filename'] = 'does-not-exist.csv'
    with pytest.raises(ValueError):
        generate_run(SimulationScenario.model_validate(raw), tmp_path / 'invalid')
    assert not (tmp_path / 'invalid').exists()


def test_json_truncation_and_other_csv_bytes(tmp_path):
    """JSON truncation is unreadable; CSV files outside the selector remain byte-identical."""
    import json
    normal = SimulationScenario()
    baseline = generate_run(normal, tmp_path / 'normal')
    raw = normal.model_dump(mode='json')
    filename = '1_mb_iEM3150 CAT01_20260102000000000_1.csv'
    raw['structural_corruptions'] = [{'filename': filename, 'operation': 'remove_header'}]
    changed = generate_run(SimulationScenario.model_validate(raw), tmp_path / 'changed')
    for original, altered in zip(baseline['publications'][0]['files'], changed['publications'][0]['files']):
        if original['name'] != filename:
            assert original == altered
        else:
            assert original['sha256'] != altered['sha256']
    raw.update(format='json', structural_corruptions=[{'filename': '20260102000000000_1.json', 'operation': 'truncate'}])
    result = generate_run(SimulationScenario.model_validate(raw), tmp_path / 'json')
    publication = result['publications'][0]
    path = tmp_path / 'json/data' / publication['key'] / publication['files'][0]['name']
    with pytest.raises(json.JSONDecodeError):
        json.loads(path.read_text())
