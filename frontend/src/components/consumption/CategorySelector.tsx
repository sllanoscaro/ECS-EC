/** Controlled selection of all seven fixed categories, irrespective of availability or physical presence. */
import type { CategoryId, CategoryStatus } from "../../lib/api/consumption";

/** Emit only the chosen category; period and representation remain owned by the query container. */
export function CategorySelector({ categories, value, onChange }: {
  categories: readonly CategoryStatus[]; value: CategoryId; onChange: (category: CategoryId) => void;
}) {
  return <label>Categoría<select value={value} onChange={event => { onChange(event.target.value as CategoryId); }}>
    {[...categories].sort((a,b) => a.id.localeCompare(b.id)).map(category => <option key={category.id} value={category.id}>
      {category.id} · {category.name}{!category.has_meter && category.id !== "CAT-01" ? " · Sin medidor" : ` · ${category.source_mode === "calculated" ? "Total calculado" : category.source_mode === "measured" ? "Con medidor" : "Sin base"}`}
    </option>)}
  </select></label>;
}
