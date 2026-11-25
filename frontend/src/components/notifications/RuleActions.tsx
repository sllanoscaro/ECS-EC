/**008 explicit activation/pause and immutable version history; keys are reused if an uncertain HTTP response is retried. */
"use client";
import {useEffect,useRef,useState} from 'react';
import {notificationsApi,type Preview,type Rule,type RuleVersionPage} from '../../lib/api/notifications';
import {Problem} from '../../lib/api/session';
import {FormStatus} from './FormStatus';

/**Rule actions never infer permission from visibility; every call uses current006 state on the server. */
export function RuleActions({current,preview,dirty,onSaved}:{current:Rule;preview:Preview|null;dirty:boolean;onSaved:(value:Rule)=>void}) {
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[versions,setVersions]=useState<RuleVersionPage|null>(null);
 const [now,setNow]=useState(Date.now);useEffect(()=>{if(!preview)return;const timer=setTimeout(()=>setNow(Date.now()),Math.max(0,Date.parse(preview.expires_at)-Date.now()));return ()=>clearTimeout(timer);},[preview]);
 const keys=useRef<Record<string,string>>({});
 /**Retain a key for the same action/revision, preventing double mutations on lost responses. */
 async function run(kind:'activate'|'pause') {
  setBusy(true);setError('');const identity=kind+':'+current.revision;keys.current[identity]??=crypto.randomUUID();
  try{const value=kind==='activate'?await notificationsApi.activate(current,preview!.preview_token,keys.current[identity]):await notificationsApi.pause(current,keys.current[identity]);onSaved(value);}
  catch(failure){setError(failure instanceof Problem&&[409,412].includes(failure.status)?'La regla o su vista previa cambió. Recargue la versión vigente antes de continuar.':'No se pudo confirmar el cambio. Puede reintentar la misma acción.');}
  finally{setBusy(false);}
 }
 /**Read-only history has a separate failure state and never overwrites the editor's draft. */
 async function history(){setError('');try{setVersions(await notificationsApi.versions(current.id));}catch{setError('No se pudieron consultar las versiones.');}}
 async function moreVersions(){if(!versions?.next_cursor||busy)return;setBusy(true);setError('');try{const next=await notificationsApi.versions(current.id,versions.next_cursor);setVersions(value=>value?{...next,items:[...value.items,...next.items]}:next);}catch{setError('No se pudieron consultar más versiones.');}finally{setBusy(false);}}
 const ready=!!preview&&Date.parse(preview.expires_at)>Math.max(now,Date.now())&&!dirty;
 return <section aria-label="Estado de la regla"><p>Estado: <strong>{current.status}</strong> · versión {current.version_number}</p><p>Próxima fecha: {current.next_due_at??'No programada'}</p><div className="notification-actions">{current.status!=='activa'&&<button disabled={busy||!ready} onClick={()=>void run('activate')}>Activar regla</button>}{current.status==='activa'&&<button disabled={busy} onClick={()=>void run('pause')}>Pausar regla</button>}<button disabled={busy} onClick={()=>void history()}>Ver versiones</button></div>{!ready&&current.status!=='activa'&&<p>Guarde los cambios y obtenga una vista previa vigente para activar.</p>}<FormStatus busy={busy} error={error}/>{versions&&<ol aria-label="Versiones conservadas">{versions.items.map(v=><li key={v.id}>Versión {v.version_number} · {v.created_at}{v.retired_at?' · sustituida':''}</li>)}</ol>}{versions?.next_cursor&&<button disabled={busy} onClick={()=>void moreVersions()}>Cargar más versiones</button>}</section>;
}
