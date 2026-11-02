/** Read-only audit009 projection with explicit UTC, filters, cutoff and runtime permission checks. */
"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { identityApi, type AdministrationEntry } from "../../lib/api/identity";
import { subscribePrivateCleanup, type Activity } from "../../lib/api/session";
import { SessionGuard, useSession } from "./SessionProvider";

/** Render stable trusted actors and safe target/result references; never original payloads or edit/delete controls. */
export function HistoryTable({ items }: { items: AdministrationEntry[] }) {
  if (!items.length) return <p>No hay registros en este período.</p>;
  return <table><caption>Historial administrativo · UTC</caption><thead><tr><th>Fecha (UTC)</th><th>Actor</th><th>Acción</th><th>Destino</th><th>Resultado</th><th>Referencia</th></tr></thead><tbody>{items.map((entry) => <tr key={entry.id}>
    <td>{new Date(entry.occurred_at).toISOString()}</td><td>{entry.actor.kind === "process" ? `Proceso: ${entry.actor.process_code}` : entry.actor.kind === "account" ? `Cuenta: ${entry.actor.account_id}` : "No autenticado"}</td>
    <td>{entry.action}</td><td>{entry.target.module} / {entry.target.entity_type} / {entry.target.id ?? "Sin objeto"} · revisión {entry.target.revision ?? "No aplica"}</td><td>{entry.result} · {entry.reason_code}</td><td>{entry.operation_ref}</td>
  </tr>)}</tbody></table>;
}

/** Fetch only after current admin permission; stale or invalidated responses cannot refill private history. */
export function AdministrationHistory() {
  const { status, session } = useSession();
  const [items, setItems] = useState<AdministrationEntry[]>([]);
  const [filters, setFilters] = useState({ from: "", to: "", action: "", result: "", actor_id: "", target_id: "" });
  const [applied, setApplied] = useState<Record<string, string>>({});
  const [cursor, setCursor] = useState<string | null>(null);
  const [cutoff, setCutoff] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const initialNavigation = useRef(true);
  const permitted = status === "authenticated" && !!session?.permissions.includes("administration.history.read");

  async function load(values: Record<string, string>, next?: string, activity: Activity = "interactive") {
    /** Keep one filter/cutoff continuation and distinguish network failure from an empty audit result. */
    const request = ++sequence.current;
    setBusy(true); setError("");
    try {
      const page = await identityApi.history({ ...values, ...(next ? { cursor: next } : {}) }, activity);
      if (request === sequence.current) { setItems(page.items); setCursor(page.next_cursor); setCutoff(page.cutoff_at); }
    } catch (failure) { if (request === sequence.current) setError(failure instanceof Error ? failure.message : "No se pudo consultar el historial."); }
    finally { if (request === sequence.current) setBusy(false); }
  }

  useEffect(() => {
    /** Erase all private rows before tab/session revalidation and invalidate pending responses. */
    return subscribePrivateCleanup(() => {
      sequence.current += 1; setItems([]); setCursor(null); setCutoff(""); setApplied({});
      setFilters({ from: "", to: "", action: "", result: "", actor_id: "", target_id: "" });
    });
  }, []);
  useEffect(() => {
    /** First navigation is interactive; automatic tab/session revalidation never renews idle time. */
    if (permitted) {
      const activity = initialNavigation.current ? "interactive" : "background";
      initialNavigation.current = false;
      void load({}, undefined, activity);
    }
    return () => { sequence.current += 1; };
  }, [permitted]);

  function submit(event: FormEvent) {
    /** Treat date inputs explicitly as UTC, rather than the browser's implicit local timezone. */
    event.preventDefault();
    const values: Record<string, string> = { ...filters };
    for (const name of ["from", "to"]) { if (values[name]) values[name] = new Date(values[name]+"Z").toISOString(); }
    setApplied(values); void load(values);
  }
  return <SessionGuard permission="administration.history.read">
    <form onSubmit={submit}>
      <p><label>Desde (UTC)<input type="datetime-local" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} /></label><label>Hasta (UTC)<input type="datetime-local" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} /></label></p>
      <p><label>Acción<input value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })} /></label><label>Resultado<select value={filters.result} onChange={(event) => setFilters({ ...filters, result: event.target.value })}><option value="">Todos</option><option value="allowed">Permitido</option><option value="denied">Denegado</option><option value="rejected">Rechazado</option></select></label></p>
      <p><label>UUID del actor<input value={filters.actor_id} onChange={(event) => setFilters({ ...filters, actor_id: event.target.value })} /></label><label>UUID del destino<input value={filters.target_id} onChange={(event) => setFilters({ ...filters, target_id: event.target.value })} /></label></p>
      <button disabled={busy}>Consultar historial</button>
    </form>
    {busy ? <p role="status">Cargando historial…</p> : error ? <p role="alert">{error}</p> : <HistoryTable items={items} />}
    {cutoff && <p>Corte de consulta (UTC): {new Date(cutoff).toISOString()}</p>}
    {cursor && <button onClick={() => void load(applied, cursor)}>Página siguiente</button>}
  </SessionGuard>;
}
