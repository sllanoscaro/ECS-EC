/** Structured004 physical-supply configuration with explicit preconditions and draft preservation on conflict. */
"use client";
import { useState, type FormEvent } from "react";
import { costsApi, financialApi, type SupplyInput, type SupplyDetail } from "../../lib/api/costs";
import { useFinancialOperation } from "./useFinancialOperation";

/** Copy only writable administrative fields, keeping the server's revision outside the request body. */
function writable(value: SupplyDetail): SupplyInput {
  const { general_board_ref, category_id, general_source_id, distributor, location, connection_conditions, document_refs, measurement_point_differences } = value;
  return { general_board_ref, category_id, general_source_id, distributor, location, connection_conditions, document_refs, measurement_point_differences };
}

/** Create withIf-None-Match or edit the last-read strong ETag; only explicit reload may replace a conflicted draft. */
export function SupplyEditor({ current, onSaved }: { current: SupplyDetail | null; onSaved: (value: SupplyDetail) => void }) {
  const [reference, setReference] = useState(current);
  const [body, setBody] = useState<SupplyInput>(current ? writable(current) : { general_board_ref: "", category_id: "CAT-01", general_source_id: "",
    distributor: null, location: null, connection_conditions: null, document_refs: [], measurement_point_differences: [] });
  const operation = useFinancialOperation();
  const [reloadError, setReloadError] = useState(false);
  function patch(value: Partial<SupplyInput>) { /** Preserve every other draft field when one supply attribute changes. */ setBody(old => ({ ...old, ...value })); }
  function submit(event: FormEvent) {
    /** Bind the operation identity to both the exact body and the reviewed prior revision. */
    event.preventDefault(); void operation.run({ body, previous: reference?.revision }, key => financialApi.saveSupply(body, key, reference), value => { setReference(value); onSaved(value); });
  }
  async function reload() {
    /** Review latest state only at the user's explicit conflict action; an error never implies an empty supply. */
    setReloadError(false);
    try { const value = await costsApi.supply(); setReference(value); setBody(writable(value)); }
    catch { setReloadError(true); }
  }
  return <form onSubmit={submit}><h2>Suministro general · {reference ? `Revisión ${reference.revision}` : "Alta inicial"}</h2>
    <p>La fuente debe ser la CAT-01 física configurada en consumo. No se inventan precios ni condiciones del suministro.</p>
    <fieldset disabled={operation.busy}>
      <label>Tablero general<input required value={body.general_board_ref} onChange={e => { patch({ general_board_ref: e.target.value }); }} /></label>
      <label>UUID del medidor general<input required value={body.general_source_id} onChange={e => { patch({ general_source_id: e.target.value }); }} /></label>
      <label>Distribuidora<input value={body.distributor ?? ""} onChange={e => { patch({ distributor: e.target.value || null }); }} /></label>
      <label>Ubicación del suministro<input value={body.location ?? ""} onChange={e => { patch({ location: e.target.value || null }); }} /></label>
      <label>Condiciones de conexión<input value={body.connection_conditions ?? ""} onChange={e => { patch({ connection_conditions: e.target.value || null }); }} /></label>
      <label>Fuentes documentales del suministro (una por línea)<textarea value={body.document_refs.join("\n")} onChange={e => { patch({ document_refs: e.target.value.split("\n").filter(Boolean) }); }} /></label>
      <label>Diferencias del punto de medición (una por línea)<textarea value={body.measurement_point_differences.join("\n")} onChange={e => { patch({ measurement_point_differences: e.target.value.split("\n").filter(Boolean) }); }} /></label>
      <button type="submit">Confirmar suministro</button>
    </fieldset>
    {operation.error && <p role="alert">{operation.error}</p>}
    {operation.conflict && <button type="button" onClick={() => { void reload(); }}>Revisar suministro actual</button>}
    {reloadError && <p role="alert">No se pudo revisar el suministro actual. Se conserva el borrador.</p>}
  </form>;
}
