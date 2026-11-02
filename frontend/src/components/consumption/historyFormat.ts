/** Shared exact block descriptions: no energy summation and no percentage-based completeness inference. */
import type { AggregateBlock, SourceMode } from '../../lib/api/consumption';
import { energyLabel, instantLabel } from './format';

/** Return Spanish temporal state using the server's captured cutoff, never the browser clock. */
export function temporalLabel(block: AggregateBlock) {
  return { not_started: 'Aún no iniciado', ongoing: 'En curso', finished: 'Terminado' }[block.temporal_state];
}
/** Incomplete exact coverage that rounded to100 remains visibly less than100 percent. */
export function coverageLabel(block: AggregateBlock) {
  const value = block.coverage_state === 'incomplete' && block.coverage_percent === '100' ? '<100' : block.coverage_percent;
  return `${value} % · ${block.covered_duration_us}/${block.duration_us} µs`;
}
/** Use the same boundary/value/coverage text in accessible chart evidence and the semantic table. */
export function blockLabel(block: AggregateBlock, timezone: string) {
  return `${instantLabel(block.start, timezone)} → ${instantLabel(block.end, timezone)} · ${block.energy_kwh === null ? 'Sin datos · —' : energyLabel(block.energy_kwh)} · ${coverageLabel(block)} · ${temporalLabel(block)}`;
}

/** Translate wire provenance codes into readable source semantics without hiding historical mixtures. */
export function sourceModeLabel(mode: SourceMode) {
  return { measured: 'Medido', calculated: 'Calculado', mixed: 'Procedencia mixta', unavailable: 'Sin fuente disponible' }[mode];
}
