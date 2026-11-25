/**008 applicable-only calendar fields; changing recurrence constructs a closed variant, retaining the nominal anchor. */
"use client";
import type { Schedule } from '../../lib/api/notifications';

/**A UTC instant is explicit; local recurrence hour and IANA zone remain separate controls. */
export function ScheduleFields({value,onChange}:{value:Schedule;onChange:(value:Schedule)=>void}) {
 const local='local_time' in value?value.local_time:'06:00';
 /**Switch variants without leaving forbidden fields from the previous schedule in the request. */
 function kind(next:string) {
  const base={starts_at:value.starts_at};
  const result:Schedule=next==='intervalo'?{...base,kind:'intervalo',interval_value:1,interval_unit:'horas'}:next==='semanal'?{...base,kind:'semanal',local_time:local,weekday:1}:next==='mensual'?{...base,kind:'mensual',local_time:local,day_of_month:1}:next==='anual'?{...base,kind:'anual',local_time:local,day_of_month:1,month:1}:{...base,kind:'diaria',local_time:local};onChange(result);
 }
 return <fieldset><legend>Programación</legend><div className="notification-fields">
 <label>Recurrencia<select value={value.kind} onChange={e=>kind(e.target.value)}><option value="diaria">Diaria</option><option value="semanal">Semanal</option><option value="mensual">Mensual</option><option value="anual">Anual</option><option value="intervalo">Intervalo</option></select></label>
 <label>Inicio (UTC, con Z)<input required value={value.starts_at} onChange={e=>onChange({...value,starts_at:e.target.value})} aria-describedby="notification-start-help"/></label>
 {value.kind==='intervalo'?<><label>Cada<input required type="number" min="1" step="1" value={value.interval_value} onChange={e=>onChange({...value,interval_value:Number(e.target.value)})}/></label><label>Unidad del intervalo<select value={value.interval_unit} onChange={e=>onChange({...value,interval_unit:e.target.value as 'minutos'|'horas'})}><option value="minutos">Minutos</option><option value="horas">Horas transcurridas</option></select></label></>:<label>Hora local<input required type="time" value={value.local_time} onChange={e=>onChange({...value,local_time:e.target.value})}/></label>}
 {value.kind==='semanal'&&<label>Día de la semana<select value={value.weekday} onChange={e=>onChange({...value,weekday:Number(e.target.value)})}>{['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'].map((day,index)=><option key={day} value={index+1}>{day}</option>)}</select></label>}
 {(value.kind==='mensual'||value.kind==='anual')&&<label>Día nominal del mes<input type="number" min="1" max="31" step="1" required value={value.day_of_month} onChange={e=>onChange({...value,day_of_month:Number(e.target.value)})}/></label>}
 {value.kind==='anual'&&<label>Mes<input type="number" min="1" max="12" step="1" required value={value.month} onChange={e=>onChange({...value,month:Number(e.target.value)})}/></label>}
 </div><p id="notification-start-help">El inicio fija el primer límite del resumen. Las horas de calendario respetan la zona de la regla; los intervalos miden tiempo transcurrido.</p></fieldset>;
}
