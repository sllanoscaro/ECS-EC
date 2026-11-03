"""Real multi-file SFTP uses001/002 to calculate optionalCAT-01 while preserving an independent measured total."""
import json
import asyncssh
import pytest
from sqlalchemy import select
from ecs_ec.acquisition.models import NativePublication,PublicationEvaluation,AdaptationResult
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.test_recovery import service,native_bytes
from backend.tests.integration.consumption.test_pending_totals import calculated_config

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('measured',[False,True])
async def test_optional_total_over_actual_multifile_sftp(sftp_environment,measured):
    """CAT-03=4 andCAT-05=7 yield calculated11, while an actualCAT-01=20 remains20; corrupt independent bytes do not discard either."""
    env=sftp_environment
    if not measured:await calculated_config(env['database'],env['clock'])
    files=[]
    for category,value in [(3,104),(5,107)]+([(1,120)] if measured else []):
        data=json.loads(native_bytes(value));series=data['message']['content']['data']['timeseries'][0]
        series['valueItemId']=f'modbus:1_mb_EaImport{category}';series['timestamp']='2026-01-02T00:00:00Z'
        files.append(json.dumps(data).encode())
    files.append(b'{broken')
    async with asyncssh.connect('127.0.0.1',env['port'],username='pas600',client_keys=[str(env['private'])],known_hosts=str(env['known'])) as connection:
        sftp=await connection.start_sftp_client()
        for index,data in enumerate(files,1):
            async with sftp.open(f'20260102003000000_{index}.json','xb',encoding=None) as stream:await stream.write(data)
        sftp.exit();await sftp.wait_closed()
    await service(env).recover()
    async with UnitOfWork(env['database'].sessions) as uow:
        publication=(await uow.session.scalars(select(NativePublication))).one()
        evaluation=(await uow.session.scalars(select(PublicationEvaluation))).one()
        assert evaluation.state=='completed' and all(r['status']=='accepted' for r in evaluation.outcome['results'])
        total=(await uow.session.scalars(select(IncorporatedRecord).where(IncorporatedRecord.category_id=='CAT-01'))).one()
        assert total.energy_kwh==(20 if measured else 11) and total.kind==('measured' if measured else 'calculated')
        assert len(evaluation.outcome['updates'])==(3 if measured else 2)
        assert len({r['category_id'] for r in evaluation.outcome['updates']})==len(evaluation.outcome['updates'])
        assert any(r.reason=='file_unreadable' for r in (await uow.session.scalars(select(AdaptationResult))).all())
