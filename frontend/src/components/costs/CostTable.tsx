/** Typed004 component table; nullable values remain unavailable and no browser-side sum is authoritative. */
import { limitationLabel, ruleLabel } from "./labels";
import type { ComponentDetail } from "../../lib/api/costs";

/** Present the server's exact quantity/price/amount and explicit reasons for each charge. */
export function CostTable({ rows }: { rows: readonly ComponentDetail[] }) {
  return <table><caption>Desglose de costos · CLP</caption><thead><tr><th>Concepto</th><th>Base</th><th>Precio</th><th>Importe</th><th>Regla y estado</th></tr></thead>
    <tbody>{rows.map(row => <tr key={row.code}><th scope="row">{row.code} · {row.kind}</th>
      <td>{row.basis_value === null ? "No disponible" : `${row.basis_value} ${row.unit}`}</td>
      <td>{row.applied_prices.length > 1 ? row.applied_prices.map(price => `${price.segment_start}: ${price.price ?? "No disponible"}`).join("; ") : row.unit_price ?? "No disponible"}</td>
      <td>{row.presented_amount === null ? "No calculable" : `${row.presented_amount} CLP`}</td>
      <td>{ruleLabel(row.rule_id)} · {row.tax_basis} · {row.state}{row.limitation_codes.length > 0 && ` · ${row.limitation_codes.map(limitationLabel).join(" ")}`}</td>
    </tr>)}</tbody></table>;
}
