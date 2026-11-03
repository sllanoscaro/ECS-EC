/** Semantic consumption table; diagnostics never become numeric rows and source evidence stays explicit. */
import type { CategoryId, DetailRow, AggregateBlock } from "../../lib/api/consumption";
import { coverageLabel, temporalLabel, sourceModeLabel } from "./historyFormat";
import { energyLabel, instantLabel } from "./format";
import { shortInstant, readableDecimal } from '../../lib/visual';

/** Render exact incorporated rows and their historical origin using the same formatters as the SVG. */
export function EnergyTable({ rows, blocks, timezone, categoryId, compact = false }: { compact?: boolean; blocks?: readonly AggregateBlock[]; rows: readonly DetailRow[]; timezone: string; categoryId: CategoryId }) {
  if (compact && !blocks) return <div className="table-scroll" tabIndex={0} role="region" aria-label="Valores del período"><table className="consumption-table"><caption className="sr-only">Energía eléctrica por intervalo · kWh</caption><thead><tr><th>Inicio</th><th>Fin</th><th className="numeric">Energía (kWh)</th><th>Origen</th></tr></thead><tbody>{rows.map(row => <tr key={row.record_id}><td title={row.start}>{shortInstant(row.start, timezone)}</td><td title={row.end}>{shortInstant(row.end, timezone)}</td><td className="numeric" title={row.energy_kwh}>{readableDecimal(row.energy_kwh)} kWh</td><td><details><summary>{row.origin.kind === 'measured' ? 'Medido' : 'Calculado'}</summary><div className="row-evidence"><p>{instantLabel(row.start, timezone)} → {instantLabel(row.end, timezone)}</p><p>Configuración: {row.configuration_revision} · Revisión: {row.category_revision}</p>{row.origin.kind === 'measured' ? <><p>Fuente: {row.origin.source_id}</p><p>Original: {row.origin.original_value} {row.origin.original_unit}</p></> : <><p>Total calculado de las categorías presentes · Base: {row.origin.base_categories.join(', ')}</p><p>La base parcial no garantiza cubrir todas las cargas del edificio.</p>{row.origin.contributions.map(part => <p key={part.measurement_id}>{part.category_id}: {energyLabel(part.energy_kwh)} · {part.start} → {part.end} · Fuente: {part.source_id} · Medición: {part.measurement_id}, revisión {part.measurement_revision}</p>)}</>}</div></details></td></tr>)}</tbody></table>{!rows.length && <p className="empty-state">Sin lecturas para este período.</p>}</div>;
  if (blocks) return <table>
    <caption>Energía eléctrica agrupada · kWh · {timezone}</caption>
    <thead><tr><th scope="col">Inicio (incluido)</th><th scope="col">Fin (excluido)</th><th scope="col">Energía (kWh)</th><th scope="col">Cobertura</th><th scope="col">Situación temporal</th><th scope="col">Procedencia</th></tr></thead>
    <tbody>{blocks.map(block => <tr key={block.start}>
      <td>{instantLabel(block.start, timezone)}</td><td>{instantLabel(block.end, timezone)}</td>
      <td>{block.energy_kwh === null ? '—' : energyLabel(block.energy_kwh)}</td>
      <td>{coverageLabel(block)} · {block.coverage_state === 'no_data' ? 'Sin datos' : block.coverage_state === 'incomplete' ? 'Incompleto' : 'Completo'}</td>
      <td>{temporalLabel(block)}</td><td>{sourceModeLabel(block.source_mode)}<ul>{block.provenance_segments.map((segment, i) => <li key={i}>
        {segment.start} → {segment.end} · {sourceModeLabel(segment.source_mode)} · Fuente: {segment.source_id ?? 'No aplica'} · Base: {segment.base_categories.join(', ') || 'No aplica'} · Revisión {segment.category_revision}
        {segment.basis_sources.map(source => <span key={source.category_id}> · {source.category_id}: {source.source_id}</span>)}
      </li>)}</ul>{block.warnings.map((warning, i) => <p key={i}>{warning.detail}</p>)}</td>
    </tr>)}</tbody>
  </table>;
  return <table>
    <caption>Energía eléctrica por intervalo · kWh · {timezone}</caption>
    <thead><tr><th scope="col">Inicio (incluido)</th><th scope="col">Fin (excluido)</th><th scope="col">Energía (kWh)</th><th scope="col">Procedencia</th></tr></thead>
    <tbody>{rows.map(row => <tr key={row.record_id}>
      <td>{instantLabel(row.start, timezone)}</td><td>{instantLabel(row.end, timezone)}</td><td>{energyLabel(row.energy_kwh)}</td>
      <td>{row.origin.kind === "measured" ? <>
        <p>{categoryId === "CAT-01" ? "Total medido" : "Medición"}</p><p>Fuente: {row.origin.source_id}</p><p>Original: {row.origin.original_value} {row.origin.original_unit}</p>
      </> : <>
        <p>Total calculado de las categorías presentes</p><p>Base: {row.origin.base_categories.join(", ")}</p>
        <p>La base parcial no garantiza cubrir todas las cargas del edificio.</p>
        <ul>{row.origin.contributions.map(part => <li key={part.measurement_id}>
          {part.category_id}: {energyLabel(part.energy_kwh)} · {instantLabel(part.start, timezone)} → {instantLabel(part.end, timezone)} ·
          Fuente: {part.source_id} · Medición: {part.measurement_id}, revisión {part.measurement_revision} · Revisión de categoría: {part.category_revision}
        </li>)}</ul>
      </>}
        <p>Configuración: {row.configuration_revision} · Revisión de categoría: {row.category_revision}</p>
      </td>
    </tr>)}</tbody>
  </table>;
}
