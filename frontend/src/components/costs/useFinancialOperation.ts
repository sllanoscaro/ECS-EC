/** Immediate duplicate-submit guard and same-body operation identity, held only in memory. */
"use client";
import { useRef, useState } from "react";
import { limitationLabel } from "./labels";
import { Problem } from "../../lib/api/session";

/** Retain an idempotency key after failure; only a changed body/reference or confirmed success starts another operation. */
export function useFinancialOperation() {
  const operation = useRef<{ signature: string; key: string } | null>(null);
  const active = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  async function run<T>(signature: unknown, send: (key: string) => Promise<T>, saved: (value: T) => void) {
    /** Protect even two submits in the same render tick, preserving draft state on every failed response. */
    if (active.current) return;
    const encoded = JSON.stringify(signature);
    if (operation.current?.signature !== encoded) operation.current = { signature: encoded, key: crypto.randomUUID() };
    active.current = true; setBusy(true); setError(""); setConflict(false);
    try { const value = await send(operation.current!.key); operation.current = null; saved(value); }
    catch (failure) {
      setError(failure instanceof Problem ? ([409, 412].includes(failure.status) ? "La revisión cambió. Revise el estado actual antes de confirmar otra operación." : failure.code === "physical_general_required" ? limitationLabel(failure.code) : failure.message) : "No se pudo confirmar la operación. Reintente sin cambiar datos para conservar su identidad.");
      setConflict(failure instanceof Problem && [409, 412].includes(failure.status));
    } finally { active.current = false; setBusy(false); }
  }
  return { busy, error, conflict, run };
}
