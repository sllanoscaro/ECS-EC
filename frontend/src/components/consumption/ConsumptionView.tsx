/** Authenticated consumption container: one response drives both views and every filter stays explicit. */
"use client";
import { useEffect, useState } from "react";
import { consumptionApi, type Catalog, type CategoryId, type Period, type Granularity } from "../../lib/api/consumption";
import { SessionGuard } from "../identity/SessionProvider";
import { CategorySelector } from "./CategorySelector";
import { GranularitySelector } from "./GranularitySelector";
import { EnergyChart } from "./EnergyChart";
import { EnergyTable } from "./EnergyTable";
import { PeriodForm } from "./PeriodForm";
import { QueryState } from "./QueryState";
import { useConsumptionQuery } from "./useConsumptionQuery";

/** Load catalog only at runtime; the guard unmounts all private state when the session changes. */
export function ConsumptionView() {
  return <SessionGuard permission="consumption.read"><ConsumptionContent /></SessionGuard>;
}

/** Own the last valid period/category and render one full response without any browser-side energy arithmetic. */
function ConsumptionContent() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [category, setCategory] = useState<CategoryId>("CAT-01");
  const [period, setPeriod] = useState<Period | null>(null);
  const [catalogError, setCatalogError] = useState(false);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [granularity, setGranularity] = useState<Granularity>("detail");
  const [view, setView] = useState("both");
  useEffect(() => {
    /** Ignore catalog responses after unmount or retries and retain a previously selected period. */
    let active = true;
    const controller = new AbortController();
    setCatalogError(false);
    void consumptionApi.catalog(controller.signal).then(value => {
      if (active) { setCatalog(value); setPeriod(previous => previous ?? value.default_period); }
    }).catch(() => { if (active) setCatalogError(true); });
    return () => { active = false; controller.abort(); };
  }, [catalogAttempt]);
  const query = useConsumptionQuery(category, period, consumptionApi.detail, granularity);
  if (catalogError) return <div role="alert">No se pudo cargar el catálogo.<button onClick={() => { setCatalogAttempt(value => value + 1); }}>Reintentar catálogo</button></div>;
  if (!catalog || !period) return <p role="status">Cargando catálogo…</p>;
  const selected = catalog.categories.find(item => item.id === category)!;
  return <>
    <CategorySelector categories={catalog.categories} value={category} onChange={setCategory} />
    <PeriodForm period={period} onSubmit={setPeriod} />
    <GranularitySelector value={granularity} onChange={setGranularity} />
    <h2>{selected.name} · {{ detail: "Detalle", hour: "Hora", day: "Día", month: "Mes", year: "Año" }[granularity]} · Energía eléctrica · kWh</h2>
    <p>{period.start} → {period.end} · {period.timezone} · [inicio, fin)</p>
    <label>Representación<select value={view} onChange={event => { setView(event.target.value); }}><option value="both">Gráfico y tabla</option><option value="chart">Gráfico</option><option value="table">Tabla</option></select></label>
    <button onClick={query.retry}>Actualizar consumo</button>
    <QueryState {...query} />
    {query.data && <>
      <p>Corte: {query.data.cutoff_at}</p>
      {category === "CAT-01" && <p>{query.data.source_mode === "measured" ? "Total medido" : query.data.source_mode === "calculated" ? "Total calculado de las categorías presentes" : "Procedencia según segmentos de configuración"}</p>}
      <ul aria-label="Configuración del período">{query.data.configuration_segments.map((segment, i) => <li key={i}>{segment.start} → {segment.end} · {segment.source_mode} · Base: {segment.base_categories.join(", ") || "No aplica"} · Revisión {segment.category_revision}</li>)}</ul>
      {view !== "table" && <EnergyChart rows={"rows" in query.data ? query.data.rows : []} blocks={"blocks" in query.data ? query.data.blocks : undefined} timezone={period.timezone} />}
      {view !== "chart" && <EnergyTable rows={"rows" in query.data ? query.data.rows : []} blocks={"blocks" in query.data ? query.data.blocks : undefined} timezone={period.timezone} categoryId={category} />}
    </>}
  </>;
}
