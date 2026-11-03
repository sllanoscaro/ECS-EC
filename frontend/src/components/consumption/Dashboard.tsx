/** Live daily consumption dashboard; all amounts/coverage come from one server-owned read snapshot. */
"use client";
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { apiRequest, sessionActivityHeaders } from '../../lib/api/session';
import type { CategoryId, Period } from '../../lib/api/consumption';
import { categoryColors, shortInstant } from '../../lib/visual';
import { projectRatio } from './format';
import { SessionGuard } from '../identity/SessionProvider';
import { useBuildingTimezone } from '../identity/ApplicationFrame';
import { Icon } from '../identity/Icon';
import { EnergyChart } from './EnergyChart';
import { compareDashboardEnergy, dashboardDecimal } from './dashboardFormat';

type DailyPoint = { start: string; end: string; energy_kwh: string | null; coverage_percent: string };
type DailyCategory = { id: CategoryId; name: string; source_mode: string; base_categories: CategoryId[]; energy_kwh: string | null; coverage_percent: string; covered_duration_us: string; elapsed_duration_us: string; last_reading_at: string | null; state: string; series: DailyPoint[]; chart_excluded_count: number };
type DailySnapshot = { timezone: string; cutoff_at: string; coverage_end_at?: string; period: Period; categories: DailyCategory[]; series: DailyPoint[]; chart_excluded_count: number };

/** Mount data fetching only while the current normal session grants consumption.read. */
export function Dashboard() { return <SessionGuard permission="consumption.read"><DailyDashboard /></SessionGuard>; }

/** Query once after the next quarter hour, allowing five seconds for reception to commit. */
export function nextDashboardRefresh(now: number): Date {
  const quarter = 15 * 60 * 1000;
  return new Date((Math.floor(now / quarter) + 1) * quarter + 5000);
}

/** Refresh at calendar quarters only; manual updates remain available without clearing visible data. */
function DailyDashboard() {
  const [data, setData] = useState<DailySnapshot | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<CategoryId | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [next, setNext] = useState<Date | null>(null);
  const background = useRef(false);
  useBuildingTimezone(data?.timezone);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    setBusy(true); setError('');
    void apiRequest<DailySnapshot>('/consumption/dashboard', { signal: controller.signal, headers: sessionActivityHeaders(background.current ? 'background' : 'interactive') }).then(value => { if (active) setData(value); })
      .catch(() => { if (active && !controller.signal.aborted) setError('No se pudo consultar el dashboard.'); })
      .finally(() => {
        if (!active) return;
        const scheduled = nextDashboardRefresh(Date.now());
        setBusy(false); setNext(scheduled);
        timer = setTimeout(() => { background.current = true; setAttempt(value => value + 1); }, scheduled.getTime() - Date.now());
      });
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [attempt]);
  const total = data?.categories.find(category => category.id === 'CAT-01');
  const partials = data?.categories.filter(category => category.id !== 'CAT-01').sort(compareDashboardEnergy) ?? [];
  const selected = partials.find(category => category.id === selectedCategory);
  const chartCategory = selected?.id ?? 'CAT-01';
  const chartSeries = selected ? selected.series : data?.series;
  const excludedCount = selected ? selected.chart_excluded_count : data?.chart_excluded_count;
  // Category shares use the same daily total and period as the summary, not the largest partial.
  const totalEnergy = total?.energy_kwh ?? '0';
  const date = data ? new Intl.DateTimeFormat('es-CL', { timeZone: data.timezone, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(data.cutoff_at)) : '';
  return <>
    <div className="consumption-toolbar"><p>Electro Conforma {date && ` · ${date}`}</p><button disabled={busy} onClick={() => { background.current = false; setAttempt(value => value + 1); }}><Icon name="refresh" />Actualizar</button></div>
    {busy && !data && <p className="loading-state" role="status">Consultando el consumo del día…</p>}
    {error && <p className="notice notice--error" role="alert"><Icon name="warning" />No se pudo consultar el dashboard. Intente actualizar de nuevo.</p>}
    {data && total && <>
      {total.state !== 'available' && <p className="notice notice--warning" role="status"><Icon name="warning" />{total.state === 'no_data' ? 'Sin datos del consumo de hoy.' : total.state === 'no_meter' ? 'Sin fuente disponible para el total.' : 'Datos incompletos: la cobertura del período es parcial.'}</p>}
      {(excludedCount ?? 0) > 0 && <p className="notice notice--warning" role="status"><Icon name="warning" />Hay lecturas que no caben en un bloque de 15 minutos. Se conservan en el total diario, sin prorratearlas en el gráfico.</p>}
      <section className="summary-strip panel" aria-label="Resumen diario"><div><h2>Consumo energético total acumulado</h2><p className="summary-value">{total.energy_kwh === null ? 'Sin datos' : `${dashboardDecimal(total.energy_kwh)} kWh`}</p><p>Sumatoria del consumo eléctrico de cada intervalo del día de hoy</p></div><div><h2>Porcentaje de cobertura</h2><p className="summary-value">{total.elapsed_duration_us === '0' ? '—' : `${dashboardDecimal(total.coverage_percent)} %`}</p><p>Porcentaje de intervalos registrados correctamente</p></div></section>
      <div className="dashboard-grid">
        <section id="dashboard-evolution" className="panel chart-panel" aria-labelledby="dashboard-chart-title">
          <div className="dashboard-chart-heading"><h2 id="dashboard-chart-title">Consumo del día de hoy</h2>{selected && <button className="dashboard-reset" onClick={() => setSelectedCategory(null)}>Ver consumo total</button>}</div>
          <p className="section-description" aria-live="polite">{selected && `${selected.name} · `}Consumo energético presentado en intervalos de 15 minutos · Consumo en kWh</p>
          <EnergyChart presentation="dashboard" smooth rows={[]} points={chartSeries ?? []} categoryId={chartCategory} period={data.period} timezone={data.timezone} footerNote={<span className="dashboard-next-update">Hora de la próxima actualización: {next ? shortInstant(next.toISOString(), data.timezone, true) : 'Consultando…'}</span>} />
          {selected?.state === 'no_meter' && <p className="section-description" role="status">Sin medidor para esta categoría.</p>}
          {selected?.state === 'no_data' && <p className="section-description" role="status">Sin datos de esta categoría hoy.</p>}
          {selected?.state === 'incomplete' && <p className="section-description" role="status">Datos incompletos de esta categoría: los intervalos sin datos se mantienen vacíos.</p>}
        </section>
        <section className="panel category-panel"><h2>Consumo por categoría</h2><p className="section-description">Barras respecto a la energía total acumulada</p>
          <ul>{partials.map(category => <li key={category.id}>
            <button className="category-choice" aria-pressed={selected?.id === category.id} aria-controls="dashboard-evolution" onClick={() => setSelectedCategory(category.id)} style={{ '--category-color': categoryColors[category.id] } as CSSProperties}>
              <span className="category-label"><span>{category.name}</span><strong className={category.energy_kwh === null ? undefined : "category-energy"}>{category.energy_kwh === null ? (category.state === 'no_meter' ? 'Sin medidor' : 'Sin datos') : `${dashboardDecimal(category.energy_kwh)} kWh`}</strong></span>
              {category.energy_kwh !== null && <span className="category-track"><span style={{ width: `${projectRatio(category.energy_kwh, totalEnergy) * 100}%`, background: categoryColors[category.id] }} /></span>}
              {category.state === 'incomplete' && <small>Datos incompletos</small>}
            </button>
          </li>)}</ul>
        </section>
      </div>
    </>}
  </>;
}
