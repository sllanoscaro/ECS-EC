"""007 terminal semantics before any producer integration: one transition, bounded safe fields and no fake completion."""
import json
from uuid import uuid4
from ecs_ec.observability.lifecycle import Telemetry,Policy
from ecs_ec.observability.context import new_context


def events(telemetry,path):
    """Drain only the real bounded logger to its synthetic spool and return schema-validated events."""
    while telemetry.logs.depth:telemetry.logs.drain_one()
    return [json.loads(line) for p in path.glob('*.jsonl') for line in p.read_text().splitlines()]


def test_report_admission_and_terminal_are_separate(tmp_path):
    """Only a new durable report is admitted; stage/query/release never inflate terminal counts."""
    telemetry=Telemetry(Policy(spool=tmp_path,environment='test'),autostart=False)
    try:
        handle=telemetry.begin('report.generate','reports')
        assert telemetry.admitted(handle)=='enqueued'
        assert telemetry.admitted(handle)=='dropped'
        context=handle.context;telemetry.release(handle)
        resumed=telemetry.continue_operation('report.generate','reports',context)
        assert resumed.context.operation_ref==context.operation_ref and resumed.context.attempt_ref==context.attempt_ref
        assert resumed.context.execution_ref!=context.execution_ref and resumed.context.context_status=='recovered'
        assert telemetry.complete(resumed,event='report.completed')=='enqueued'
        assert telemetry.complete(resumed,event='report.completed')=='dropped'
        observed=events(telemetry,tmp_path)
        assert [e['event'] for e in observed].count('report.admitted')==1
        assert [e['event'] for e in observed].count('report.completed')==1
        assert not any(e['event']=='operation.completed' for e in observed)
    finally:telemetry.shutdown()


def test_receipt_partial_execution_cannot_claim_logical_completion(tmp_path):
    """A partial failed execution has no counts; only the producer-confirmed complete receipt has its summary."""
    telemetry=Telemetry(Policy(spool=tmp_path,environment='test'),autostart=False)
    try:
        handle=telemetry.begin('reception.accept','consumption')
        assert telemetry.complete(handle,event='execution.completed',outcome='unexpected_error',code='processing_interrupted',counts={'records_accepted':3})=='dropped'
        assert telemetry.complete(handle,event='execution.completed',outcome='unexpected_error',code='processing_interrupted')=='enqueued'
        resumed=telemetry.continue_operation('reception.accept','consumption',handle.context)
        assert telemetry.complete(resumed,event='reception.completed',counts={'records_accepted':5})=='enqueued'
        observed=events(telemetry,tmp_path)
        assert len([e for e in observed if e['event']=='execution.completed'])==1
        assert [e for e in observed if e['event']=='reception.completed'][0]['counts']=={'records_accepted':5}
    finally:telemetry.shutdown()
