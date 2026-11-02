/**004 immutable calculation detail: independent execution/coverage/time states and a nullable complete total. */
import type { CalculationDetail } from "../../lib/api/costs";
import { limitationLabel } from "./labels";
import { CostChart } from "./CostChart";
import { ReproductionDetail } from "./ReproductionDetail";
import { CostTable } from "./CostTable";

/** Render a persisted revision without recalculating money, inferring missing data or replacing physicalCAT-01. */
export function CostBreakdown({ calculation }: { calculation: CalculationDetail }) {
  const data = calculation;
  return <section aria-label="Resultado del cálculo"><h2>Cálculo · Revisión {data.revision}</h2>
    <p>{data.snapshot.request.start} → {data.snapshot.request.end} · {data.snapshot.request.timezone}</p>
    <p>Corte: {data.snapshot.cutoff_at} · {data.execution_state} · {data.temporal_state} · {data.sufficiency}</p>
    {data.temporal_state === "en_curso" && <p>Resultado provisional del consumo observado. No proyecta el costo al cierre.</p>}
    <p>Subtotal disponible: {data.available_subtotal} CLP</p>
    <p>{data.complete_total === null ? "Costo completo: no disponible" : `Costo completo: ${data.complete_total} CLP`}</p>
    <p>Tablero: {data.snapshot.supply.general_board_ref} · Suministro revisión {data.snapshot.supply_revision} · Perfil revisión {data.snapshot.profile_revision ?? "No disponible"}</p>
    {data.snapshot.general_reason === "calculated_general" && <p>Se requiere medición física del suministro general. El total calculado de categorías no la sustituye.</p>}
    <p>Mes de demanda: {data.snapshot.billing_month_ref ?? "No resuelto"}</p>
    {data.reason_codes.length > 0 && <p role="status">Limitaciones: {data.reason_codes.map(limitationLabel).join(" ")}</p>}
    {data.snapshot.supply.measurement_point_differences.map((difference, index) => <p key={index}>Diferencia del punto de medición: {difference}. Sin ajuste implícito.</p>)}
    <CostChart rows={data.components} /><CostTable rows={data.components} /><ReproductionDetail calculation={data} />
  </section>;
}
