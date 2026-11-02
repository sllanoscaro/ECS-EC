/** Runtime-only account administration, with cleanup and stale-response protection on every revalidation. */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { identityApi, type AccountDraft, type AccountMode, type AccountView } from "../../lib/api/identity";
import { subscribePrivateCleanup, type Activity } from "../../lib/api/session";
import { AccountForm } from "./AccountForm";
import { AccountTable } from "./AccountTable";
import { SessionGuard, useSession } from "./SessionProvider";

/** Fetch/list/edit only while current normal permissions permit it; never populate static HTML. */
export function AccountAdministration() {
  const { status: sessionStatus, session, invalidate } = useSession();
  const [items, setItems] = useState<AccountView[]>([]);
  const [selected, setSelected] = useState<AccountView>();
  const [mode, setMode] = useState<AccountMode>("create");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [next, setNext] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const previousFilters = useRef<string | null>(null);
  const authorized = sessionStatus === "authenticated" && !!session?.permissions.includes("identity.accounts.read");

  const load = useCallback(async (cursor?: string, activity: Activity = "interactive") => {
    /** Preserve the user's chosen filters while rejecting responses from earlier filters or sessions. */
    const request = ++sequence.current;
    setBusy(true); setError("");
    try {
      const result = await identityApi.list({ role, status, cursor }, activity);
      if (request === sequence.current) { setItems(result.items); setNext(result.next_cursor); }
    } catch (failure) { if (request === sequence.current) setError(failure instanceof Error ? failure.message : "No se pudieron cargar las cuentas."); }
    finally { if (request === sequence.current) setBusy(false); }
  }, [role, status]);

  useEffect(() => {
    /** Clear private rows/selection synchronously when the session provider invalidates a view. */
    return subscribePrivateCleanup(() => { sequence.current += 1; setItems([]); setSelected(undefined); setNext(null); });
  }, []);
  useEffect(() => {
    /** Person navigation/filter changes are interactive; restoring a verified tab is background. */
    if (authorized) {
      const signature = `${role}:${status}`;
      const activity = previousFilters.current === null || previousFilters.current !== signature ? "interactive" : "background";
      previousFilters.current = signature;
      void load(undefined, activity);
    }
    return () => { sequence.current += 1; };
  }, [authorized, load, role, status]);

  async function save(draft: AccountDraft) {
    /** Use the current received revision; own effective changes clear context and require reentry. */
    const row = mode === "create" ? await identityApi.create(draft) : mode === "edit" ? await identityApi.update(selected!, draft) : await identityApi.reset(selected!, draft);
    if (row.id === session?.account.id && row.revision !== selected?.revision) { invalidate(); window.location.assign("/ingreso/"); return; }
    setSelected(row); setMode("edit"); await load();
  }
  async function reloadSelected() {
    /** Explicitly reload a conflicted revision before another edit; never retry an ambiguous write automatically. */
    if (selected) { try { setSelected(await identityApi.get(selected.id)); } catch (failure) { setError(failure instanceof Error ? failure.message : "No se pudo recargar."); } }
  }
  return <SessionGuard permission="identity.accounts.read">
    <p><label>Filtrar perfil<select value={role} onChange={(event) => setRole(event.target.value)}><option value="">Todos</option><option value="operador">Operador</option><option value="administrador_tecnico">Administrador técnico</option></select></label></p>
    <p><label>Filtrar estado<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option><option value="active">Activo</option><option value="inactive">Inactivo</option></select></label></p>
    <AccountTable items={items} busy={busy} error={error} selfId={session?.account.id ?? ""} select={(account, reset) => { setSelected(account); setMode(reset ? "reset" : "edit"); }} />
    {next && <button onClick={() => void load(next)}>Página siguiente</button>}
    <p><button onClick={() => { setSelected(undefined); setMode("create"); }}>Nueva cuenta</button>{selected && <button onClick={reloadSelected}>Recargar cuenta</button>}</p>
    <AccountForm key={`${selected?.id ?? "new"}:${selected?.revision ?? 0}:${mode}`} account={selected} mode={mode} save={save} />
  </SessionGuard>;
}
