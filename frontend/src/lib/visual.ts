/** Stable energy-category encoding shared by dashboard, detail charts and breakdowns. */
import type { CategoryId } from './api/consumption';

export const categoryColors: Record<CategoryId, string> = {
  'CAT-01': '#0D4A37', 'CAT-02': '#A65E2E', 'CAT-03': '#7A6EAB',
  'CAT-04': '#2876B7', 'CAT-05': '#B54979', 'CAT-06': '#16857C', 'CAT-07': '#596579',
};

/** Localize canonical decimal strings without converting energy or money to floating point. */
export function readableDecimal(value: string): string {
  const [integer, fraction] = value.split('.');
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (fraction === undefined ? '' : ',' + fraction);
}

/** Format an instant for reading, retaining original exact value in evidence/title attributes. */
export function shortInstant(value: string, timezone: string, timeOnly = false): string {
  return new Intl.DateTimeFormat('es-CL', { timeZone: timezone,
    ...(timeOnly ? {} : { day: '2-digit', month: 'short' as const }), hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value));
}
