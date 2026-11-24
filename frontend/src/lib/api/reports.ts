/**005 same-origin report client; only metadata travels through JSON, never private PDF bytes at build time. */
import { apiRequest, sessionActivityHeaders } from './session';
export type Selection = {scale:'diario';date:string}|{scale:'mensual';year:number;month:number}|{scale:'anual';year:number};
export type Report = {id:string;scale:Selection['scale'];window:{start:string;end:string};timezone:string;cutoff_at:string;state:'pendiente'|'generando'|'generado'|'fallido';download_path:string|null;created_at?:string;issued_at?:string|null;filename?:string|null;functional_reason_code?:string|null;sha256?:string|null;byte_length?:number|null};
/** Admit one explicit generation; keep the same key when retrying a request whose response was lost. */
export function createReport(selection:Selection,key:string) {return apiRequest<Report>('/reports',{method:'POST',headers:{'Idempotency-Key':key,...sessionActivityHeaders('interactive')},body:JSON.stringify(selection)});}
/** Polling defaults to background and cannot extend a session's idle deadline. */
export function reportStatus(id:string,signal?:AbortSignal) {return apiRequest<Report>(`/reports/${encodeURIComponent(id)}`,{signal});}
/** Download through006's shared current-session/error handling; object URLs never become public server resources. */
export function downloadReport(id:string) {return apiRequest<Blob>(`/reports/${encodeURIComponent(id)}/download`,{headers:sessionActivityHeaders('interactive')},async response=>{
 if(!response.headers.get('Content-Type')?.startsWith('application/pdf'))throw new Error('invalid_document');
 return response.blob();
});}
