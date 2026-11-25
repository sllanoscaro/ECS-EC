/**008 static-route history workspace loads private captures only after a current006 session. */
"use client";
import {useEffect,useRef,useState} from 'react';
import {SessionGuard,useSession} from '../identity/SessionProvider';
import {useBuildingTimezone} from '../identity/ApplicationFrame';
import {notificationsApi,type DeliveryPage,type DeliveryDetail as Detail} from '../../lib/api/notifications';
import {DeliveryDetail,deliveryStates} from './DeliveryDetail';
import {HistoryFilters,type HistorySelection} from './HistoryFilters';
import {notificationInstant} from './presentation';
import {ResendDialog} from './ResendDialog';

/**An operator's own scope is enforced by the API and the current guard independently. */
export function DeliveryList(){return <SessionGuard permission="notifications.deliveries.read" returnTo="/notificaciones/"><Workspace/></SessionGuard>;}

/**A failed query and a successful empty own history have different, retryable states. */
function Workspace(){const {session}=useSession(),admin=!!session?.permissions.includes('notifications.rules.manage');const [resending,setResending]=useState(false);const [page,setPage]=useState<DeliveryPage|null>(null),[detail,setDetail]=useState<Detail|null>(null),[busy,setBusy]=useState(true),[error,setError]=useState(''),[filters,setFilters]=useState<HistorySelection>({}),[refresh,setRefresh]=useState(0);const sequence=useRef(0),selection=useRef(0);useBuildingTimezone(detail?.content.timezone);
useEffect(()=>{
 /**Abort stale list/detail responses and prevent private data from reappearing after unmount. */
 const epoch=++sequence.current,controller=new AbortController();selection.current++;setBusy(true);setError('');setDetail(null);setPage(null);
 notificationsApi.deliveries(filters,controller.signal).then(async result=>{const identifier=new URLSearchParams(window.location.search).get('entrega');const selected=identifier?await notificationsApi.delivery(identifier,controller.signal):null;if(epoch===sequence.current){setPage(result);setDetail(selected);setBusy(false);}}).catch(()=>{if(epoch===sequence.current){setBusy(false);setError('No se pudo consultar el historial autorizado.');}});
 return ()=>{sequence.current++;selection.current++;controller.abort();};
},[filters,refresh]);
/**Selecting history never retries delivery or changes its captured content. */
async function choose(id:string){const epoch=++selection.current;setDetail(null);setError('');try{const value=await notificationsApi.delivery(id);if(epoch!==selection.current)return;setDetail(value);const url=new URL(window.location.href);url.searchParams.set('entrega',id);window.history.replaceState(null,'',url);}catch{if(epoch===selection.current)setError('No se pudo consultar esa entrega con los permisos actuales.');}}
/**Append only a confirmed server page; pagination keeps the active filters. */
async function more(){if(!page?.next_cursor)return;const epoch=sequence.current;try{const next=await notificationsApi.deliveries({...filters,cursor:page.next_cursor});if(epoch===sequence.current)setPage(current=>current?{...next,items:[...current.items,...next.items]}:next);}catch{if(epoch===sequence.current)setError('No se pudo consultar la siguiente página.');}}
return <><div className="notification-toolbar">{admin&&<a href="/notificaciones/reglas/">Configurar reglas</a>}<button onClick={()=>setRefresh(r=>r+1)}>Actualizar historial</button></div><HistoryFilters admin={admin} onApply={setFilters}/>{busy&&<p role="status">Consultando entregas…</p>}{error&&<p role="alert">{error}<button onClick={()=>setRefresh(r=>r+1)}>Reintentar consulta</button></p>}{!busy&&page&&<div className="notification-workspace"><section className="notification-rule-list" aria-label="Entregas autorizadas"><h2>{admin?'Entregas':'Mis entregas'}</h2>{!page.items.length?<p>No hay entregas para este ámbito y filtros.</p>:<ul>{page.items.map(item=><li key={item.id} data-selected={detail?.delivery.id===item.id}><button onClick={()=>void choose(item.id)} aria-pressed={detail?.delivery.id===item.id}><strong>{item.rule_name}</strong><span>{deliveryStates[item.state]}</span><span title={item.created_at}>{notificationInstant(item.created_at)} UTC</span><span>Versión {item.rule_version} · {item.transport_kind==='local_prueba'?'Correo local de prueba':'Correo de producción'}</span></button></li>)}</ul>}{page.next_cursor&&<button onClick={()=>void more()}>Cargar más entregas</button>}</section>{detail?<DeliveryDetail detail={detail} onResend={admin?()=>setResending(true):undefined}/>:<p className="notification-editor">Seleccione una entrega para consultar su contenido e intentos.</p>}</div>}{resending&&detail&&admin&&<ResendDialog deliveryId={detail.delivery.id} onClose={()=>setResending(false)} onSent={id=>{setResending(false);void choose(id).then(()=>setRefresh(r=>r+1));}}/>}</>;}
