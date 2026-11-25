/**007 bounded reconciliation: immutable Loki rows, independent Jaeger evidence, UTC nanoseconds.
 * Pure functions; no credentials, storage, ingestion, business API or UUID dimensions.
 * Counts are observed; only a fully reconciled closed window supports exact totals/ratios.
 */
export const DIMENSIONS = ['service_name', 'environment', 'operation', 'outcome', 'severity'];
export const TERMINALS = ['operation.completed', 'reception.completed', 'report.completed', 'notification.operation.completed'];
const SECOND = 1000000000n;

/**Parse RFC3339 UTC without losing the fractional nanoseconds at adjacent boundaries. */
export function timestampNs(value) {
  const match = /^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z$/.exec(value ?? '');
  if (!match) throw Error('invalid_timestamp');
  const seconds = Date.parse(match[1] + 'Z');
  if (!Number.isFinite(seconds)) throw Error('invalid_timestamp');
  return BigInt(seconds) * 1000000n + BigInt((match[2] ?? '').padEnd(9, '0'));
}

/**Flatten a bounded Loki response, preserving each immutable line and its stored timestamp. */
export function lokiRows(payload) {
  if (payload?.status !== 'success' || payload?.data?.resultType !== 'streams') throw Error('query_failed');
  return payload.data.result.flatMap(stream => stream.values.map(([ns, line]) => ({ ...JSON.parse(line), storedNs: ns, original: line })));
}

/**Return root trace references from Jaeger v3 OTLP JSON; reject malformed/truncated envelopes. */
export function jaegerReferences(payload) {
  const groups = payload?.result?.resourceSpans ?? payload?.resourceSpans;
  if (!Array.isArray(groups)) throw Error('trace_evidence_unknown');
  const ids = new Set();
  let count = 0;
  for (const group of groups) for (const scope of group.scopeSpans ?? []) for (const span of scope.spans ?? []) {
    count++;
    if (/^[a-f0-9]{32}$/i.test(span.traceId ?? '')) ids.add(span.traceId.toLowerCase());
    else if (span.traceId) {
      // OTLP's protobuf JSON encodes bytes as base64; browser/Node share atob.
      const raw = atob(span.traceId);
      if (raw.length !== 16) throw Error('trace_evidence_unknown');
      ids.add(Array.from(raw, char => char.charCodeAt(0).toString(16).padStart(2, '0')).join(''));
    }
  }
  return { ids, count };
}

/**Quantile with linear interpolation, matching observed Loki quantiles; no averaging percentiles. */
export function quantile(values, ratio) {
  if (!values.length) return null;
  const sorted = [...values].sort((a,b) => a-b), index = (sorted.length-1)*ratio;
  const low = Math.floor(index), high = Math.ceil(index);
  return sorted[low] + (sorted[high]-sorted[low])*(index-low);
}

/**Separate logical transitions from executions and preadmission005 diagnostics. */
export function isLogical(event) {
  return TERMINALS.includes(event.event) && !(event.operation === 'report.generate' && event.event === 'operation.completed');
}

/**Evaluate one bounded closed window; uncertainty survives recovered transport and later heartbeats.
 * options includes expected policy/retention, independent query statuses, and typed trace evidence.
 * Returning partial/unknown never upgrades observed counters into complete business accounting.
 */
export function reconcile(input, options) {
  const { startNs, endNs, nowNs, environment, revision = '007-v1', retentionHours = 168, traceRatio = 1 } = options;
  const start=BigInt(startNs), end=BigInt(endNs), now=BigInt(nowNs);
  if (start >= end || end-start > 86400n*SECOND) throw Error('invalid_window');
  const causes = [], traceCauses = [];
  let logs = 'complete', traces = 'complete';
  /**Apply the most conservative evidence state; unknown dominates a known loss. */
  function limit(signal, state, cause) {
    const list=signal==='logs'?causes:traceCauses;
    if (!list.includes(cause)) list.push(cause);
    if (signal === 'logs') logs=logs==='unknown'||state==='unknown'?'unknown':'partial';
    else traces=traces==='unknown'||state==='unknown'?'unknown':'partial';
  }
  if (options.logsReachable === false) limit('logs','unknown','consulta_logs_fallida');
  if (input.length >= 10000 || options.truncated) limit('logs','unknown','limite_10000');
  if (options.positionsKnown === false) limit('logs','unknown','posiciones_no_verificables');
  if (end > now || end > now-45n*SECOND) limit('logs','unknown','ventana_provisional');
  if (start < now-BigInt(retentionHours)*3600n*SECOND) limit('logs','partial','retencion');
  const byId = new Map();
  for (const event of input) {
    if (event.environment !== environment) continue;
    if (!event.event_id || !event.boot_id || !Number.isSafeInteger(event.sequence) || event.sequence < 1) {
      limit('logs','unknown','evento_invalido'); continue;
    }
    const prior=byId.get(event.event_id);
    if (prior && (prior.original ?? JSON.stringify(prior)) !== (event.original ?? JSON.stringify(event))) limit('logs','partial','replay_ambiguo');
    else byId.set(event.event_id,event);
  }
  let events=[];
  try { events=[...byId.values()].map(event=>({...event,ns:timestampNs(event.timestamp)})).sort((a,b)=>a.ns<b.ns?-1:a.ns>b.ns?1:a.sequence-b.sequence); }
  catch { limit('logs','unknown','evento_invalido'); }
  const heartbeats=events.filter(event=>event.event==='telemetry.heartbeat');
  const before=heartbeats.filter(event=>event.ns<=start).at(-1), after=heartbeats.find(event=>event.ns>=end);
  const last=heartbeats.filter(event=>event.ns<=end).at(-1);
  if (!before || !after) limit('logs','unknown','sin_heartbeats_que_encuadren');
  const bracket=before&&after?events.filter(event=>event.ns>=before.ns&&event.ns<=after.ns):[];
  const beats=bracket.filter(event=>event.event==='telemetry.heartbeat');
  const lossFields=['logs_dropped_total','spool_dropped_total','schema_rejected_total','collector_dropped_total','collector_restarts_total'];
  const traceFields=['spans_dropped_total','trace_export_failures_total'];
  const deltas={};
  for (let index=0;index<bracket.length;index++) {
    const event=bracket[index], prior=bracket[index-1];
    if (event.policy_revision !== revision) { limit('logs','partial','politica_distinta'); limit('traces','partial','politica_distinta'); }
    if (prior && event.boot_id !== prior.boot_id) { limit('logs','partial','reinicio'); limit('traces','partial','reinicio'); }
    if (prior && event.boot_id === prior.boot_id && event.sequence !== prior.sequence+1) limit('logs','partial','hueco_secuencia');
  }
  for (let index=0;index<beats.length;index++) {
    const beat=beats[index], prior=beats[index-1], health=beat.health;
    if (!health) { limit('logs','unknown','salud_ausente'); limit('traces','unknown','salud_ausente'); continue; }
    if (prior && beat.ns-prior.ns>45n*SECOND) {limit('logs','unknown','heartbeat_mayor_45s');limit('traces','unknown','heartbeat_mayor_45s');}
    if (!health.collector_started_at) limit('logs','unknown','inicio_recolector_no_verificado');
    if (health.log_collector_status !== 'available' || !health.last_log_collector_success) limit('logs','unknown','recoleccion_no_verificada');
    if (health.trace_export_status==='degraded') limit('traces','partial','fallo_exportacion');
    for (const key of [...lossFields,...traceFields]) {
      const value=health[key], old=prior?.health?.[key];
      const signal=traceFields.includes(key)?'traces':'logs';
      if (!Number.isSafeInteger(value) || value < 0) {limit(signal,'unknown','contador_no_verificable');continue;}
      if (prior) {
        if (beat.boot_id===prior.boot_id && Number.isSafeInteger(old) && value<old) limit(signal,'unknown','reset_sin_arranque');
        const delta=beat.boot_id!==prior.boot_id?value:Number.isSafeInteger(old)?Math.max(0,value-old):0;
        deltas[key]=(deltas[key]??0)+delta;
        if (delta>0) limit(signal,'partial','perdidas_'+key);
      }
    }
  }
  if (!before || !after) limit('traces','unknown','sin_heartbeats_que_encuadren');
  if (end>now-45n*SECOND) limit('traces','unknown','ventana_provisional');
  if (start<now-BigInt(retentionHours)*3600n*SECOND) limit('traces','partial','retencion');
  if (traceRatio<1) limit('traces','partial','muestreo');
  const window=events.filter(event=>event.ns>=start&&event.ns<end);
  if (options.aggregateQueryReachable === false) limit('logs','unknown','consulta_agregado_no_verificada');
  if (typeof options.logicalAggregate === 'number' && options.logicalAggregate !== window.filter(isLogical).length) limit('logs','partial','replay_en_agregado');
  const filtered=window.filter(event=>(!options.reference||event.operation_ref===options.reference||event.publication_ref===options.reference)&&(!options.operation||event.operation===options.operation)&&(!options.outcome||event.outcome===options.outcome)&&(!options.severity||event.severity===options.severity));
  const expected=options.expectedTraceIds ?? (logs==='complete'?new Set(window.filter(event=>event.trace_id).map(event=>event.trace_id)):null);
  if (!options.traceEvidence?.reachable || options.traceEvidence?.truncated) limit('traces','unknown','consulta_trazas_no_verificada');
  else if (expected===null) limit('traces','unknown','referencias_esperadas_no_conciliadas');
  else if ([...expected].some(id=>!options.traceEvidence.ids.has(id))) limit('traces','partial','trazas_esperadas_ausentes');
  const logical=filtered.filter(isLogical), executions=filtered.filter(event=>event.event==='execution.completed');
  /**Only a known denominator from complete coverage permits a percentage. */
  function percentage(rows) {return logs==='complete'&&rows.length?100*rows.filter(event=>event.outcome==='unexpected_error').length/rows.length:null;}
  /**A zero is observed only with complete coverage; unknown summaries remain nullable. */
  function sum(rows,key) {
    const values=rows.map(event=>event.counts?.[key]).filter(value=>Number.isSafeInteger(value)&&value>=0);
    return values.length?values.reduce((a,b)=>a+b,0):logs==='complete'&&rows.length===0?0:null;
  }
  const receptions=filtered.filter(event=>event.event==='reception.completed');
  const files=filtered.filter(event=>event.operation==='acquisition.process'&&event.event==='operation.completed');
  const durations=logical.map(event=>event.duration_ms).filter(value=>typeof value==='number'&&Number.isFinite(value)&&value>=0);
  return {logs,traces,causes,traceCauses,events:filtered,windowStart:start.toString(),windowEnd:end.toString(),cutoff:now.toString(),lastHeartbeat:last?.timestamp??null,
    heartbeatAgeSeconds:last?Number(now-last.ns)/1e9:null,policyRevision:revision,versions:[...new Set(window.map(event=>event.service_version))],deltas,
    queryableTraces:options.traceEvidence?.ids?.size??null,queueDepth:last?.health?.log_queue_depth??null,spanQueueDepth:last?.health?.span_queue_depth??null,
    measures:{operations_total:logical.length||logs==='complete'?logical.length:null,attempt_executions_total:executions.length||logs==='complete'?executions.length:null,
      report_generations_admitted:filtered.filter(event=>event.event==='report.admitted').length||logs==='complete'?filtered.filter(event=>event.event==='report.admitted').length:null,
      unexpected_error_percent:percentage(logical),execution_unexpected_error_percent:percentage(executions),
      processing_duration_mean_ms:durations.length?durations.reduce((a,b)=>a+b,0)/durations.length:null,processing_duration_p50_ms:quantile(durations,.5),processing_duration_p95_ms:quantile(durations,.95),
      ...Object.fromEntries(['records_seen','records_accepted','records_invalid','records_duplicate','records_other_rejected'].map(key=>[key,sum(receptions,key)])),
      ...Object.fromEntries(['files_seen','files_parsed','files_unreadable'].map(key=>[key,sum(files,key)]))}};
}
