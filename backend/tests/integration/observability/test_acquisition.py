"""007 terminal protocol with real002 partial commits; installed002/003 coverage belongs to step3.

The explicit emitter calls exercise the common producer protocol against durable
outcomes. They do not claim that002:T065/003:T072 have installed that adapter yet.
Existing actualSFTP emitter tests are referenced in validation/step2.md.
"""
import json
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from backend.tests.contract.consumption.test_reception_contract import publish,BUILDING,PROCESS
from backend.tests.unit.consumption.test_validation import record
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.consumption.models import IncorporatedRecord
from ecs_ec.observability.context import new_context
from ecs_ec.observability.lifecycle import Telemetry,Policy
pytestmark=pytest.mark.integration


async def test_three_commits_two_pending_one_logical_terminal(history_environment,database,clock,tmp_path,monkeypatch):
    """Real partial consumption never permits a logical completion; recovery reports all five accepted positions once."""
    telemetry=Telemetry(Policy(environment='test',spool=tmp_path),autostart=False)
    attempt=uuid4();context=new_context();handle=telemetry.begin('reception.accept','consumption',context=context)
    rows=[record(category_id='CAT-03',source_id=UUID(int=3),value=str(i+1),start=f'2026-01-01T00:{15*i:02}:00Z',end=f'2026-01-01T00:{15*(i+1):02}:00Z') for i in range(3)]
    rows.extend([record(value='1'),record(value='2',start='2026-01-01T01:00:00Z',end='2026-01-01T02:00:00Z')])
    original=history_environment._category
    async def fail(attempt,building,category,*args):
        """Interrupt the actual later category transaction, preserving the first three committed results."""
        if category=='CAT-05':raise RuntimeError('synthetic_partial')
        return await original(attempt,building,category,*args)
    try:
        monkeypatch.setattr(history_environment,'_category',fail)
        with pytest.raises(RuntimeError):await publish(history_environment,rows,attempt=attempt)
        partial=await history_environment.read_attempt(attempt,BUILDING,PROCESS)
        assert partial.state=='partial_failure' and len(partial.outcome.results)==3 and len(partial.outcome.pending_positions)==2
        assert telemetry.complete(handle,event='execution.completed',outcome='unexpected_error',code='processing_interrupted',counts=None)=='enqueued'
        monkeypatch.setattr(history_environment,'_category',original)
        resumed=telemetry.continue_operation('reception.accept','consumption',context)
        result=await publish(history_environment,rows,attempt=attempt)
        assert result.state=='completed' and len(result.results)==5
        telemetry.complete(resumed,event='execution.completed')
        telemetry.complete(resumed,event='reception.completed',counts={'records_accepted':len(result.results)})
        assert (await history_environment.read_attempt(attempt,BUILDING,PROCESS)).outcome==result
        payloads=[];telemetry.logs._writer=payloads.append
        while telemetry.logs.drain_one():pass
        events=[json.loads(p) for p in payloads]
        executions=[e for e in events if e['event']=='execution.completed'];logical=[e for e in events if e['event']=='reception.completed']
        assert len(executions)==2 and len(logical)==1 and executions[0]['counts'] is None
        assert executions[0]['attempt_ref']==executions[1]['attempt_ref']==logical[0]['attempt_ref']
        assert executions[0]['execution_ref']!=executions[1]['execution_ref']
        async with UnitOfWork(database.sessions) as uow:assert await uow.session.scalar(select(func.count()).select_from(IncorporatedRecord))==5
    finally:telemetry.shutdown()
