/** Accessible004 component bars using the identical rows/strings shown in the cost table. */
import Decimal from "decimal.js";
import type { Cycle, ComponentDetail } from "../../lib/api/costs";

/** Project absolute amounts to geometry only; signed exact values remain in every accessible label. */
export function CostChart({ rows = [], series }: { rows?: readonly ComponentDetail[]; series?: readonly Cycle[] }) {
  const values = series ? series.flatMap(cycle => {
    /** Use only the selected exact pair; a pending comparison contributes no fabricated financial bars. */
    const period = `${cycle.start_at} → ${cycle.end_at}`;
    const amounts = cycle.calculation ? [{ code: `${period} · ${cycle.calculation.complete_total === null ? "Subtotal disponible" : "Costo completo"}`,
      presented_amount: cycle.calculation.complete_total ?? cycle.calculation.available_subtotal }] : [];
    if (cycle.comparison_status === "available" && cycle.comparison) {
      for (const [label, amount] of [["Calculado comparable", cycle.comparison.comparable_calculated], ["Facturado comparable", cycle.comparison.comparable_billed], ["Diferencia comparable", cycle.comparison.delta_amount]]) {
        if (amount !== null) amounts.push({ code: `${period} · ${label}`, presented_amount: amount });
      }
    }
    return amounts;
  }) : rows.filter(row => row.presented_amount !== null);
  const Geometry = Decimal.clone({ precision: 128 });
  const maximum = values.reduce((max, row) => Geometry.max(max, new Geometry(row.presented_amount!).abs()), new Geometry(1));
  return <figure><svg role="img" aria-label={series ? "Evolución de costos por ciclo real en CLP" : "Importes por concepto en CLP"} viewBox={`0 0 800 ${Math.max(80, values.length * 64)}`} style={{ width: "100%" }}>
    {values.map((row, index) => <g role="graphics-symbol" tabIndex={0} key={row.code} aria-label={`${row.code}: ${row.presented_amount} CLP`}>
      <title>{row.code}: {row.presented_amount} CLP</title><text x="0" y={index * 64 + 18}>{row.code}</text>
      <rect x="0" y={index * 64 + 28} width={Math.max(1, new Geometry(row.presented_amount!).abs().div(maximum).mul(780).toNumber())} height="20" fill={new Geometry(row.presented_amount!).isNegative() ? "#963c17" : "#176996"} />
    </g>)}
  </svg><figcaption>{series ? "Importes por ciclo real y comparación de sus revisiones seleccionadas, sin prorratear. Los subtotales disponibles no son costos completos; un contraste pendiente no tiene barras comparables." : "Importes disponibles por concepto · CLP. Los conceptos no calculables no se dibujan como cero."}</figcaption></figure>;
}
