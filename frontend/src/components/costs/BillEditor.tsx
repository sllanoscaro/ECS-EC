/** Structured manual invoice editor; document amounts are independent from calculated values and retain their signs. */
"use client";
import { useState, type FormEvent } from "react";
import { financialApi, type BillInput, type BillDetail, type CalculationDetail, type BillLine } from "../../lib/api/costs";
import { useFinancialOperation } from "./useFinancialOperation";

/** Keep only writable document fields from a returned immutable revision. */
function writable(bill: BillDetail): BillInput {
  const { supply_id, external_identifier, issued_at, start, end, timezone, declared_start, declared_end,
    boundary_criterion, boundary_limited, document_reference, currency, energy_read, demand_read, demand_billed, declared_tax, total_payable, lines } = bill;
  return { supply_id, external_identifier, issued_at, start, end, timezone, declared_start, declared_end,
    boundary_criterion, boundary_limited, document_reference, currency, energy_read, demand_read, demand_billed, declared_tax, total_payable, lines };
}

/** Edit actual invoice fields; errors preserve entries and412 requires an explicit reload/review action. */
export function BillEditor({ calculation, previous = null, onSaved }: { calculation: CalculationDetail; previous?: BillDetail | null; onSaved: (bill: BillDetail) => void }) {
  const [current, setCurrent] = useState(previous);
  const [body, setBody] = useState<BillInput>(() => previous ? writable(previous) : {
    supply_id: calculation.snapshot.supply_id, external_identifier: "", issued_at: "", start: calculation.snapshot.request.start,
    end: calculation.snapshot.request.end, timezone: calculation.snapshot.request.timezone, declared_start: null, declared_end: null,
    boundary_criterion: "Límites efectivos declarados en boleta", boundary_limited: false, document_reference: "", currency: "CLP",
    energy_read: null, demand_read: null, demand_billed: null, declared_tax: null, total_payable: "", lines: [],
  });
  const operation = useFinancialOperation();
  const [reloadError, setReloadError] = useState(false);
  function patch(value: Partial<BillInput>) { /** Preserve unrelated manual fields while editing one document property. */ setBody(old => ({ ...old, ...value })); }
  function editLine(index: number, value: Partial<BillLine>) { /** Replace one typed signed line without recomputing invoice totals. */ patch({ lines: body.lines.map((line, i) => i === index ? { ...line, ...value } : line) }); }
  function submit(event: FormEvent) {
    /** Confirm the independently entered document with a current revision precondition on correction. */
    event.preventDefault(); void operation.run({ body, previous: current?.revision }, key => financialApi.saveBill(body, key, current), onSaved);
  }
  async function reload() {
    /** Reload only on explicit review, replacing the draft after the administrator chose to inspect current state. */
    if (!current) return;
    try { const latest = await financialApi.bill(current.id); setCurrent(latest); setBody(writable(latest)); setReloadError(false); }
    catch { setReloadError(true); }
  }
  return <form onSubmit={submit}><h2>{current ? `Corregir boleta · revisión ${current.revision}` : "Registrar boleta manual"}</h2>
    <p>Confirme el período y los valores del documento; no se ajustan mediciones ni tarifas para igualarlos.</p><fieldset disabled={operation.busy}>
    <label>Identificador de boleta<input required readOnly={Boolean(current)} value={body.external_identifier} onChange={e => { patch({ external_identifier: e.target.value }); }} /></label>
    <label>Emisión con offset<input required value={body.issued_at} onChange={e => { patch({ issued_at: e.target.value }); }} /></label>
    <label>Inicio efectivo de boleta<input required value={body.start} onChange={e => { patch({ start: e.target.value }); }} /></label>
    <label>Fin efectivo de boleta<input required value={body.end} onChange={e => { patch({ end: e.target.value }); }} /></label>
    <label>Criterio de lectura de boleta<input required value={body.boundary_criterion} onChange={e => { patch({ boundary_criterion: e.target.value }); }} /></label>
    <label>Inicio declarado (si difiere)<input value={body.declared_start ?? ""} onChange={e => { patch({ declared_start: e.target.value || null }); }} /></label>
    <label>Fin declarado (si difiere)<input value={body.declared_end ?? ""} onChange={e => { patch({ declared_end: e.target.value || null }); }} /></label>
    <label><input type="checkbox" checked={body.boundary_limited} onChange={e => { patch({ boundary_limited: e.target.checked }); }} />Límites efectivos limitados</label>
    <label>Referencia del documento<input required value={body.document_reference} onChange={e => { patch({ document_reference: e.target.value }); }} /></label>
    <label>Energía leída (kWh, si consta)<input value={body.energy_read ?? ""} onChange={e => { patch({ energy_read: e.target.value || null }); }} /></label>
    <label>Demanda leída (kW, si consta)<input value={body.demand_read ?? ""} onChange={e => { patch({ demand_read: e.target.value || null }); }} /></label>
    <label>Demanda facturada (kW, si consta)<input value={body.demand_billed ?? ""} onChange={e => { patch({ demand_billed: e.target.value || null }); }} /></label>
    <label>Impuesto declarado (CLP, si consta)<input value={body.declared_tax ?? ""} onChange={e => { patch({ declared_tax: e.target.value || null }); }} /></label>
    <label>Total a pagar de boleta (CLP)<input required value={body.total_payable} onChange={e => { patch({ total_payable: e.target.value }); }} /></label>
    {body.lines.map((line, index) => <fieldset key={index}><legend>Concepto {index + 1}</legend>
      <label>Código de concepto {index + 1}<input required value={line.code} onChange={e => { editLine(index, { code: e.target.value }); }} /></label>
      <label>Descripción {index + 1}<input required value={line.description} onChange={e => { editLine(index, { description: e.target.value }); }} /></label>
      <label>Cantidad {index + 1}<input value={line.quantity ?? ""} onChange={e => { editLine(index, { quantity: e.target.value || null }); }} /></label>
      <label>Unidad {index + 1}<select value={line.unit} onChange={e => { editLine(index, { unit: e.target.value as BillLine['unit'] }); }}>{["kWh", "kW", "cycle", "CLP"].map(unit => <option key={unit}>{unit}</option>)}</select></label>
      <label>Importe CLP {index + 1}<input required value={line.amount} onChange={e => { editLine(index, { amount: e.target.value }); }} /></label>
      <label>Base tributaria {index + 1}<select value={line.tax_basis} onChange={e => { editLine(index, { tax_basis: e.target.value as BillLine['tax_basis'] }); }}>{["neto", "impuesto_incluido", "impuesto_separado"].map(basis => <option key={basis}>{basis}</option>)}</select></label>
      <label>Impuesto del concepto {index + 1}<input value={line.tax_amount ?? ""} onChange={e => { editLine(index, { tax_amount: e.target.value || null }); }} /></label>
      <label>Relación con ciclo {index + 1}<select value={line.cycle_relation} onChange={e => { editLine(index, { cycle_relation: e.target.value as BillLine['cycle_relation'] }); }}>{["current_cycle", "outside_cycle", "unknown"].map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Referencia del concepto {index + 1}<input required value={line.document_reference} onChange={e => { editLine(index, { document_reference: e.target.value }); }} /></label>
      <button type="button" onClick={() => { patch({ lines: body.lines.filter((_, i) => i !== index) }); }}>Quitar concepto {index + 1}</button>
    </fieldset>)}
    <button type="button" onClick={() => { patch({ lines: [...body.lines, { code: "", description: "", quantity: null, unit: "kWh", amount: "", tax_basis: "neto", tax_amount: null, cycle_relation: "current_cycle", document_reference: body.document_reference }] }); }}>Añadir concepto</button>
    <button type="submit">Confirmar boleta</button></fieldset>
    {operation.error && <p role="alert">{operation.error}</p>}{reloadError && <p role="alert">No se pudo revisar la boleta actual; se conserva el borrador.</p>}
    {operation.conflict && current && <button type="button" onClick={() => { void reload().catch(() => undefined); }}>Revisar boleta actual</button>}
  </form>;
}
