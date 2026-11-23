"use client";
import { useEffect, useState, type FormEvent } from 'react';
import { costsApi, type CalculationDetail, type CyclePage, type EnergyDistribution as Distribution } from '../../lib/api/costs';
import { useBuildingTimezone } from '../identity/ApplicationFrame';
import { Icon } from '../identity/Icon';
import { EnergyDistribution } from './EnergyDistribution';
import { FinancialPanel } from './FinancialPanel';
import { CostHistory } from './CostHistory';
import { CostTable } from './CostTable';
import { ReproductionDetail } from './ReproductionDetail';
import { CostsEmptyState } from './CostsEmptyState';
import { limitationLabel } from './labels';
import { chargeNames, cycleDate, cycleBoundary, money } from './presentation';

export function CostsConsultation({ page, selected, busy, error, refresh, choose }: {
  page: CyclePage | null; selected: CalculationDetail | null; busy: boolean; error: string;
  refresh: () => void; choose: (calculation: CalculationDetail) => void;
}) {
  const [cycles, setCycles] = useState(page);
  const [draft, setDraft] = useState(selected?.id ?? '');
  const [cycleDraft, setCycleDraft] = useState(selected?.cycle_id ?? '');
  const [selectionError, setSelectionError] = useState('');
  const [selecting, setSelecting] = useState(false);
  const [distribution, setDistribution] = useState<Distribution | null>(null);
  const [distributionError, setDistributionError] = useState(false);
  const [loadingDistribution, setLoadingDistribution] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const timezone = selected?.snapshot.request.timezone;
  useBuildingTimezone(timezone);
  useEffect(() => { setCycles(page); }, [page]);
  useEffect(() => { setDraft(selected?.id ?? ''); setCycleDraft(selected?.cycle_id ?? ''); }, [selected?.id, selected?.cycle_id]);
  useEffect(() => {
    let active = true; const controller = new AbortController();
    setDistribution(null); setDistributionError(false); setLoadingDistribution(Boolean(selected));
    if (selected) void costsApi.distribution(selected.id, controller.signal).then(data => {
      if (data.calculation_id !== selected.id) throw new Error('Mismatched calculation response');
      if (active) { setDistribution(data); setLoadingDistribution(false); }
    }).catch(() => { if (active) { setDistributionError(true); setLoadingDistribution(false); } });
    return () => { active = false; controller.abort(); };
  }, [selected, attempt]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!draft) return;
    setSelecting(true); setSelectionError('');
    try {
      const known = cycles?.items.find(item => item.calculation?.id === draft)?.calculation;
      choose(known ?? await costsApi.calculation(draft));
    } catch { setSelectionError('No se pudo abrir esta revisión. Intente consultar de nuevo.'); }
    finally { setSelecting(false); }
  }
  async function moreCycles() {
    if (!cycles?.next_cursor) return;
    setSelecting(true); setSelectionError('');
    try {
      const next = await costsApi.cycles({ cursor: cycles.next_cursor });
      setCycles({ ...next, items: [...cycles.items, ...next.items] });
    } catch { setSelectionError('No se pudieron consultar más ciclos. Intente de nuevo.'); }
    finally { setSelecting(false); }
  }
  const latest = cycles?.items.find(item => item.id === cycleDraft)?.calculation;
  const draftCalculation = selected?.cycle_id === cycleDraft ? selected : latest;
  const known = cycles?.items.some(item => item.id === selected?.cycle_id);
  const currentDistribution = distribution?.calculation_id === selected?.id ? distribution : null;
  return <div className="costs-consultation">
    <div className="consumption-toolbar"><p>Consulta del suministro general · Tarifa BT4.3</p><button disabled={busy} onClick={refresh}><Icon name="refresh" />Actualizar</button></div>
    {selected?.snapshot.profile?.source_refs.includes('synthetic:costs-demo-v1') && <p className="notice cost-demo-notice">Demostración local: ciclo de muestra, mediciones simuladas, tarifas y boleta ilustrativas, sin validez comercial.</p>}
    {busy && <p role="status" className="loading-state">Consultando costos…</p>}
    {error && <p className="notice notice--error" role="alert">{error}<button onClick={refresh}>Reintentar</button></p>}
    {cycles && cycles.items.length > 0 && <form className="panel cost-filters" onSubmit={submit}>
      <label>Ciclo de consumo<select value={cycleDraft} onChange={event => { setCycleDraft(event.target.value); setDraft(cycles.items.find(item => item.id === event.target.value)?.calculation?.id ?? ''); }}>
        {cycles.items.map(cycle => <option key={cycle.id} value={cycle.id} disabled={!cycle.calculation}>{cycleBoundary(cycle.start_at,cycle.end_at,cycle.timezone)} — {cycleBoundary(cycle.end_at,cycle.start_at,cycle.timezone)}{!cycle.calculation && ' · Sin cálculo'}</option>)}
        {selected && !known && <option value={selected.cycle_id}>{cycleBoundary(selected.snapshot.request.start,selected.snapshot.request.end,timezone!)} — {cycleBoundary(selected.snapshot.request.end,selected.snapshot.request.start,timezone!)} · Histórica</option>}
      </select></label>
      <label>Revisión<select value={draft} onChange={event => setDraft(event.target.value)}>
        <option value={draftCalculation?.id ?? ''}>Revisión {draftCalculation?.revision ?? '—'}</option>
        {latest && latest.id !== draftCalculation?.id && <option value={latest.id}>Revisión {latest.revision} · Más reciente</option>}
        {draftCalculation?.previous_id && <option value={draftCalculation.previous_id}>Anterior a la revisión {draftCalculation.revision}</option>}
      </select></label>
      <span className="cost-cycle-state">{selected?.temporal_state === 'en_curso' ? 'Ciclo en curso' : selected ? 'Ciclo cerrado' : 'Sin cálculo'}</span>
      <button className="primary-button" disabled={selecting || !draft} type="submit">{selecting ? 'Consultando…' : 'Consultar'}</button>
      {cycles.next_cursor && <button type="button" disabled={selecting} onClick={moreCycles}>Más ciclos</button>}
    </form>}
    {selectionError && <p className="notice notice--error" role="alert">{selectionError}</p>}
    {!busy && !error && !selected && (cycles?.items.length ? <p className="panel empty-state">El ciclo seleccionado no tiene un cálculo registrado. Consulte otro ciclo o el historial.</p> : <CostsEmptyState />)}
    {selected && <>
      {selected.temporal_state === 'en_curso' && <p className="notice notice--warning">Resultado provisional del consumo observado. No proyecta el costo al cierre.</p>}
      {(selected.complete_total === null || selected.execution_state === 'fallido') && <p className="notice notice--warning" role="status">{selected.execution_state === 'fallido' ? 'No se pudo completar el cálculo.' : 'Cálculo incompleto.'} {selected.reason_codes.map(limitationLabel).join(' ')}</p>}
      <section className="panel cost-summary" aria-label="Resumen del ciclo">
        <div><h2>{selected.complete_total === null ? 'Subtotal disponible' : 'Costo completo del ciclo'}</h2><p className="summary-value">{money(selected.complete_total ?? selected.available_subtotal)}</p><p>{selected.complete_total === null ? 'CLP · Suma de conceptos calculables' : 'CLP · Según perfil del cálculo'}</p></div>
        <div><h2>Cargo de energía</h2><p className="summary-value">{money(currentDistribution?.energy_amount)}</p><p>Base del reparto por categoría · Neto</p></div>
        <div><h2>Otros cargos e impuestos</h2><p className="summary-value">{money(currentDistribution?.other_amount)}</p><p>{selected.complete_total === null ? 'Costo completo no disponible' : 'Importes fuera del reparto'}</p></div>
      </section>
      <EnergyDistribution data={currentDistribution} busy={loadingDistribution || (!currentDistribution && !distributionError)} error={distributionError} retry={() => setAttempt(value => value + 1)} timezone={timezone!} />
      <div className="cost-detail-grid">
        <section className="panel" aria-labelledby="cost-breakdown-heading"><h2 id="cost-breakdown-heading">Desglose del ciclo</h2><p className="section-description">Cálculo · Revisión {selected.revision} · Importes en CLP</p>
          <table className="cost-charges"><thead><tr><th>Concepto</th><th className="numeric">Importe</th></tr></thead><tbody>
            {selected.components.map(row => <tr key={row.code}><th scope="row">{chargeNames[row.kind]}<small>{row.tax_basis === 'neto' ? 'Neto' : row.tax_basis === 'impuesto_incluido' ? 'Impuesto incluido' : 'Impuesto separado'}{row.state === 'limited' && ' · Limitado'}</small></th><td className="numeric">{row.presented_amount === null ? 'No calculable' : money(row.presented_amount)}</td></tr>)}
            {selected.net_total !== null && <tr><th scope="row">Subtotal neto</th><td className="numeric">{money(selected.net_total)}</td></tr>}
          </tbody><tfoot><tr><th scope="row">{selected.complete_total === null ? 'Subtotal disponible' : 'Costo completo'}</th><td className="numeric">{money(selected.complete_total ?? selected.available_subtotal)}</td></tr></tfoot></table>
          <details className="cost-inline-details"><summary>Ver bases y reglas de cada cargo</summary><div className="table-scroll"><CostTable rows={selected.components} /></div></details>
        </section>
        <FinancialPanel key={selected.id} calculation={selected} administrative={false} />
      </div>
    </>}
    <details className="panel cost-disclosure"><summary>Historial de ciclos y revisiones <span>Consultar períodos anteriores</span></summary><CostHistory onSelect={choose} /></details>
    {selected && <div className="panel cost-provenance"><ReproductionDetail calculation={selected} /><p className="cost-footnote">Corte del cálculo: {cycleDate(selected.cutoff_at ?? selected.snapshot.cutoff_at, timezone!)} · {selected.execution_state === 'completado' ? 'Ejecución completada' : 'Ejecución fallida'} · {selected.sufficiency === 'completo' ? 'Evidencia completa' : 'Evidencia insuficiente'}.</p></div>}
  </div>;
}
