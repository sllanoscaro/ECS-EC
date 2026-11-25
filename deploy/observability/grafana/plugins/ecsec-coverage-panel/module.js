/**007 hand-authored Grafana SystemJS panel. No generated bundle or remote dependency.
 * React and PanelPlugin are supplied by the pinned Grafana installation.
 * Only existing per-request-authorized technical endpoints are queried; no credentials
 * are retained, no business API is exposed and no additional service is deployed.
 */
System.register(['react', '@grafana/data'], function(exports) {
  let React, PanelPlugin;
  return {
    setters: [function(module) { React=module.default ?? module; }, function(module) { PanelPlugin=module.PanelPlugin; }],
    execute: function() {
      const h=React.createElement;
      const codeLabels={ok:'Completado',invalid_input:'Entrada rechazada',duplicate:'Duplicado',too_early:'Actualización anticipada',permission_denied:'Acceso denegado',authentication_failed:'Autenticación rechazada',file_unreadable:'Archivo ilegible',database_unavailable:'Persistencia no disponible',calculation_failed:'Cálculo fallido',pdf_failed:'Generación PDF fallida',processing_interrupted:'Procesamiento interrumpido',transport_unavailable:'Transporte no disponible',queue_full:'Cola llena',spool_full:'Spool lleno',schema_rejected:'Señal rechazada por esquema',sampling:'Muestreo de trazas',retention_expired:'Retención vencida',coverage_unknown:'Cobertura desconocida',unclassified:'Sin clasificación'};
      /**Fetch one finite authorized technical response; failure never fabricates an empty result. */
      async function query(path, parameters, signal) {
        const response=await fetch(path+'?'+new URLSearchParams(parameters),{signal,credentials:'same-origin',cache:'no-store'});
        if (response.status===404 && path.startsWith('/jaeger/'))return {result:{resourceSpans:[]}};
        if (!response.ok) throw Error('consulta_no_disponible');
        return response.json();
      }
      /**Load a bounded common cut from Loki and a separate Jaeger query, independently of Grafana's data frames. */
      async function load(props, signal) {
        const core=await import('/grafana/public/plugins/ecsec-coverage-panel/reconcile.mjs');
        const start=BigInt(props.timeRange.from.valueOf())*1000000n, end=BigInt(props.timeRange.to.valueOf())*1000000n, now=BigInt(Date.now())*1000000n;
        const environment=props.replaceVariables('$environment');
        if (!['local','test','vps'].includes(environment))throw Error('entorno_no_configurado');
        const expression='{service_name="ecs-ec",environment="'+environment+'"}';
        let rows=[],logsReachable=true,truncated=false;
        try {
          // Three bounded queries preserve the full24h choice without widening any backend window beyond24h.
          for (const [lower,upper] of [[start-45000000000n,start],[start,end-1n],[end,end+45000000000n<now?end+45000000000n:now]]) {
            if (upper<lower)continue;
            const part=core.lokiRows(await query('/logs/loki/api/v1/query_range',{query:expression,start:lower.toString(),end:upper.toString(),limit:'10000',direction:'forward'},signal));
            if (part.length>=10000)truncated=true;
            rows.push(...part);
          }
        } catch {logsReachable=false;}
        let traceEvidence={reachable:false,ids:new Set()};
        try {
          const data=await query('/jaeger/api/v3/traces',{'query.serviceName':'ecs-ec','query.startTimeMin':new Date(Number(start/1000000n)).toISOString(),'query.startTimeMax':new Date(Number(end/1000000n)).toISOString(),'query.searchDepth':'10000'},signal);
          const refs=core.jaegerReferences(data);
          traceEvidence={reachable:true,ids:refs.ids,truncated:refs.count>=10000};
        } catch { /* Keep independent trace evidence unavailable; never infer it from Alloy. */ }
        let logicalAggregate, aggregateQueryReachable=true;
        try {
          const logical=expression+' | json terminal="event" | (terminal="operation.completed" and operation!="report.generate") or terminal="reception.completed" or terminal="report.completed" or terminal="notification.operation.completed" | __error__=""';
          const raw=await query('/logs/loki/api/v1/query',{query:'sum(count_over_time('+logical+' ['+((end-start)/1000000n).toString()+'ms]))',time:(end-1n).toString()},signal);
          logicalAggregate=raw.data.result.length?Number(raw.data.result[0].value[1]):0;
        } catch {aggregateQueryReachable=false;}
        const operation=props.replaceVariables('$operation'),outcome=props.replaceVariables('$outcome'),severity=props.replaceVariables('$severity');
        const result=core.reconcile(rows,{startNs:start,endNs:end,nowNs:now,environment,revision:props.options.revision??'007-v1',retentionHours:environment==='test'?24:168,traceRatio:props.options.traceRatio??1,reference:props.replaceVariables('$operation_ref')==='.*'?null:props.replaceVariables('$operation_ref'),logsReachable,truncated,traceEvidence,logicalAggregate,aggregateQueryReachable,operation:operation==='.*'?null:operation,outcome:outcome==='.*'?null:outcome,severity:severity==='.*'?null:severity});
        const reference=props.replaceVariables('$operation_ref');
        if (reference && reference!=='.*')result.events=result.events.filter(event=>event.operation_ref===reference || event.publication_ref===reference);
        return {...result,environment,traceEvidence};
      }
      /**Render real observed measures with coverage first, one retry and a bounded diagnostic list. */
      function ContinuityPanel(props) {
        const [state,setState]=React.useState({loading:true}),[revision,setRevision]=React.useState(0);
        React.useEffect(function() {
          const controller=new AbortController();let active=true;
          setState(previous=>({...previous,loading:true,error:false}));
          load(props,controller.signal).then(function(data){if(active)setState({data,loading:false});}).catch(function(){if(active)setState(previous=>({...previous,loading:false,error:true}));});
          return function(){active=false;controller.abort();};
        },[props.timeRange.from.valueOf(),props.timeRange.to.valueOf(),props.replaceVariables('$environment $operation $outcome $severity $operation_ref'),revision]);
        const data=state.data, m=data?.measures ?? {};
        /**Format missing evidence as N/D; observed zero remains a zero. */
        function number(value) {return value===null||value===undefined?'N/D':new Intl.NumberFormat('es-CL',{maximumFractionDigits:2}).format(value);}
        /**Build an aligned metric row whose unit and denominator are stated beside its value. */
        function row(label,value,unit) {return h('tr',{key:label},h('td',{style:{padding:'6px 12px 6px 0',width:'40%' }},label),h('td',{style:{textAlign:'right',width:'15%',fontVariantNumeric:'tabular-nums',padding:'6px'}},number(value)),h('td',{style:{padding:'6px',opacity:.85}},unit));}
        const terminal=data?.events.filter(event=>['operation.completed','reception.completed','report.completed','execution.completed','notification.operation.completed'].includes(event.event)).slice(-6) ?? [];
        return h('section',{'aria-label':'Continuidad ECS-EC',style:{height:'100%',overflow:'auto',overflowWrap:'anywhere',padding:'4px 8px',fontSize:'14px'}},
          h('div',{style:{display:'flex',gap:'12px',justifyContent:'space-between',alignItems:'center'}},
            h('strong',null,data?'Logs: '+data.logs+' · Trazas: '+data.traces:'Sin evidencia · cobertura unknown'),
            h('button',{type:'button',onClick:function(){setRevision(value=>value+1);},style:{background:'transparent',color:'inherit',border:'1px solid currentColor',borderRadius:'4px',padding:'4px 10px',whiteSpace:'nowrap',flexShrink:0}},'Reintentar')),
          state.loading?h('p',{role:'status'},'Consultando señales…'):null,
          state.error?h('p',{role:'alert'},'No se pudo actualizar la consulta. Los valores anteriores conservan su corte; la cobertura actual es desconocida.'):null,
          h('p',null,data?'UTC ['+new Date(Number(BigInt(data.windowStart)/1000000n)).toISOString()+', '+new Date(Number(BigInt(data.windowEnd)/1000000n)).toISOString()+') · Corte '+new Date(Number(BigInt(data.cutoff)/1000000n)).toISOString():'Ventana UTC de Grafana · sin consulta confirmada'),
          h('p',null,'Dashboard incluye configuración esperada aunque nunca haya llegado una señal. Política '+(props.options.revision??'007-v1')+'; trazas '+(props.options.traceRatio??1)+'; retención local/VPS168h, test24h.'),
          data?h('p',null,'Entorno '+data.environment+' · versión '+(data.versions.join(', ')||'sin evidencia')+' · último heartbeat '+(data.lastHeartbeat??'no disponible')+' · edad '+number(data.heartbeatAgeSeconds)+' s'):null,
          data?h('p',null,'Logs: '+(data.causes.join(', ')||'secuencias y transporte conciliados')+'. Trazas: '+(data.traceCauses.join(', ')||'referencias esperadas consultables')+'. '+number(data.queryableTraces)+' trazas consultables.'):null,
          h('table',{style:{width:'100%',maxWidth:'800px',tableLayout:'fixed'}},h('colgroup',null,h('col',{style:{width:'42%'}}),h('col',{style:{width:'18%'}}),h('col',{style:{width:'40%'}})),h('thead',null,h('tr',null,h('th',{style:{textAlign:'left'}},'Medida observada'),h('th',{style:{textAlign:'right'}},'Valor'),h('th',{style:{textAlign:'left'}},'Unidad / denominador'))),h('tbody',null,
            row('Operaciones terminadas',m.operations_total,'operaciones lógicas'),row('Error inesperado',m.unexpected_error_percent,'% de operaciones; N/D sin cobertura completa'),
            row('Ejecuciones',m.attempt_executions_total,'execution.completed'),row('Error por ejecución',m.execution_unexpected_error_percent,'% de ejecuciones; denominador separado'),
            row('Generaciones admitidas',m.report_generations_admitted,'report.admitted; excluye replay HTTP'),
            row('Posiciones / novedades',m.records_seen,'registros evaluados'),row('Novedades confirmadas',m.records_accepted,'registros aceptados'),row('Inválidos / duplicados',m.records_invalid,'inválidos; duplicados: '+number(m.records_duplicate)),
            row('Archivos evaluados',m.files_seen,'archivos; ilegibles: '+number(m.files_unreadable)),row('Duración media / p50 / p95',m.processing_duration_mean_ms,'ms / '+number(m.processing_duration_p50_ms)+' / '+number(m.processing_duration_p95_ms)),
            row('Cola de logs / trazas',data?.queueDepth,'eventos / '+number(data?.spanQueueDepth)+' spans; límites1024/2048'),
            row('Descartes en emisor',data?.deltas.logs_dropped_total,'eventos; delta entre heartbeats del corte'),
            row('Descartes en spool',data?.deltas.spool_dropped_total,'eventos; incluye rotación y TTL'),
            row('Descartes en recolección',data?.deltas.collector_dropped_total,'eventos; delta Alloy'),
            row('Rechazos de esquema',data?.deltas.schema_rejected_total,'eventos; delta antes de admisión'),
            row('Descartes de spans',data?.deltas.spans_dropped_total,'spans; delta del corte'),
            row('Fallos de exportación',data?.deltas.trace_export_failures_total,'lotes; no multiplicar por reintento'),
            row('Reinicios de recolector',data?.deltas.collector_restarts_total,'procesos; limita continuidad'))) ,
          h('p',null,'Los valores son observados. Una señal ausente no prueba que nunca hubo operación. Una confirmación OTLP no prueba persistencia consultable.'),
          h('ul',{style:{paddingLeft:'18px'}},...terminal.map(function(event){
            const available=event.trace_id && data.traceEvidence.ids.has(event.trace_id);
            const url=new URL(window.location.href);url.searchParams.set('var-operation_ref',event.operation_ref??'.*');
            return h('li',{key:event.event_id,style:{marginBottom:'8px',overflowWrap:'anywhere'}},event.operation+' · '+event.outcome+' · '+event.stage+' · '+(codeLabels[event.code]??codeLabels.unclassified)+' · '+event.timestamp+' ',
              available?h('a',{href:'/jaeger/trace/'+event.trace_id,target:'_blank',rel:'noopener noreferrer'},'Ver traza'):h('span',null,'Traza no disponible: muestreo, retención o entrega incompleta.'),' · ',
              h('a',{href:url.pathname+url.search},'Otras ejecuciones '+(event.operation_ref??'sin contexto')));
          })));
      }
      exports('plugin',new PanelPlugin(ContinuityPanel));
    }
  };
});
