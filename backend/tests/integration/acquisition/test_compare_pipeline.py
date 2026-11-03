"""Standalone generator/compare CLI consumes a real003/002 export, with independent known4kWh expectations."""
import json,os,subprocess
from pathlib import Path
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.staging import Staging
from ecs_ec.acquisition.models import NativePublication
from ecs_ec.acquisition.evidence import export_results
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import service
from backend.tests.integration.consumption.test_detail_queries import facade

pytestmark=pytest.mark.integration
CLI='tools/pas600_simulator/.venv/bin/pas600-sim'


async def pipeline(env,tmp_path,intervals=1):
    """Generate exact4kWh source3 increments without backend imports, then adapt through real003 and002."""
    scenario=json.loads(Path('tools/pas600_simulator/examples/seven-meters.json').read_text())
    scenario.update(start='2025-12-31T21:00:00-03:00',end=f'2025-12-31T21:{intervals*15:02}:00-03:00',
        publication_time='2025-12-31T22:00:00-03:00',timezone='America/Santiago',format='json')
    for index,category in enumerate(scenario['categories'],1):
        if index!=3:
            category.clear();category.update(category_id=f'CAT-{index:02}',has_meter=False)
        else:
            channel=env['binding'].channels[2]
            category['meter'].update(device_local_id=channel.device_local_id,reduced_id=channel.reduced_id,
                device_name=channel.device_name,csv_topic_id=channel.csv_topic_id,json_value_item_id=channel.json_value_item_id,initial_counter='100')
            category['expected_range'].update(min='4',max='4')
    scenario['publisher'].update(publisher_serial=env['binding'].publisher_serial,publisher_remote_id=env['binding'].publisher_remote_id)
    configuration=tmp_path/'scenario.json';configuration.write_text(json.dumps(scenario))
    run=tmp_path/'run'
    generated=subprocess.run([CLI,'generate','--scenario',str(configuration),'--output',str(run),'--format','json'],capture_output=True,text=True)
    assert generated.returncode==0,generated.stderr
    manifest=json.loads((run/'control/manifest.json').read_text())['publications'][0]
    staging=Staging(env['database'],env['clock'],env['settings'],env['binding']);await staging.start()
    for file in manifest['files']:
        handle=await staging.open(file['name'])
        await staging.write(handle,0,(run/'data'/manifest['key']/file['name']).read_bytes());await staging.close(handle)
    staging.clean_eof=True
    publication=await staging.finish()
    acquisition=service(env);acquisition.consumption=facade(env['database'],env['clock'])
    outcome=await acquisition.process_sealed(publication)
    assert len(outcome['results'])==intervals and all(r['status']=='accepted' for r in outcome['results'])
    async with UnitOfWork(env['database'].sessions) as uow:
        reference=(await uow.session.get(NativePublication,publication)).publication_ref
    return run,acquisition,reference


@pytest.mark.parametrize('condition,exit_code',[('normal',0),('different',6),('unavailable',5),('partial',5),('false_coverage',6)])
async def test_compare_actual_snapshot(acquisition_environment,tmp_path,condition,exit_code):
    """Complete matches return0, observed differences6 and insufficient/unavailable coverage5 without false global success."""
    env=acquisition_environment
    grouped=condition in ('partial','false_coverage')
    run,acquisition,reference=await pipeline(env,tmp_path,3 if grouped else 1)
    snapshot=await export_results(acquisition,process='process:test',publication_ref=reference,
        start='2025-12-31T21:00:00-03:00',end='2025-12-31T22:00:00-03:00' if grouped else '2025-12-31T21:15:00-03:00',
        timezone='America/Santiago',categories=['CAT-03'],view='hour' if grouped else 'detail')
    if condition=='different':snapshot['consumption_snapshot']['detail_results'][0]['rows'][0]['energy_kwh']='5'
    if condition=='unavailable':snapshot['consumption_snapshot']=dict(status='unavailable',reason_code='provider_unavailable',detail_results=[],aggregate_results=[])
    if grouped:
        block=snapshot['consumption_snapshot']['aggregate_results'][0]['blocks'][0]
        assert block['covered_duration_us']=='2700000000' and block['coverage_percent']=='75'
        if condition=='false_coverage':block.update(covered_duration_us='3600000000',coverage_percent='100')
    reception=tmp_path/'snapshot.json';reception.write_text(json.dumps(snapshot))
    output=tmp_path/'comparison.json'
    result=subprocess.run([CLI,'compare','--run',str(run),'--reception',str(reception),'--output',str(output)],capture_output=True,text=True)
    assert result.returncode==exit_code,(result.stderr,result.stdout)
    comparison=json.loads(output.read_text())
    assert comparison['snapshot_id']==snapshot['snapshot_id']
    assert (comparison['comparison_status']=='complete')==(condition in ('normal','different','false_coverage'))
    assert bool(comparison['differences'])==(condition in ('different','false_coverage'))
