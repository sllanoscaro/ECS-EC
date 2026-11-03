/** Authenticated consumption container: one response drives both views and every filter stays explicit. */
"use client";
import { useEffect, useState } from "react";
import { consumptionApi, type Catalog, type CategoryId, type Period, type Granularity } from "../../lib/api/consumption";
import { SessionGuard } from "../identity/SessionProvider";
import { ConsumptionFilters } from './ConsumptionFilters';
import { useBuildingTimezone } from '../identity/ApplicationFrame';
import { EnergyChart } from "./EnergyChart";
import { EnergyTable } from "./EnergyTable";
import { QueryState } from "./QueryState";
import { useConsumptionQuery } from "./useConsumptionQuery";
import { Icon } from '../identity/Icon';

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
  useBuildingTimezone(catalog?.timezone);
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
  useEffect(() => {
    /** Preserve explicit historical grouped links without restoring the removed filter toolbar. */
    const scale = new URLSearchParams(window.location.search).get('escala');
    if (['hour', 'day', 'month', 'year'].includes(scale ?? '')) setGranularity(scale as Granularity);
  }, []);
  const query = useConsumptionQuery(category, period, consumptionApi.detail, granularity);
  if (catalogError) return <div className="notice notice--error" role="alert"><Icon name="warning" />No se pudo cargar el catálogo.<button onClick={() => { setCatalogAttempt(value => value + 1); }}>Reintentar catálogo</button></div>;
  if (!catalog || !period) return <p role="status">Cargando catálogo…</p>;
  const selected = catalog.categories.find(item => item.id === category)!;
  return <>
    <div className="consumption-toolbar"><p>Consulta por categoría y período</p><button onClick={query.retry}>Actualizar consumo</button></div>
    <ConsumptionFilters catalog={catalog} category={category} period={period} choose={setCategory} apply={setPeriod} />
    <QueryState loading={query.loading} error={query.error} data={query.data} retry={query.retry} />
    {query.data && <>
      <section className="panel chart-panel"><h2>Energía por intervalo</h2><p className="section-description">{selected.name} · {new Intl.DateTimeFormat('es-CL', {timeZone: period.timezone, dateStyle: 'short', timeStyle: 'short'}).format(new Date(period.start))} → {new Intl.DateTimeFormat('es-CL', {timeZone: period.timezone, dateStyle: 'short', timeStyle: 'short'}).format(new Date(period.end))} · kWh</p>
      <EnergyChart rows={"rows" in query.data ? query.data.rows : []} blocks={"blocks" in query.data ? query.data.blocks : undefined} timezone={period.timezone} categoryId={category} period={period} /></section>
      <section className="panel values-panel"><h2>Valores del período</h2><p className="section-description">{"rows" in query.data ? `${query.data.rows.length} lecturas disponibles` : 'Valores agrupados'} · Corte: {new Intl.DateTimeFormat('es-CL', {timeZone: period.timezone, dateStyle: 'short', timeStyle: 'short'}).format(new Date(query.data.cutoff_at))}</p>
      <EnergyTable compact rows={"rows" in query.data ? query.data.rows : []} blocks={"blocks" in query.data ? query.data.blocks : undefined} timezone={period.timezone} categoryId={category} /></section>
    </>}
  </>;
}
