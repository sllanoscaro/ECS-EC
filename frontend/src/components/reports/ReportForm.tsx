/**005 calendar selection and race-safe private state, integrated with006 cleanup and background polling. */
'use client';
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {createReport,reportStatus,type Report,type Selection} from '../../lib/api/reports';
import {Problem,subscribePrivateCleanup} from '../../lib/api/session';
import {ReportStatus} from './ReportStatus';
import {consumptionApi} from '../../lib/api/consumption';

/** Select a full calendar period and preserve inputs during errors, generation and session revalidation. */
export function ReportForm() {
 const edited=useRef(false);
 const [scale,setScale]=useState<Selection['scale']>('mensual');
 const [date,setDate]=useState('');const [year,setYear]=useState('');const [month,setMonth]=useState('');
 const [zone,setZone]=useState('');
 const [report,setReport]=useState<Report|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [refresh,setRefresh]=useState(0);const generation=useRef(0);const key=useRef<{body:string;value:string}|null>(null);
 useEffect(()=>subscribePrivateCleanup(()=>{generation.current++;setReport(null);setZone('');setError('');setBusy(false);key.current=null;}),[]);
 useEffect(()=>{
  /** Read the authoritative building timezone without inventing one from the browser or build host. */
  const controller=new AbortController();const epoch=generation.current;
  void consumptionApi.catalog(controller.signal).then(value=>{if(epoch===generation.current)setZone(value.timezone);}).catch(()=>{});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{
  /** A static query parameter selects a private server result without embedding it in the exported page. */
  const id=new URLSearchParams(window.location.search).get('reporte');
  if(!id||!/^[-a-f0-9]{36}$/i.test(id))return;
  const epoch=generation.current;const controller=new AbortController();
  void reportStatus(id,controller.signal).then(value=>{if(epoch===generation.current){setReport(value);if(!edited.current){setScale(value.scale);const parts=new Intl.DateTimeFormat('en-CA',{timeZone:value.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(value.window.start));const part=(type:string)=>parts.find(p=>p.type===type)?.value??'';setYear(part('year'));setMonth(String(Number(part('month'))));setDate(`${part('year')}-${part('month')}-${part('day')}`);}}}).catch(failure=>{if(!controller.signal.aborted&&epoch===generation.current)setError(failure instanceof Problem?failure.message:'No se pudo consultar el documento.');});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{
  /** Only pending work polls; cleanup and request ordering prevent obsolete results from reappearing. */
  if(!report||!['pendiente','generando'].includes(report.state))return;
  const controller=new AbortController();const epoch=generation.current;
  const timer=setTimeout(()=>{void reportStatus(report.id,controller.signal).then(value=>{if(epoch===generation.current){setReport(value);setRefresh(n=>n+1);}}).catch(failure=>{if(!controller.signal.aborted&&epoch===generation.current)setError(failure instanceof Problem?failure.message:'No se pudo actualizar el estado. Use Actualizar estado.');});},1000);
  return ()=>{clearTimeout(timer);controller.abort();};
 },[report,refresh]);
 async function submit(event:FormEvent<HTMLFormElement>) {
  /** Retain a key across uncertain HTTP failures; an explicit new generation after admission gets a new identity. */
  event.preventDefault();if(busy)return;
  const selection:Selection=scale==='diario'?{scale,date}:scale==='mensual'?{scale,year:Number(year),month:Number(month)}:{scale,year:Number(year)};
  const body=JSON.stringify(selection);if(!key.current||key.current.body!==body)key.current={body,value:crypto.randomUUID()};
  const epoch=++generation.current;setBusy(true);setError('');setReport(null);
  try {const value=await createReport(selection,key.current.value);if(epoch!==generation.current)return;key.current=null;setReport(value);const url=new URL(window.location.href);url.searchParams.set('reporte',value.id);window.history.replaceState(null,'',url);}
  catch(failure){if(epoch===generation.current)setError(failure instanceof Problem?(failure.code==='future_period'?'El período todavía no comienza. Seleccione otro día, mes o año.':failure.message):'No se pudo confirmar la solicitud. Reintente para recuperar la misma petición.');}
  finally{if(epoch===generation.current)setBusy(false);}
 }
 const pending=report&&['pendiente','generando'].includes(report.state);
 return <>
  <p className="account-description">Elija un día, mes o año. El PDF reúne consumo, cobertura y costos en una página A4, con el corte de datos indicado.</p>
  <section className="panel" aria-labelledby="report-period-title"><h2 id="report-period-title">Período del reporte</h2>{zone&&<p className="report-help">Zona horaria del edificio: {zone}</p>}
   <form className="report-form" onSubmit={submit}>
    <label>Tipo de reporte<select value={scale} onChange={e=>{edited.current=true;setScale(e.target.value as Selection['scale']);}}><option value="diario">Diario</option><option value="mensual">Mensual</option><option value="anual">Anual</option></select></label>
    {scale==='diario'?<label>Fecha<input required type="date" value={date} onChange={e=>{edited.current=true;setDate(e.target.value);}}/></label>:<label>Año<input required type="number" min="1" max="9998" value={year} onChange={e=>{edited.current=true;setYear(e.target.value);}}/></label>}
    {scale==='mensual'&&<label>Mes<select required value={month} onChange={e=>{edited.current=true;setMonth(e.target.value);}}><option value="">Seleccione un mes</option>{Array.from({length:12},(_,i)=><option key={i} value={i+1}>{new Intl.DateTimeFormat('es-CL',{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2024,i,1)))}</option>)}</select></label>}
    <button type="submit" disabled={busy||!!pending}>{busy?'Confirmando solicitud…':'Generar PDF'}</button>
   </form>
   <p className="report-help">Los períodos en curso incluyen información provisional. Los períodos futuros no están disponibles.</p>
   {error&&<p role="alert" className="notice">{error}</p>}
  </section>
  {report&&<ReportStatus report={report} onRefresh={()=>setRefresh(n=>n+1)}/>}
 </>;
}
