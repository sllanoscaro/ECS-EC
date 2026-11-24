/**005 readable report lifecycle; download links identify exactly one stored result and remain cookie-protected. */
import {useState,type MouseEvent} from 'react';
import {downloadReport,type Report} from '../../lib/api/reports';
const reasons:Record<string,string>={captura_no_disponible:'No fue posible capturar los datos.',composicion_no_admisible:'El contenido no cabe con la legibilidad requerida.',validacion_documento_fallida:'El documento no superó la comprobación de integridad.',generacion_interrumpida:'La generación se interrumpió.',generacion_no_completada:'La generación no pudo completarse.'};
/** Distinguish pending, running, failed and downloadable states without presenting partial files as success. */
export function ReportStatus({report,onRefresh}:{report:Report;onRefresh:()=>void}) {
 const [downloading,setDownloading]=useState(false);const [error,setError]=useState('');
 async function download(event:MouseEvent<HTMLAnchorElement>){
  /** Preserve the exact selected resource/name while applying shared session invalidation to download errors. */
  event.preventDefault();if(downloading)return;setDownloading(true);setError('');
  try {const blob=await downloadReport(report.id);const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=report.filename??'reporte.pdf';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  catch{setError('No se pudo descargar el documento. Compruebe su sesión y vuelva a intentarlo.');}
  finally{setDownloading(false);}
 }
 const display=(instant:string)=>{const value=new Date(instant);return Number.isNaN(value.getTime())?instant:new Intl.DateTimeFormat('es-CL',{dateStyle:'medium',timeStyle:'short',timeZone:report.timezone}).format(value);};
 const pending=report.state==='pendiente'||report.state==='generando';
 return <section className="panel report-result" aria-labelledby="report-result-title">
  <h2 id="report-result-title">{report.state==='generado'?'Documento disponible':report.state==='fallido'?'No se pudo generar el documento':'Preparando el documento'}</h2>
  <p role={report.state==='fallido'?'alert':'status'}>{pending?'La generación continúa. Puede conservar esta página mientras se prepara.':report.state==='fallido'?(reasons[report.functional_reason_code??'']??'Intente generar un nuevo documento con la misma selección.'):'El archivo conserva los datos y el corte de esta solicitud.'}</p>
  <dl className="report-facts"><div><dt>Período</dt><dd>{display(report.window.start)} — {display(report.window.end)} (fin excluido)</dd></div><div><dt>Zona horaria</dt><dd>{report.timezone}</dd></div><div><dt>Corte de datos</dt><dd>{display(report.cutoff_at)}</dd></div></dl>
  {report.state==='generado'&&report.download_path&&<a className="button" href={report.download_path} download={report.filename??true} onClick={download} aria-disabled={downloading}>{downloading?'Descargando…':'Descargar PDF'}</a>}
  {error&&<p role="alert">{error}</p>}
  {pending&&<button type="button" className="secondary" onClick={onRefresh}>Actualizar estado</button>}
 </section>;
}
