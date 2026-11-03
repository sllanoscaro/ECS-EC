/** Dashboard-only presentation; rounding never changes source values or chart geometry. */
import Decimal from 'decimal.js';
import { readableDecimal } from '../../lib/visual';

/** Round exact decimal text half up to one visible decimal, without binary float conversion. */
export function dashboardDecimal(value: string): string {
  return readableDecimal(new Decimal(value).toFixed(1, Decimal.ROUND_HALF_UP));
}

/** Show energy first, then the local interval end with seconds and no timezone suffix. */
export function dashboardPointLabel(energy: string | null, end: string, timezone: string): string {
  const time = new Intl.DateTimeFormat('es-CL', {
    timeZone: timezone, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).format(new Date(end));
  return `${energy === null ? 'Sin datos' : `${dashboardDecimal(energy)} kWh`} · ${time}`;
}

/** Sort exact energy descending with missing readings last; ties preserve catalog order. */
export function compareDashboardEnergy(a: { energy_kwh: string | null }, b: { energy_kwh: string | null }): number {
  if (a.energy_kwh === null) return b.energy_kwh === null ? 0 : 1;
  if (b.energy_kwh === null) return -1;
  return new Decimal(b.energy_kwh).comparedTo(a.energy_kwh);
}
