"""Full anomalous generations reproduce original truth, defect positions and native bytes across reordered configuration."""
import json
from pathlib import Path
from pas600_simulator.report import generate_run
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.identity import scenario_hashes


def test_anomalous_reproduction_and_format_identity(tmp_path):
    """Same seed and semantic configuration preserve100% evidence; real run UUID/time remain distinct."""
    raw=json.loads(Path('tools/pas600_simulator/examples/anomalies-100.json').read_text())
    first=SimulationScenario.model_validate(raw)
    reordered=json.loads(json.dumps(raw,sort_keys=True))
    reordered['categories'].reverse()
    second=SimulationScenario.model_validate(reordered)
    assert scenario_hashes(first)==scenario_hashes(second)
    a,b=tmp_path/'a',tmp_path/'b'
    generate_run(first,a);generate_run(second,b)
    assert {p.relative_to(a/'data'):p.read_bytes() for p in (a/'data').rglob('*.csv')}=={p.relative_to(b/'data'):p.read_bytes() for p in (b/'data').rglob('*.csv')}
    for name in ('expected.jsonl','anomalies.jsonl','manifest.json'):
        assert (a/'control'/name).read_bytes()==(b/'control'/name).read_bytes()
    assert json.loads((a/'control/run.json').read_text())['id']!=json.loads((b/'control/run.json').read_text())['id']
    second.format='json';c=tmp_path/'json';generate_run(second,c)
    assert scenario_hashes(first)[0]==scenario_hashes(second)[0]
    assert scenario_hashes(first)[1]!=scenario_hashes(second)[1]
    assert (a/'control/expected.jsonl').read_bytes()==(c/'control/expected.jsonl').read_bytes()
