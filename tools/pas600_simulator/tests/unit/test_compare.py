"""Offline capture validation never turns missing selected evidence into complete success."""
import json
from uuid import uuid4
import pytest
from pas600_simulator.report import generate_run
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.compare import compare_run


@pytest.mark.parametrize('condition',['missing_category','empty_blocks','foreign_manifest'])
def test_incomplete_capture_is_not_complete(tmp_path,condition):
    """A valid capture ID alone proves neither all categories nor any covered block; foreign bytes are rejected."""
    scenario=SimulationScenario(end='2026-01-01T00:15:00Z')
    root=tmp_path/'run';manifest=generate_run(scenario,root)
    publication=manifest['publications'][0]
    payload=dict(schema_version=1,snapshot_id=str(uuid4()),cutoff_at='2026-01-02T00:00:00Z',
        selection=dict(building_id=str(uuid4()),category_ids=['CAT-03','CAT-05'],view='hour',
            period=dict(start=scenario.start.isoformat(),end=scenario.end.isoformat(),timezone=scenario.timezone)),
        publication=dict(manifest=publication['files']),files=[],readings=[],candidates=[],evaluations=[dict(state='completed')],
        consumption_snapshot=dict(status='available',reason_code=None,detail_results=[],aggregate_results=[dict(category_id='CAT-03',excluded_blocks=[],blocks=[])]))
    if condition=='empty_blocks':payload['consumption_snapshot']['aggregate_results'].append(dict(category_id='CAT-05',excluded_blocks=[],blocks=[]))
    if condition=='foreign_manifest':payload['publication']['manifest']=[]
    path=tmp_path/'capture.json';path.write_text(json.dumps(payload))
    if condition=='foreign_manifest':
        with pytest.raises(ValueError,match='foreign_publication'):compare_run(root,path)
    else:assert compare_run(root,path)['comparison_status']!='complete'
