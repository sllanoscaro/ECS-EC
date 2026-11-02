/** Explicit004 administrative calculation operation; inputs survive validation and same-body retries reuse their key. */
"use client";
import { useRef, useState, type FormEvent } from "react";
import { costsApi, type CalculationDetail, type SupplyDetail, type CalculateRequest } from "../../lib/api/costs";
import { Problem } from "../../lib/api/session";

/** Confirm one real cycle and optional documentary month; a recalculation requires a reason and preserves the prior revision. */
export function CalculationForm({ supply, previous, onSaved, save = costsApi.calculate }: {
  supply: SupplyDetail; previous: CalculationDetail | null; onSaved: (value: CalculationDetail) => void;
  save?: (body: CalculateRequest, key: string) => Promise<CalculationDetail>;
}) {
  const [start, setStart] = useState(previous?.snapshot.request.start ?? "");
  const [end, setEnd] = useState(previous?.snapshot.request.end ?? "");
  const [zone, setZone] = useState(previous?.snapshot.request.timezone ?? "America/Santiago");
  const [reason, setReason] = useState("");
  const [month, setMonth] = useState("");
  const [document, setDocument] = useState("");
  const [criterion, setCriterion] = useState("Límites efectivos documentados");
  const [limited, setLimited] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const active = useRef(false);
  const operation = useRef<{ body: string; key: string } | null>(null);
  async function submit(event: FormEvent) {
    /** Preserve drafts and retry identity after a lost response; change body/new confirmation creates another operation. */
    event.preventDefault(); if (active.current) return; active.current = true;
    const body: CalculateRequest = { supply_id: supply.id, start, end, timezone: zone, boundary_criterion: criterion,
      boundary_limited: limited, reason: reason || null, billing_month_ref: month || null,
      billing_month_source_ref: month ? { document_reference: document, supply_id: supply.id, start, end, billing_month_ref: month } : null };
    const encoded = JSON.stringify(body);
    if (operation.current?.body !== encoded) operation.current = { body: encoded, key: crypto.randomUUID() };
    setBusy(true); setError("");
    try { const result = await save(body, operation.current!.key); operation.current = null; onSaved(result); }
    catch (failure) { setError(failure instanceof Problem ? failure.message : "No se pudo calcular. Puede reintentar la misma operación."); }
    finally { active.current = false; setBusy(false); }
  }
  return <form onSubmit={submit}><h2>{previous ? `Recalcular desde revisión ${previous.revision}` : "Nuevo cálculo"}</h2>
    <p>Suministro {supply.id}, revisión {supply.revision}. Solo CAT-01 física.</p><fieldset disabled={busy}>
    <label>Inicio del ciclo con offset<input required value={start} onChange={event => { setStart(event.target.value); }} /></label>
    <label>Fin del ciclo con offset<input required value={end} onChange={event => { setEnd(event.target.value); }} /></label>
    <label>Zona IANA<input required value={zone} onChange={event => { setZone(event.target.value); }} /></label>
    <label>Criterio de límites<input required value={criterion} onChange={event => { setCriterion(event.target.value); }} /></label>
    <label><input type="checkbox" checked={limited} onChange={event => { setLimited(event.target.checked); }} />El documento solo indica fechas; límites efectivos no confirmados</label>
    <label>Mes de demanda documentado (opcional)<input type="month" value={month} onChange={event => { setMonth(event.target.value); }} /></label>
    <label>Referencia documental del mes<input required={Boolean(month)} value={document} onChange={event => { setDocument(event.target.value); }} /></label>
    <p>Declare el mes solo si la política del perfil exige evidencia explícita y el documento respalda este suministro y ciclo. Sin evidencia, los cargos dependientes quedan limitados.</p>
    <label>Motivo del recálculo<input required={Boolean(previous)} value={reason} onChange={event => { setReason(event.target.value); }} /></label>
    <button type="submit">Confirmar cálculo</button></fieldset>{error && <p role="alert">{error}</p>}
  </form>;
}
