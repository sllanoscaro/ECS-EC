"""003 authorized export retains one actual002/001 capture, with explicit insufficient evidence instead of fictitious zeros."""
import pytest
from backend.tests.integration.acquisition.conftest import acquisition_environment
from backend.tests.integration.acquisition.test_recovery import sealed,service
from backend.tests.integration.consumption.test_detail_queries import facade
from ecs_ec.acquisition.evidence import export_results

pytestmark=pytest.mark.integration


async def test_single_capture_and_unavailable(acquisition_environment):
    """Known4kWh matches frozen002 references and detail in a shared export; an absent provider is unavailable, not empty success."""
    env=acquisition_environment;acquisition=service(env)
    publication=await sealed(env)
    outcome=await acquisition.process_sealed(publication)
    acquisition.consumption=facade(env['database'],env['clock'])
    from ecs_ec.core.unit_of_work import UnitOfWork
    from ecs_ec.acquisition.models import NativePublication
    async with UnitOfWork(env['database'].sessions) as uow:
        reference=(await uow.session.get(NativePublication,publication)).publication_ref
    args=dict(process='process:test',publication_ref=reference,start='2025-12-31T21:00:00-03:00',end='2025-12-31T21:15:00-03:00',timezone='America/Santiago',categories=['CAT-03'],view='detail')
    result=await export_results(acquisition,**args)
    assert result['evaluations'][0]['outcome']==outcome
    detail=result['consumption_snapshot']['detail_results'][0]
    assert detail['rows'][0]['energy_kwh']=='4'
    assert detail['rows'][0]['record_id']==outcome['results'][0]['measurement_id']
    assert result['selection']['category_ids']==['CAT-03']
    acquisition.consumption=None
    missing=await export_results(acquisition,**args)
    assert missing['consumption_snapshot']==dict(status='unavailable',reason_code='provider_unavailable',detail_results=[],aggregate_results=[])
    with pytest.raises(PermissionError):await export_results(acquisition,**(args|{'process':'untrusted'}))
    with pytest.raises(ValueError):await export_results(acquisition,**(args|{'categories':['CAT-03','CAT-03']}))


async def test_export_capture_does_not_mix_concurrent_reception(acquisition_environment,monkeypatch):
    """Pause after the readonly capture starts, accept4 concurrently, and prove the old export remains coherently empty."""
    import asyncio
    from ecs_ec.acquisition.models import NativePublication
    from ecs_ec.core.unit_of_work import UnitOfWork
    env=acquisition_environment;acquisition=service(env)
    publication=await sealed(env)
    await acquisition.prepare(publication)
    acquisition.consumption=facade(env['database'],env['clock'])
    entered,resume=asyncio.Event(),asyncio.Event()
    original=acquisition.consumption.read_report_snapshot
    async def paused(*args,**kwargs):
        """Hold the exact caller-owned read transaction while the real reception commits elsewhere."""
        entered.set();await resume.wait()
        return await original(*args,**kwargs)
    monkeypatch.setattr(acquisition.consumption,'read_report_snapshot',paused)
    async with UnitOfWork(env['database'].sessions) as uow:
        ref=(await uow.session.get(NativePublication,publication)).publication_ref
    args=dict(process='process:test',publication_ref=ref,start='2025-12-31T21:00:00-03:00',end='2025-12-31T21:15:00-03:00',timezone='America/Santiago',categories=['CAT-03'],view='detail')
    task=asyncio.create_task(export_results(acquisition,**args))
    await entered.wait()
    try:await acquisition.process_sealed(publication)
    finally:resume.set()
    old=await task
    assert old['evaluations'][0]['outcome'] is None
    assert old['consumption_snapshot']['detail_results'][0]['rows']==[]
    monkeypatch.setattr(acquisition.consumption,'read_report_snapshot',original)
    new=await export_results(acquisition,**args)
    assert new['evaluations'][0]['outcome']['state']=='completed'
    assert new['consumption_snapshot']['detail_results'][0]['rows'][0]['energy_kwh']=='4'
