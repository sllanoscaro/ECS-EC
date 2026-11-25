/**008 real rule workspace: one question first—what is configured and when will it run? */
"use client";
import {useEffect,useRef,useState} from 'react';
import {SessionGuard} from '../identity/SessionProvider';
import {useBuildingTimezone} from '../identity/ApplicationFrame';
import {notificationsApi,type Rule,type RulePage,type Catalog,type RecipientPage} from '../../lib/api/notifications';
import {consumptionApi} from '../../lib/api/consumption';
import type {Catalog as ConsumptionCatalog} from '../../lib/api/consumption-types';
import {RuleEditor} from './RuleEditor';

/**Never mount administrative data access before the current006 management grant is known. */
export function RuleList(){return <SessionGuard permission="notifications.rules.manage" returnTo="/notificaciones/reglas/"><Workspace/></SessionGuard>;}

/**Share existing shell/type/palette; master/detail is two columns only while both retain usable width. */
function Workspace(){
 const [page,setPage]=useState<RulePage|null>(null),[catalog,setCatalog]=useState<Catalog|null>(null),[recipients,setRecipients]=useState<RecipientPage|null>(null),[sources,setSources]=useState<ConsumptionCatalog|null>(null);
 const [selected,setSelected]=useState<Rule|undefined>(),[busy,setBusy]=useState(true),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 const generation=useRef(0);
 useBuildingTimezone(sources?.timezone);
 useEffect(()=>{
  /**Abort and discard all stale/private loads; list failure is never rendered as an empty successful result. */
  const epoch=++generation.current,controller=new AbortController();setBusy(true);setError('');
  Promise.all([notificationsApi.rules({},controller.signal),notificationsApi.catalog(controller.signal),notificationsApi.recipients(['recepcion'],controller.signal),consumptionApi.catalog(controller.signal)]).then(async([rules,types,accounts,source])=>{
   const identifier=new URLSearchParams(window.location.search).get('regla');const current=identifier?await notificationsApi.rule(identifier,controller.signal):undefined;
   if(epoch===generation.current){setPage(rules);setCatalog(types);setRecipients(accounts);setSources(source);setSelected(current);setBusy(false);}
  }).catch(()=>{if(epoch===generation.current){setBusy(false);setError('No se pudieron consultar las reglas y sus fuentes.');}});
  return ()=>{generation.current++;controller.abort();};
 },[refresh]);
 /**Selecting one persisted object never writes a configuration revision. */
 async function choose(rule?:Rule){setError('');try{const value=rule?await notificationsApi.rule(rule.id):undefined;setSelected(value);const url=new URL(window.location.href);if(value)url.searchParams.set('regla',value.id);else url.searchParams.delete('regla');window.history.replaceState(null,'',url);document.querySelector<HTMLElement>('.notification-editor h2')?.focus();}catch{setError('No se pudo consultar la regla seleccionada.');}}
 /**Only confirmed mutations replace selected metadata; subsequent reads preserve its identity. */
 function saved(rule:Rule){setSelected(rule);setPage(current=>current?{...current,items:current.items.some(r=>r.id===rule.id)?current.items.map(r=>r.id===rule.id?rule:r):[...current.items,rule]}:current);const url=new URL(window.location.href);url.searchParams.set('regla',rule.id);window.history.replaceState(null,'',url);}
 /**Append one stable server page; never invent a total beyond the known rows. */
 async function more(){if(!page?.next_cursor)return;try{const next=await notificationsApi.rules({cursor:page.next_cursor});setPage(current=>current?{...next,items:[...current.items,...next.items]}:next);}catch{setError('No se pudieron consultar más reglas.');}}
 if(busy)return <p role="status">Consultando reglas y cuentas…</p>;
 if(error&&!catalog)return <section role="alert"><p>{error}</p><button onClick={()=>setRefresh(r=>r+1)}>Reintentar consulta</button></section>;
 return <><div className="notification-toolbar"><a href="/notificaciones/">Ver entregas</a><button onClick={()=>void choose()}>Nueva regla</button><button onClick={()=>setRefresh(r=>r+1)}>Actualizar reglas</button></div>{error&&<p role="alert">{error}<button onClick={()=>setRefresh(r=>r+1)}>Reintentar consulta</button></p>}
 <div className="notification-workspace"><section className="notification-rule-list" aria-label="Reglas configuradas"><h2>Reglas configuradas</h2>{page&&!page.items.length?<p>No hay reglas configuradas. Cree la primera; se guardará desactivada.</p>:<ul>{page?.items.map(rule=><li key={rule.id} data-selected={selected?.id===rule.id}><button onClick={()=>void choose(rule)} aria-pressed={selected?.id===rule.id}><strong>{rule.config.name}</strong><span>{rule.status} · versión {rule.version_number}</span><span>{rule.next_due_at??'Sin fecha programada'}</span></button></li>)}</ul>}{page?.next_cursor&&<button onClick={()=>void more()}>Cargar más reglas</button>}</section>
 {catalog&&recipients&&sources&&<RuleEditor key={selected?`${selected.id}:${selected.revision}`:'new'} current={selected} catalog={catalog} recipients={recipients.items} categories={sources.categories} timezone={sources.timezone} onSaved={saved} onReload={()=>void choose(selected)}/>}</div></>;
}
