/** Administrative composition for001 source configuration using006's existing session guard. */
"use client";
import { useEffect, useState } from "react";
import { consumptionApi, type Catalog, type Configuration } from "../../lib/api/consumption";
import { Problem } from "../../lib/api/session";
import { SessionGuard } from "../identity/SessionProvider";
import { ConfigurationForm } from "./ConfigurationForm";

/** Mount administrative IO only while the live session grants source configuration access. */
export function ConsumptionAdministration() {
  return <SessionGuard permission="consumption.configuration.manage"><AdministrationContent /></SessionGuard>;
}

/** Load catalog/current revision together; only a404 configuration response permits the initial editor. */
function AdministrationContent() {
  const [state, setState] = useState<{ catalog: Catalog; configuration: Configuration | null } | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    /** Cancel reads and discard all responses on guard unmount; a503 never becomes empty configuration. */
    let active = true;
    const controller = new AbortController();
    setError(false);
    void Promise.all([consumptionApi.catalog(controller.signal), consumptionApi.configuration(controller.signal).catch(error => {
      if (error instanceof Problem && error.status === 404) return null;
      throw error;
    })]).then(([catalog, configuration]) => { if (active) setState({ catalog, configuration }); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; controller.abort(); };
  }, [attempt]);
  if (error) return <div role="alert">No se pudo cargar la configuración.<button onClick={() => { setAttempt(value => value + 1); }}>Reintentar</button></div>;
  if (!state) return <p role="status">Cargando configuración…</p>;
  return <ConfigurationForm configuration={state.configuration} timezone={state.catalog.timezone} categories={state.catalog.categories} />;
}
