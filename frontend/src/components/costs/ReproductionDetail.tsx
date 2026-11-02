/** Captured004 documentary evidence; inspection never reloads current prices or original source payloads. */
import type { CalculationDetail } from "../../lib/api/costs";

/** Explain the physical point, immutable references, demand policy and actual monthly coverage used by this revision. */
export function ReproductionDetail({ calculation }: { calculation: CalculationDetail }) {
  const capture = calculation.snapshot;
  return <details><summary>Revisar bases de reproducción</summary>
    <p>Tablero: {capture.supply.general_board_ref} · Fuente física: {capture.supply.general_source_id} · Revisión de suministro: {capture.supply_revision}</p>
    <p>Perfil: {capture.profile_id ?? "No disponible"} · Revisión: {capture.profile_revision ?? "No disponible"}</p>
    <p>Mes de demanda: {capture.billing_month_ref ?? "No resuelto"} · Política: {capture.billing_month_policy_version ?? "No resuelta"}</p>
    {capture.billing_month_source_ref && <p>Documento del mes: {capture.billing_month_source_ref.document_reference} · Mes declarado: {capture.billing_month_source_ref.billing_month_ref}</p>}
    <p>Los datos capturados se conservan aunque venza el detalle original. Las consultas no cambian precios ni plazos.</p>
    <ul>{capture.supply.document_refs.map(reference => <li key={reference}>Fuente del suministro: {reference}</li>)}</ul>
    <ul>{capture.profile?.segments.map((segment, index) => <li key={index}>{segment.valid_from} → {segment.valid_to ?? "Vigencia abierta"} · Quantum: {segment.rounding_policy.quantum} CLP · Etapa: {segment.rounding_policy.stage}
      <ul>{segment.source_refs.map(reference => <li key={reference}>{reference}</li>)}</ul>
    </li>)}</ul>
    <table><caption>Máximos mensuales conservados · kW</caption><thead><tr><th>Mes</th><th>Tipo</th><th>Máximo</th><th>Cobertura</th></tr></thead><tbody>
      {calculation.monthly_maxima.map(row => <tr key={`${row.kind}:${row.month}`}><th scope="row">{row.month}</th><td>{row.kind === "peak" ? "Punta" : "Potencia suministrada"}</td><td>{row.maximum_kw ?? "No calculable"}</td><td>{row.coverage === "complete" ? "Completa" : "Incompleta"}</td></tr>)}
    </tbody></table>
    <p>Versión del método: {calculation.engine_version} · Huella de la captura: {calculation.input_hash}</p>
    <p>Conservación mínima de esta revisión: {calculation.retain_until}</p>
  </details>;
}
