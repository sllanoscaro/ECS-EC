/** Paginated004 financial history: fixed-cutoff server selections drive both the evolution chart and table. */
"use client";
import { useEffect, useState, type FormEvent } from "react";
import { costsApi, financialApi, type CalculationDetail, type ComparisonDetail, type CyclePage } from "../../lib/api/costs";
import { CostChart } from "./CostChart";
import { ComparisonTable } from "./ComparisonTable";

/** Filter actual cycles without creating reports/calculations or prorating monthly charges into smaller periods. */
export function CostHistory({ onSelect }: { onSelect: (value: CalculationDetail) => void }) {
  const [draft, setDraft] = useState({ from: "", to: "" });
  const [filters, setFilters] = useState<Record<string,string>>({});
  const [page, setPage] = useState<CyclePage | null>(null);
  const [cursor, setCursor] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");
  const [comparison, setComparison] = useState<ComparisonDetail | null>(null);
  useEffect(() => {
    /** Invalidate a previous filter immediately; abort and discard responses after another selection or session unmount. */
    let active = true; const controller = new AbortController(); setPage(null); setError("");
    void costsApi.history({ ...filters, ...(cursor ? { cursor } : {}) }, controller.signal).then(value => { if (active) setPage(value); })
      .catch(() => { if (active) setError("No se pudo consultar el historial. Revise el período y reintente."); });
    return () => { active = false; controller.abort(); };
  }, [filters, cursor, attempt]);
  function submit(event: FormEvent) {
    /** Keep invalid draft correction local; the server validates all explicit offsets and interval bounds. */
    event.preventDefault(); setPage(null); setComparison(null); setCursor("");
    setFilters(Object.fromEntries(Object.entries(draft).filter(([,value]) => Boolean(value))));
  }
  async function historical(id: string) {
    /** Open a stable historical comparison as historical, never as the selected cycle's current pair. */
    try { setComparison(await financialApi.comparison(id)); }
    catch { setError("No se pudo consultar la comparación histórica."); }
  }
  return <section aria-label="Historial de costos"><h2>Historial por ciclo real</h2>
    <form onSubmit={submit}><label>Historial desde (con offset)<input value={draft.from} onChange={event => { setDraft(old => ({ ...old, from: event.target.value })); }} /></label>
      <label>Historial hasta (con offset)<input value={draft.to} onChange={event => { setDraft(old => ({ ...old, to: event.target.value })); }} /></label><button type="submit">Consultar historial de costos</button></form>
    {error && <p role="alert">{error}<button onClick={() => { setAttempt(value => value + 1); }}>Reintentar historial</button></p>}
    {!page && !error && <p role="status">Consultando historial…</p>}
    {page && <><p>Corte del historial: {page.cutoff_at}</p>{!page.items.length && <p>Sin ciclos para el período solicitado.</p>}
      <CostChart series={page.items} />
      <table><caption>Historia financiera · ciclos sin prorrateo</caption><thead><tr><th>Ciclo y zona</th><th>Estado y revisión</th><th>Disponible</th><th>Costo completo</th><th>Calculado comparable</th><th>Facturado comparable</th><th>Contraste seleccionado</th><th>Referencias</th></tr></thead>
        <tbody>{page.items.map(cycle => <tr key={cycle.id}><th scope="row">{cycle.start_at} → {cycle.end_at} · {cycle.timezone}</th>
          <td>{cycle.calculation ? `${cycle.calculation.execution_state} · ${cycle.calculation.temporal_state} · ${cycle.calculation.sufficiency} · Revisión ${cycle.calculation.revision}` : "Sin cálculo"}</td>
          <td>{cycle.calculation ? `${cycle.calculation.available_subtotal} CLP` : "No disponible"}</td>
          <td>{cycle.calculation?.complete_total === null || !cycle.calculation ? "No disponible" : `${cycle.calculation.complete_total} CLP`}</td>
          <td>{cycle.comparison_status === "available" && cycle.comparison?.comparable_calculated !== null ? `${cycle.comparison?.comparable_calculated} CLP` : "No disponible"}</td>
          <td>{cycle.comparison_status === "available" && cycle.comparison?.comparable_billed !== null ? `${cycle.comparison?.comparable_billed} CLP` : "No disponible"}</td>
          <td>{cycle.comparison_status === "missing_for_selected_revisions" ? "Contraste pendiente para estas revisiones" : cycle.comparison_status === "no_bill" ? "Sin boleta registrada" : cycle.comparison_status === "no_calculation" ? "Sin cálculo" : `${cycle.delta_amount ?? "No disponible"} CLP · ${cycle.delta_percent === null ? "Porcentaje no aplicable" : `${cycle.delta_percent} %`}`}</td>
          <td>{cycle.calculation && <button onClick={() => { onSelect(cycle.calculation!); }}>Consultar cálculo {cycle.calculation.revision}</button>}
            {(cycle.historical_comparisons ?? []).map(reference => <button key={reference.id} onClick={() => { void historical(reference.id); }}>Ver contraste histórico {reference.revision} · {reference.id}</button>)}
          </td>
        </tr>)}</tbody></table>
      {page.next_cursor && <button onClick={() => { setPage(null); setCursor(page.next_cursor!); }}>Siguiente página de ciclos</button>}
      {cursor && <button onClick={() => { setPage(null); setCursor(""); }}>Primera página de ciclos</button>}
    </>}
    {comparison && <><h3>Comparación histórica seleccionada</h3><ComparisonTable comparison={comparison} /></>}
  </section>;
}
