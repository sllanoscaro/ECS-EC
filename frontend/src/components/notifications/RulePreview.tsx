/**008 show the exact server-resolved local slots and UTC cuts; an urgent preview never predicts condition timing. */
import type { Preview } from '../../lib/api/notifications';

/**The selected rule's next three dates share their source with activation, including the explicit initial empty window. */
export function RulePreview({value}:{value:Preview}) {
 return <section className="notification-preview" aria-label="Vista previa"><h3>Próximas fechas</h3>{!value.next_occurrences.length?<p>Esta regla es urgente. La fecha depende de una detección válida.</p>:<ol>{value.next_occurrences.map(date=><li key={date.resolved_at}><strong>{date.nominal_local.replace('T',' ')} · {date.timezone}</strong><span>UTC {date.resolved_at}</span><span>Ventana [{date.window.start}, {date.window.end})</span>{date.calendar_adjustment!=='ninguno'&&<span>Ajuste: {date.calendar_adjustment.replaceAll('_',' ')}</span>}{date.initial_window_empty&&<span>Ventana inicial vacía: todavía no hay período observado.</span>}</li>)}</ol>}<p>Vista previa válida hasta {value.expires_at}. Los cambios de configuración o destinatarios requieren otra vista previa.</p>{value.warnings.map(w=><p key={w}>{w}</p>)}</section>;
}
