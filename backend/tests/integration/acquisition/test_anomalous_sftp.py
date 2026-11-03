"""Generated100-sample anomalies travel over real SFTP; independent defect positions predict only admissible adjacent pairs."""
import asyncio,json
from pathlib import Path
import asyncssh
import pytest
from sqlalchemy import select
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.acquisition.models import NativeReading
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import service

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('native_format,format_mode',[('csv','type'),('csv','date'),('json','type'),('json','date')])
async def test_known_anomalies_preserve_independent_categories(sftp_environment,tmp_path,native_format,format_mode):
    """Ten omissions, ten invalid records and ten positive outliers affect onlyCAT-03; no gap becomes zero or a bridged delta."""
    env=sftp_environment
    scenario=json.loads(Path('tools/pas600_simulator/examples/anomalies-100.json').read_text())
    scenario.update(timezone='America/Santiago',format=native_format)
    scenario['publisher'].update(publisher_serial=env['binding'].publisher_serial,publisher_remote_id=env['binding'].publisher_remote_id)
    from datetime import datetime
    from zoneinfo import ZoneInfo
    for field in ('start','end','publication_time'):
        scenario[field]=datetime.fromisoformat(scenario[field]).astimezone(ZoneInfo('America/Santiago')).isoformat()
    for category,channel in zip(scenario['categories'],env['binding'].channels):
        category['meter'].update(device_local_id=channel.device_local_id,reduced_id=channel.reduced_id,device_name=channel.device_name,
            csv_topic_id=channel.csv_topic_id,json_value_item_id=channel.json_value_item_id)
        category['rates']['format_mode']=format_mode
    path=tmp_path/'scenario.json';path.write_text(json.dumps(scenario));root=tmp_path/'run'
    generate=await asyncio.create_subprocess_exec('tools/pas600_simulator/.venv/bin/pas600-sim','generate','--scenario',str(path),'--output',str(root),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    output,error=await generate.communicate();assert generate.returncode==0,(output,error)
    manifest=json.loads((root/'control/manifest.json').read_text())
    assignments=[json.loads(line) for line in (root/'control/anomalies.jsonl').read_text().splitlines()]
    assert {kind:sum(a['kind']==kind for a in assignments) for kind in ('missing','format','out_of_range')}=={'missing':10,'format':10,'out_of_range':10}
    absent={i for a in assignments if a['kind'] in ('missing','format') for i in a['affected_interval_indices']}
    for publication in manifest['publications']:
        async with asyncssh.connect('127.0.0.1',env['port'],username='pas600',client_keys=[str(env['private'])],known_hosts=str(env['known'])) as connection:
            sftp=await connection.start_sftp_client()
            for file in publication['files']:
                async with sftp.open(file['name'],'xb',encoding=None) as stream:await stream.write((root/'data'/publication['key']/file['name']).read_bytes())
            sftp.exit();await sftp.wait_closed()
        await service(env).recover()
        env['clock'].advance(900)  # Internal002 timing test only; real_time separately measures real SSH cadence.
    async with UnitOfWork(env['database'].sessions) as uow:
        incorporated=(await uow.session.scalars(select(IncorporatedRecord))).all()
        counts={f'CAT-{i:02}':sum(row.category_id==f'CAT-{i:02}' for row in incorporated) for i in range(1,8)}
        assert counts=={f'CAT-{i:02}':100-len(absent) if i==3 else 100 for i in range(1,8)}
        invalid=(await uow.session.scalars(select(NativeReading).where(NativeReading.state=='invalid'))).all()
        assert len(invalid)==10 and all(row.value is None for row in invalid)
