/** Shared textual state for graph/table; numeric rows and diagnostics remain separate. */
import type { DetailResult, AggregateQueryResult } from "../../lib/api/consumption";

/** Explain transport, absence and incomplete evidence using static text and explicit retry action. */
export function QueryState({ loading, error, data, retry }: {
  loading: boolean; error: string | null; data: DetailResult | AggregateQueryResult | null; retry: () => void;
}) {
  if (loading) return <p role="status">Consultando consumo…</p>;
  if (error) return <div role="alert"><p>{error}</p><button onClick={retry}>Reintentar</button></div>;
  if (!data) return null;
  const labels = { available: "Datos disponibles", no_meter: "Sin medidor", no_data: "Sin datos", incomplete: "Datos incompletos" };
  return <section aria-label="Estado del consumo"><p role="status">{labels[data.state]}</p>
    {data.warnings.map((warning, i) => <p key={i}>{"message" in warning ? `${warning.message} (${warning.count})` : warning.detail}</p>)}
    {"blocks" in data && data.blocks.length === 0 && <p>Ningún bloque cabe completamente en el filtro. Se conserva el período seleccionado.</p>}
    {data.diagnostics.map((diagnostic, index) => <div key={index}>
      <p>{diagnostic.start} → {diagnostic.end}</p>
      {diagnostic.reason_code === "calculation_configuration_changed" ? <>
        <p>Cambió la configuración de cálculo dentro del intervalo</p>
        <ul>{diagnostic.configuration_segments.map((segment, i) => <li key={i}>{segment.start} → {segment.end} · {segment.source_mode} · Revisión {segment.category_revision} · Base: {segment.base_categories.join(", ")} · Fuentes: {segment.basis_sources.map(source => `${source.category_id}: ${source.source_id}`).join(", ")}</li>)}</ul>
      </> : diagnostic.reason_code === "pending_incorporation" ? <p>Incorporación pendiente. Próxima admisible: {diagnostic.next_admissible_at ?? "Sin fecha disponible"}</p>
        : <p>Faltan contribuciones: {diagnostic.missing_categories.join(", ")}</p>}
    </div>)}
  </section>;
}
