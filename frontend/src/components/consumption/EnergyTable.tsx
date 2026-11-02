/** Semantic consumption table; diagnostics never become numeric rows and source evidence stays explicit. */
import type { CategoryId, DetailRow } from "../../lib/api/consumption";
import { energyLabel, instantLabel } from "./format";

/** Render exact incorporated rows and their historical origin using the same formatters as the SVG. */
export function EnergyTable({ rows, timezone, categoryId }: { rows: readonly DetailRow[]; timezone: string; categoryId: CategoryId }) {
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
