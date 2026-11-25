/**007 known outcomes exercise continuity, denominators and ns boundaries independently of LogQL. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcile,timestampNs,jaegerReferences,DIMENSIONS} from './reconcile.mjs';
const start=timestampNs('2026-11-24T00:01:00Z'), end=start+30000000000n, now=end+60000000000n;
/**Construct only synthetic safe transport snapshots, not domain implementations. */
function health(extra={}) {return {collector_restarts_total:0,collector_started_at:'2026-11-23T00:00:00Z',logs_dropped_total:0,spool_dropped_total:0,schema_rejected_total:0,collector_dropped_total:0,spans_dropped_total:0,trace_export_failures_total:0,log_collector_status:'available',last_log_collector_success:'2026-11-24T00:00:59Z',trace_export_status:'available',last_trace_export_success:'2026-11-24T00:00:59Z',...extra};}
/**Allocate a deterministic interval with three heartbeat boundaries and fixture results. */
function fixture(results=[]) {
 const rows=[{timestamp:'2026-11-24T00:00:59Z',event:'telemetry.heartbeat',health:health()},...results,{timestamp:'2026-11-24T00:01:31Z',event:'telemetry.heartbeat',health:health()}];
 return rows.map((row,index)=>({event_id:'event-'+index,boot_id:'boot-a',sequence:index+1,environment:'test',policy_revision:'007-v1',service_version:'test-1',timestamp:'2026-11-24T00:01:10Z',operation:'consumption.query_detail',event:'operation.completed',outcome:'success',...row}));
}
/**Use a closed verified technical window, independent of a production clock or real retention. */
function options(extra={}) {return {startNs:start,endNs:end,nowNs:now,environment:'test',retentionHours:24,traceEvidence:{reachable:true,ids:new Set()},...extra};}

test('10/8/2 is20%; stages and preadmission rejection do not change logical denominator',()=>{
 const rows=fixture([...Array.from({length:10},(_,i)=>({outcome:i<8?'success':'unexpected_error'})),{event:'stage.completed'},{operation:'report.generate',event:'operation.completed',outcome:'expected_rejection'}]);
 const result=reconcile(rows,options());assert.equal(result.logs,'complete');assert.equal(result.measures.operations_total,10);assert.equal(result.measures.unexpected_error_percent,20);
});
test('3 commits then2 recovered are5 new records,1 logical attempt and2 executions,50% versus0%',()=>{
 const rows=fixture([{event:'execution.completed',operation:'reception.accept',outcome:'unexpected_error',counts:null},{event:'execution.completed',operation:'reception.accept'},{event:'reception.completed',operation:'reception.accept',counts:{records_seen:5,records_accepted:5,records_invalid:0,records_duplicate:0,records_other_rejected:0}}]);
 const result=reconcile(rows,options());assert.equal(result.measures.operations_total,1);assert.equal(result.measures.attempt_executions_total,2);assert.equal(result.measures.records_accepted,5);assert.equal(result.measures.unexpected_error_percent,0);assert.equal(result.measures.execution_unexpected_error_percent,50);
});
test('empty verified window is zero; percentages N/D; no heartbeat is unknown and N/D',()=>{
 const good=reconcile(fixture(),options());assert.equal(good.measures.operations_total,0);assert.equal(good.measures.unexpected_error_percent,null);
 const absent=reconcile([],options());assert.equal(absent.logs,'unknown');assert.equal(absent.measures.operations_total,null);
});
test('durations100/200/300 produce mean200,p50200,p95290; null is excluded',()=>{
 const result=reconcile(fixture([100,200,300,null].map(duration_ms=>({duration_ms}))),options());assert.equal(result.measures.processing_duration_mean_ms,200);assert.equal(result.measures.processing_duration_p50_ms,200);assert.equal(result.measures.processing_duration_p95_ms,290);
});
test('adjacent ns boundaries assign an event once',()=>{
 const rows=fixture([{timestamp:'2026-11-24T00:01:00.000000000Z'},{timestamp:'2026-11-24T00:01:29.999999999Z'},{timestamp:'2026-11-24T00:01:30.000000000Z'}]);
 assert.equal(reconcile(rows,options()).measures.operations_total,2);
 assert.equal(reconcile(rows,options({startNs:end,endNs:end+1000000000n})).measures.operations_total,1);
});
test('known losses and missing sequence remain partial; recovery cannot fill a historical gap',()=>{
 const rows=fixture([{},{}]);rows[2].sequence++;rows[3].sequence++;rows.at(-1).health.logs_dropped_total=1;
 const result=reconcile(rows,options());assert.equal(result.logs,'partial');assert.equal(result.measures.unexpected_error_percent,null);assert.equal(result.deltas.logs_dropped_total,1);
});
test('exact reread is deduplicated; conflicting body or lost positions forbid exact totals',()=>{
 const rows=fixture([{}]);assert.equal(reconcile([...rows,rows[1]],options()).measures.operations_total,1);
 assert.equal(reconcile([...rows,{...rows[1],outcome:'unexpected_error'}],options()).logs,'partial');
 assert.equal(reconcile(rows,options({positionsKnown:false})).logs,'unknown');
});
test('logs and traces use independent failure evidence',()=>{
 const rows=fixture([{}]);
 const noTraces=reconcile(rows,options({traceEvidence:{reachable:false,ids:new Set()}}));assert.equal(noTraces.logs,'complete');assert.equal(noTraces.traces,'unknown');
 const noLogs=reconcile(rows,options({logsReachable:false,expectedTraceIds:new Set(),traceEvidence:{reachable:true,ids:new Set(['123'])}}));assert.equal(noLogs.logs,'unknown');assert.equal(noLogs.traces,'complete');assert.equal(noLogs.queryableTraces,1);
 const sampled=reconcile(rows,options({traceRatio:.1}));assert.equal(sampled.logs,'complete');assert.equal(sampled.traces,'partial');
});
test('restarts/resets are not summed snapshots; bad metadata and10000rows are unknown',()=>{
 const rows=fixture([{}]);rows.at(-1).boot_id='boot-b';rows.at(-1).sequence=1;rows.at(-1).health.logs_dropped_total=3;
 const result=reconcile(rows,options());assert.equal(result.logs,'partial');assert.equal(result.deltas.logs_dropped_total,3);
 assert.equal(reconcile(Array(10000).fill(rows[0]),options()).logs,'unknown');
});
test('45s missing heartbeat and open windows remain provisional',()=>{
 const rows=fixture([{}]);rows.at(-1).timestamp='2026-11-24T00:02:00Z';assert.equal(reconcile(rows,options()).logs,'unknown');
 assert.equal(reconcile(fixture([{}]),options({nowNs:end})).logs,'unknown');
});
test('export confirmation alone is insufficient; missing persisted references are partial',()=>{
 const rows=fixture([{trace_id:'a'.repeat(32)}]);const result=reconcile(rows,options());assert.equal(result.traces,'partial');assert.ok(result.traceCauses.includes('trazas_esperadas_ausentes'));
 const complete=reconcile(rows,options({traceEvidence:{reachable:true,ids:new Set(['a'.repeat(32)])}}));assert.equal(complete.traces,'complete');
});
test('catalog dimensions exclude IDs; Jaeger OTLP hex/base64 are interpreted as references only',()=>{
 assert.deepEqual(DIMENSIONS,['service_name','environment','operation','outcome','severity']);
 assert.ok(jaegerReferences({result:{resourceSpans:[{scopeSpans:[{spans:[{traceId:'a'.repeat(32)}]}]}]}}).ids.has('a'.repeat(32)));
 assert.throws(()=>jaegerReferences({}),/unknown/);
});

test('native metric replay inflation is visible as partial while unique logical records stay exact',()=>{
 const rows=fixture(Array.from({length:1000},()=>({})));
 const result=reconcile(rows,options({logicalAggregate:1001}));
 assert.equal(result.measures.operations_total,1000);assert.equal(result.logs,'partial');
 assert.equal(result.measures.unexpected_error_percent,null);assert.ok(result.causes.includes('replay_en_agregado'));
});
