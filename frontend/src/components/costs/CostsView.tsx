/** Runtime004 workspace: persisted-cycle selection and shared component views, guarded by006. */
"use client";
import { useEffect, useRef, useState } from "react";
import { costsApi, type CalculationDetail, type SupplyDetail, type CyclePage } from "../../lib/api/costs";
import { Problem } from "../../lib/api/session";
import { SessionGuard } from "../identity/SessionProvider";
import { CostBreakdown } from "./CostBreakdown";
import { CalculationForm } from "./CalculationForm";
import { FinancialPanel } from "./FinancialPanel";
import { SupplyEditor } from "./SupplyEditor";
import { ProfileEditor } from "./ProfileEditor";
import { CostHistory } from "./CostHistory";

/** Never mount private IO before current functional permissions are known; unmount on session invalidation. */
export function CostsView({ administrative = false }: { administrative?: boolean }) {
  return <SessionGuard permission={administrative ? "costs.calculations.create" : "costs.read"}><CostsContent administrative={administrative} /></SessionGuard>;
}

/** Select stable result IDs in client URL state; a GET/filter/reload never creates a calculation revision. */
function CostsContent({ administrative }: { administrative: boolean }) {
  const [page, setPage] = useState<CyclePage | null>(null);
  const [supply, setSupply] = useState<SupplyDetail | null>(null);
  const [selected, setSelected] = useState<CalculationDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    /** Abort/discard old workspace loads, preserving no private data across guard unmounts or errors. */
    const epoch = ++generation.current;
    const controller = new AbortController();
    setBusy(true); setSelected(null); setError("");
    void Promise.all([costsApi.cycles({}, controller.signal), administrative ? costsApi.supply(controller.signal).catch(failure => {
      if (failure instanceof Problem && failure.status === 404) return null;
      throw failure;
    }) : Promise.resolve(null)]).then(async ([cycles, configuration]) => {
      const id = new URLSearchParams(window.location.search).get("calculation");
      const calculation = id ? await costsApi.calculation(id, controller.signal) : cycles.items[0]?.calculation ?? null;
      if (epoch === generation.current) { setPage(cycles); setSupply(configuration); setSelected(calculation); setBusy(false); }
    }).catch(() => { if (epoch === generation.current) { setError("No se pudieron consultar los costos."); setBusy(false); } });
    return () => { generation.current += 1; controller.abort(); };
  }, [administrative, attempt]);
  function choose(value: CalculationDetail) {
    /** Retain a stable persisted revision across reloads, without dynamic server routes in the static export. */
    setSelected(value);
    const url = new URL(window.location.href); url.searchParams.set("calculation", value.id); window.history.replaceState(null, "", url);
  }
  function saved(value: CalculationDetail) {
    /** Refresh list metadata after a confirmed mutation; subsequent queries only read the persisted revision. */
    choose(value); setAttempt(current => current + 1);
  }
  if (busy) return <p role="status">Consultando costos…</p>;
  return <>
    <button onClick={() => { setAttempt(value => value + 1); }}>Actualizar costos</button>
    {error && <p role="alert">{error}<button onClick={() => { setAttempt(value => value + 1); }}>Reintentar</button></p>}
    {page && <><p>Corte: {page.cutoff_at}</p>{!page.items.length && <p>Sin ciclos registrados.</p>}
      <ul>{page.items.map(cycle => <li key={cycle.id}>{cycle.start_at} → {cycle.end_at} · {cycle.timezone}
        {cycle.calculation && <button onClick={() => { choose(cycle.calculation!); }}>Abrir revisión {cycle.calculation.revision}</button>}</li>)}</ul>
      {page.next_cursor && <p>Hay más ciclos; consulte el historial.</p>}
    </>}
    {administrative && <button onClick={() => {
      /** Start an explicitly new cycle without accidentally treating the selected historical cycle as its predecessor. */
      setSelected(null); const url = new URL(window.location.href); url.searchParams.delete("calculation"); window.history.replaceState(null, "", url);
    }}>Calcular otro ciclo</button>}
    {administrative && <SupplyEditor key={supply ? `${supply.id}:${supply.revision}` : "initial-supply"} current={supply} onSaved={value => { setSupply(value); }} />}
    {administrative && supply && <ProfileEditor supply={supply} />}
    {administrative && (supply ? <CalculationForm key={selected?.id ?? "new"} supply={supply} previous={selected} onSaved={saved} /> : <p>Configure el suministro general antes de calcular.</p>)}
    <CostHistory onSelect={choose} />
    {selected && <><CostBreakdown calculation={selected} /><FinancialPanel key={selected.id} calculation={selected} administrative={administrative} /></>}
  </>;
}
