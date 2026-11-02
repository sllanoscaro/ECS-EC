/**004 invoice/contrast workspace; current exact-pair selection stays distinct from explicitly selected historical results. */
"use client";
import { useEffect, useState } from "react";
import { costsApi, financialApi, type BillDetail, type CalculationDetail, type ComparisonDetail, type Cycle } from "../../lib/api/costs";
import { BillEditor } from "./BillEditor";
import { ComparisonActions } from "./ComparisonActions";
import { ComparisonTable } from "./ComparisonTable";

/** Fetch immutable document references and current-cycle metadata; never create a comparison in an effect. */
export function FinancialPanel({ calculation, administrative }: { calculation: CalculationDetail; administrative: boolean }) {
  const [bills, setBills] = useState<BillDetail[]>([]);
  const [cycle, setCycle] = useState<Cycle | null>(null);
  const [explicit, setExplicit] = useState<ComparisonDetail | null>(null);
  const [edit, setEdit] = useState<BillDetail | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(true);
  const [more, setMore] = useState<string | null>(null);
  useEffect(() => {
    /** Scope every completion to this selected calculation; guard unmount aborts private requests. */
    let active = true; const controller = new AbortController(); setBusy(true); setError(false);
    void Promise.all([financialApi.bills(calculation.cycle_id, controller.signal), costsApi.cycle(calculation.cycle_id, controller.signal)]).then(([documents, cycles]) => {
      if (active) { setBills([...documents.items]); setMore(documents.next_cursor); setCycle(cycles); setBusy(false); }
    }).catch(() => { if (active) { setError(true); setBusy(false); } });
    return () => { active = false; controller.abort(); };
  }, [calculation.cycle_id, attempt]);
  function savedBill(value: BillDetail) {
    /** Refresh current-pair status after a document revision while preserving the previous comparison as history. */
    setEdit(value); setExplicit(null); setAttempt(old => old + 1);
  }
  async function moreBills() {
    /** Append the next immutable page at its signed original cutoff instead of dropping old document revisions. */
    if (!more) return;
    try { const next = await financialApi.bills(calculation.cycle_id, undefined, more); setBills(old => [...old, ...next.items]); setMore(next.next_cursor); }
    catch { setError(true); }
  }
  const current = cycle?.calculation?.id === calculation.id ? cycle.comparison : null;
  if (busy) return <p role="status">Consultando boletas y contraste…</p>;
  if (error) return <p role="alert">No se pudieron consultar las boletas.<button onClick={() => { setAttempt(old => old + 1); }}>Reintentar boletas</button></p>;
  return <section aria-label="Boleta y comparación">
    {!bills.length && <p>Sin boleta registrada</p>}
    {cycle?.comparison_status === "missing_for_selected_revisions" && <p>Contraste pendiente para estas revisiones</p>}
    {cycle?.calculation && cycle.calculation.id !== calculation.id && <p>Está consultando un cálculo histórico. El par actual usa la revisión {cycle.calculation.revision}.</p>}
    <ul>{bills.map(bill => <li key={bill.bill_revision_id}>{bill.external_identifier} · Revisión {bill.revision} · Total a pagar: {bill.total_payable} CLP · Energía leída: {bill.energy_read ?? "No consta"} kWh · Demanda leída: {bill.demand_read ?? "No consta"} kW · Base facturada: {bill.demand_billed ?? "No consta"} kW
      {administrative && <button onClick={() => { setEdit(bill); }}>Corregir boleta revisión {bill.revision}</button>}
    </li>)}</ul>
    {more && <button onClick={() => { void moreBills(); }}>Más revisiones de boleta</button>}
    {current && <ComparisonTable comparison={current} />}
    {explicit && explicit.id !== current?.id && <><p>Contraste confirmado para la selección explícita. Sus referencias pueden ser históricas.</p><ComparisonTable comparison={explicit} /></>}
    {administrative && <>
      <button onClick={() => { setEdit(null); }}>Nueva boleta</button>
      <BillEditor key={edit?.bill_revision_id ?? "new"} calculation={calculation} previous={edit} onSaved={savedBill} />
      <ComparisonActions calculation={calculation} bills={bills} onSaved={value => { setExplicit(value); setAttempt(old => old + 1); }} />
    </>}
  </section>;
}
