/** Live daily consumption dashboard; all amounts/coverage come from one server-owned read snapshot. */
"use client";
import { useEffect, useRef, useState } from 'react';
import { apiRequest, sessionActivityHeaders } from '../../lib/api/session';
import type { CategoryId, Period } from '../../lib/api/consumption';
import { categoryColors, shortInstant, readableDecimal } from '../../lib/visual';
import { projectRatio, chartMaximum } from './format';
import { SessionGuard } from '../identity/SessionProvider';
import { useBuildingTimezone } from '../identity/ApplicationFrame';
import { Icon } from '../identity/Icon';
import { EnergyChart } from './EnergyChart';

type DailyCategory = { id: CategoryId; name: string; source_mode: string; base_categories: CategoryId[]; energy_kwh: string | null; coverage_percent: string; covered_duration_us: string; elapsed_duration_us: string; last_reading_at: string | null; state: string };
type DailySnapshot = { timezone: string; cutoff_at: string; period: Period; categories: DailyCategory[]; series: { start: string; end: string; energy_kwh: string | null; coverage_percent: string }[]; chart_excluded_count: number };

/** Mount data fetching only while the current normal session grants consumption.read. */
export function Dashboard() { return <SessionGuard permission="consumption.read"><DailyDashboard /></SessionGuard>; }

/** Refresh every60s after completion; background reads never renew session activity or predict new readings. */
function DailyDashboard() {
  const [data, setData] = useState<DailySnapshot | null>(null);
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
    setBusy(true); setError(''); setData(null); setNext(null);
    void apiRequest<DailySnapshot>('/consumption/dashboard', { signal: controller.signal, headers: sessionActivityHeaders(background.current ? 'background' : 'interactive') }).then(value => { if (active) setData(value); })
      .catch(() => { if (active && !controller.signal.aborted) setError('No se pudo consultar el dashboard.'); })
      .finally(() => {
        if (!active) return;
        setBusy(false); setNext(new Date(Date.now() + 60000));
        timer = setTimeout(() => { background.current = true; setAttempt(value => value + 1); }, 60000);
      });
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [attempt]);
  const total = data?.categories.find(category => category.id === 'CAT-01');
  const partials = data?.categories.filter(category => category.id !== 'CAT-01') ?? [];
  const maximum = chartMaximum(partials.flatMap(category => category.energy_kwh === null ? [] : [category.energy_kwh]));
  const date = data ? new Intl.DateTimeFormat('es-CL', { timeZone: data.timezone, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(data.cutoff_at)) : '';
  return <>
    <div className="consumption-toolbar"><p>Consumo eléctrico{date && ` · ${date}`}</p><button disabled={busy} onClick={() => { background.current = false; setAttempt(value => value + 1); }}><Icon name="refresh" />Actualizar</button></div>
    {busy && <p className="loading-state" role="status">Consultando el consumo del día…</p>}
    {error && <p className="notice notice--error" role="alert"><Icon name="warning" />No se pudo consultar el dashboard. Intente actualizar de nuevo.</p>}
    {data && total && <>
      {total.state !== 'available' && <p className="notice notice--warning" role="status"><Icon name="warning" />{total.state === 'no_data' ? 'Sin datos del consumo de hoy.' : total.state === 'no_meter' ? 'Sin fuente disponible para el total.' : 'Datos incompletos: la cobertura del período es parcial.'}</p>}
      {data.chart_excluded_count > 0 && <p className="notice notice--warning" role="status"><Icon name="warning" />Hay lecturas que no caben en un bloque de 15 minutos. Se conservan en el total diario, sin prorratearlas en el gráfico.</p>}
      <section className="summary-strip panel" aria-label="Resumen diario"><div><h2>{total.source_mode === 'calculated' ? 'Energía total calculada' : total.source_mode === 'measured' ? 'Energía total medida' : 'Energía total'}</h2><p className="summary-value">{total.energy_kwh === null ? 'Sin datos' : `${readableDecimal(total.energy_kwh)} kWh`}</p><p>Consumo acumulado de hoy.</p>{total.source_mode === 'calculated' && <small>Base: {total.base_categories.join(', ')} · Puede no cubrir todas las cargas.</small>}</div><div><h2>Cobertura del período</h2><p className="summary-value">{total.elapsed_duration_us === '0' ? '—' : `${readableDecimal(total.coverage_percent)} %`}</p><p>Tiempo transcurrido con datos válidos.</p></div></section>
      <div className="dashboard-grid"><section className="panel chart-panel"><h2>Evolución del consumo</h2><p className="section-description">Energía por intervalo · kWh</p><EnergyChart rows={[]} points={data.series} period={data.period} timezone={data.timezone} />{total.last_reading_at && <p className="section-description">Última lectura: {shortInstant(total.last_reading_at, data.timezone, true)}</p>}<p className="next-update">Hora de la próxima actualización: {next ? shortInstant(next.toISOString(), data.timezone, true) : 'Consultando…'}</p></section>
      <section className="panel category-panel"><h2>Consumo por categoría</h2><p className="section-description">Mismo período · kWh</p><ul>{partials.map(category => <li key={category.id}><div><span>{category.name}</span><strong>{(category.energy_kwh === null ? null : readableDecimal(category.energy_kwh)) ?? (category.state === 'no_meter' ? 'Sin medidor' : 'Sin datos')}</strong></div>{category.energy_kwh !== null && <div className="category-track"><span style={{ width: `${projectRatio(category.energy_kwh, maximum) * 100}%`, background: categoryColors[category.id] }} /></div>}{category.state === 'incomplete' && <small>Datos incompletos</small>}</li>)}</ul></section></div>
    </>}
  </>;
}
