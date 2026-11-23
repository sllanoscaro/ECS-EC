/** Presentation only; authoritative amounts and estimates are both supplied by the server. */
import { readableDecimal } from '../../lib/visual';
import type { ComponentDetail } from '../../lib/api/costs';

export function money(value: string | null | undefined): string {
  return value === null || value === undefined ? 'No disponible' : value.startsWith('-') ? `−$${readableDecimal(value.slice(1))}` : `$${readableDecimal(value)}`;
}

export function signedMoney(value: string | null): string {
  return value !== null && !value.startsWith('-') && !/^0(?:\.0+)?$/.test(value) ? `+${money(value)}` : money(value);
}

export const chargeNames: Record<ComponentDetail['kind'], string> = {
  energia: 'Energía', transmision: 'Transmisión', servicio_publico: 'Servicio público', fijo: 'Cargo fijo',
  demanda_punta: 'Demanda en punta', potencia_suministrada: 'Potencia suministrada', impuesto: 'Impuesto', otro_documentado: 'Otro cargo documentado',
};

export function cycleDate(value: string, timezone: string, includeTime = false): string {
  return new Intl.DateTimeFormat('es-CL', { timeZone: timezone, day: '2-digit', month: 'short', year: 'numeric',
    ...(includeTime ? {hour:'2-digit',minute:'2-digit',hourCycle:'h23' as const} : {}) }).format(new Date(value));
}

export function cycleBoundary(value:string, other:string, timezone:string):string {
  return cycleDate(value,timezone,cycleDate(value,timezone)===cycleDate(other,timezone));
}
