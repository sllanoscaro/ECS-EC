"""Report CLI exposes only control facts and cannot infer functional acceptance or echo credentials."""
import json,subprocess,sys
from pathlib import Path
from pas600_simulator.report import generate_run
from pas600_simulator.scenario import SimulationScenario


def test_report_closed_transfer_fields_and_immutable_originals(tmp_path):
    """Unrecognized journal secret fields never reach the report; transfer facts do not become reception facts."""
    root=tmp_path/'run';generate_run(SimulationScenario(end='2026-01-01T00:15:00Z'),root)
    originals={p.relative_to(root):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}
    (root/'control/transfers.pending.json').write_text(json.dumps({'attempts':[dict(id='synthetic-attempt',publication_status='transferred',session_end='clean',password='PRIVATE_REPORT_MARKER',files=[dict(name='native.csv',file_status='transferred',private_key='PRIVATE_KEY_MARKER')])]}))
    output=tmp_path/'report.json'
    result=subprocess.run([str(Path(sys.executable).with_name('pas600-sim')),'report','--run',str(root),'--output',str(output)],capture_output=True,text=True)
    assert result.returncode==0
    report=output.read_text()
    assert 'PRIVATE_' not in report and 'transferred' in report
    assert {p.relative_to(root):p.read_bytes() for p in (root/'data').rglob('*') if p.is_file()}==originals
