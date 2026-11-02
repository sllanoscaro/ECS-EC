/** Exact persisted pair comparison; payable amount and comparable subtotals remain visibly distinct. */
import { limitationLabel } from "./labels";
import type { ComparisonDetail } from "../../lib/api/costs";

/** Present signed differences/exclusions and a non-applicable percentage for zero billed subtotal. */
export function ComparisonTable({ comparison }: { comparison: ComparisonDetail }) {
  return <section aria-label="Contraste registrado"><h2>Contraste · Revisión {comparison.revision}</h2>
    <p>Cálculo: {comparison.calculation_id} · Boleta revisión: {comparison.bill_revision_id}</p>
    <p>Calculado comparable: {comparison.comparable_calculated ?? "No disponible"} CLP · Facturado comparable: {comparison.comparable_billed ?? "No disponible"} CLP</p>
    <p>Total a pagar del documento: {comparison.total_payable} CLP</p>
    <p>Diferencia: {comparison.delta_amount ?? "No disponible"} CLP · Porcentaje: {comparison.delta_percent === null ? "No aplica" : `${comparison.delta_percent} %`}</p>
    <table><caption>Conceptos comparables · {comparison.currency}</caption><thead><tr><th>Concepto</th><th>Calculado</th><th>Facturado</th><th>Diferencia</th></tr></thead>
      <tbody>{comparison.pairs.map(pair => <tr key={pair.code}><th scope="row">{pair.code} · {pair.tax_basis} · {pair.unit}</th><td>{pair.calculated_amount}</td><td>{pair.billed_amount}</td><td>{pair.delta_amount}</td></tr>)}</tbody></table>
    <ul aria-label="Conceptos excluidos">{comparison.excluded_lines.map(line => <li key={line.code}>{line.code}: {line.amount} CLP · {limitationLabel(line.reason_code)}</li>)}</ul>
    {comparison.limitation_codes.map(code => <p key={code}>{limitationLabel(code)}</p>)}
  </section>;
}
