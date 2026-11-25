/**008 runtime client shares006 session/CSRF; action keys remain stable across retries and no private state is persisted. */
import { apiRequest, sessionActivityHeaders } from './session';
import type { Catalog, Rule, RuleInput, RulePage, RuleVersionPage, RecipientPage, Preview, DeliveryPage, DeliveryDetail, ResendRequest, ResendResult } from './notification-types';
export type * from './notification-types';

/**Build only approved scalar/list query parameters; every read still authorizes on the server. */
function query(values:Record<string,string|number|undefined>) {const query=new URLSearchParams();for(const [key,value] of Object.entries(values))if(value!==undefined&&value!=='')query.set(key,String(value));return query.size?'?'+query.toString():'';}
/**Keep mutation identity explicit and add only the supplied optimistic revision. */
function action(key:string,revision?:number) {return {...sessionActivityHeaders('interactive'),'Idempotency-Key':key,...(revision===undefined?{}:{'If-Match':`"${revision}"`})};}
export const notificationsApi={
 /**Read the fixed content/category catalog after current management permission. */
 catalog:(signal?:AbortSignal)=>apiRequest<Catalog>('/notifications/catalog',{signal}),
 /**List registered active accounts; source content governs eligibility, never arbitrary recipient addresses. */
 recipients:async(contents:ReadonlyArray<string>=['recepcion'],signal?:AbortSignal):Promise<RecipientPage>=>{const items:RecipientPage['items'][number][]=[];let cursor:string|null=null;do{const params=new URLSearchParams({limit:'100'});contents.forEach(value=>params.append('content_types',value));if(cursor)params.set('cursor',cursor);const page=await apiRequest<RecipientPage>('/notifications/recipients?'+params,{signal});items.push(...page.items);cursor=page.next_cursor;}while(cursor);return {items,next_cursor:null};},
 /**Page current rule heads with stable filter-bound cursors. */
 rules:(options:{status?:string;cursor?:string}={},signal?:AbortSignal)=>apiRequest<RulePage>('/notifications/rules'+query(options),{signal}),
 /**Read a selected rule by identity after fresh authorization. */
 rule:(id:string,signal?:AbortSignal)=>apiRequest<Rule>('/notifications/rules/'+encodeURIComponent(id),{signal}),
 /**Preview has no delivery side effects; configuration/cuentas/tzdata bind its expiring token. */
 preview:(body:RuleInput)=>apiRequest<Preview>('/notifications/rules/preview',{method:'POST',body:JSON.stringify(body)}),
 /**A save creates an inactive rule or an explicitly paused immutable revision. */
 save:(body:RuleInput,key:string,current?:Rule)=>apiRequest<Rule>('/notifications/rules'+(current?'/'+current.id:''),{method:current?'PUT':'POST',headers:action(key,current?.revision),body:JSON.stringify(body)}),
 /**Activation requires the preview of the exact persisted configuration. */
 activate:(current:Rule,token:string,key:string)=>apiRequest<Rule>('/notifications/rules/'+current.id+'/activate',{method:'POST',headers:action(key,current.revision),body:JSON.stringify({preview_token:token})}),
 /**Pause is bodyless and preserves all attempts already started. */
 pause:(current:Rule,key:string)=>apiRequest<Rule>('/notifications/rules/'+current.id+'/pause',{method:'POST',headers:action(key,current.revision)}),
 /**Read immutable definitions without treating a read as substantive revision. */
 versions:(id:string,cursor?:string,signal?:AbortSignal)=>apiRequest<RuleVersionPage>('/notifications/rules/'+id+'/versions'+query({cursor}),{signal}),
 /**Read own delivery scope; administrative recipient/rule filters remain server-controlled. */
 deliveries:(options:Record<string,string|undefined>={},signal?:AbortSignal)=>apiRequest<DeliveryPage>('/notifications/deliveries'+query(options),{signal}),
 /**Read an authorized immutable content capture and its actual attempts. */
 delivery:(id:string,signal?:AbortSignal)=>apiRequest<DeliveryDetail>('/notifications/deliveries/'+encodeURIComponent(id),{signal}),
 /**An explicit duplicate acknowledgement authorizes a new linked delivery; same action keeps its key. */
 resend:(id:string,body:ResendRequest,key:string)=>apiRequest<ResendResult>('/notifications/deliveries/'+id+'/resends',{method:'POST',headers:action(key),body:JSON.stringify(body)}),
};
