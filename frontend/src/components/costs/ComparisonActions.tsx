/** Explicit immutable-pair selection; loading or saving a bill never triggers comparison creation. */
"use client";
import { useState, type FormEvent } from "react";
import { financialApi, type BillDetail, type CalculationDetail, type ComparisonDetail } from "../../lib/api/costs";
import { useFinancialOperation } from "./useFinancialOperation";

/** Confirm a selected current/historical bill revision against this explicitly displayed calculation revision. */
export function ComparisonActions({ calculation, bills, onSaved }: { calculation: CalculationDetail; bills: readonly BillDetail[]; onSaved: (value: ComparisonDetail) => void }) {
  const [bill, setBill] = useState("");
  const operation = useFinancialOperation();
  function submit(event: FormEvent) {
    /** Only the submit action persists a comparison; retries retain the same explicit pair and operation identity. */
    event.preventDefault(); const body = { calculation_id: calculation.id, bill_revision_id: bill };
    void operation.run(body, key => financialApi.compare(body, key), onSaved);
  }
  return <form onSubmit={submit}><h2>Crear contraste de revisiones elegidas</h2><p>Cálculo elegido: {calculation.id}, revisión {calculation.revision}. Una selección histórica no pasa a ser la actual.</p>
    <fieldset disabled={operation.busy}><label>Revisión de boleta para contrastar<select required value={bill} onChange={event => { setBill(event.target.value); }}>
      <option value="">Seleccione una revisión</option>{bills.map(value => <option value={value.bill_revision_id} key={value.bill_revision_id}>{value.external_identifier} · Revisión {value.revision} · {value.bill_revision_id}</option>)}
    </select></label><button type="submit">Confirmar contraste</button></fieldset>{operation.error && <p role="alert">{operation.error}</p>}
  </form>;
}
