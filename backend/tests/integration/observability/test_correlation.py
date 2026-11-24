"""007 trusted continuation crosses execution/request boundaries without accepting public trace parents."""
import asyncio,json
from uuid import UUID
from opentelemetry.trace import SpanContext,TraceFlags
from ecs_ec.observability.context import Context,new_context,bind,current,opaque_reference,resend
from ecs_ec.observability.lifecycle import Telemetry,Policy


async def test_concurrent_contexts_and_post_request_continuation(tmp_path):
    """Concurrent scopes stay separate; a serialized trusted envelope resumes into a fresh trace/execution."""
    telemetry=Telemetry(Policy(environment='test',spool=tmp_path),autostart=False)
    async def operation():
        """Close one transient request span and continue exactly its logical operation after leaving the binding."""
        context=new_context()
        with bind(context):
            await asyncio.sleep(0)
            assert current()==context
            handle=telemetry.begin('report.generate','reports',context=context)
            trace=handle.span.get_span_context();telemetry.release(handle)
        saved=json.loads(json.dumps(context.fields()))
        restored=Context(**{k:UUID(v) if k.endswith('_ref') and v else v for k,v in saved.items()})
        continued=telemetry.continue_operation('report.generate','reports',restored,link=trace)
        assert continued.context.operation_ref==context.operation_ref and continued.context.attempt_ref==context.attempt_ref
        assert continued.context.execution_ref!=context.execution_ref
        assert continued.span.get_span_context().trace_id!=trace.trace_id
        assert len(continued.span.links)==1 and continued.span.links[0].context.trace_id==trace.trace_id
        telemetry.complete(continued,event='report.completed')
        return context.operation_ref
    try:
        refs=await asyncio.gather(*(operation() for _ in range(8)))
        assert len(set(refs))==8 and current().context_status=='unavailable'
        handle=telemetry.continue_operation('report.generate','reports',new_context(),link=SpanContext(1,1,True,TraceFlags(1)))
        assert handle is not None and handle.span is None
        telemetry.release(handle)
        assert opaque_reference(b'x'*32,'test','v1','binding-a','same')!=opaque_reference(b'x'*32,'test','v1','binding-b','same')
        first=new_context();assert resend(first).attempt_ref!=first.attempt_ref
    finally:telemetry.shutdown()
