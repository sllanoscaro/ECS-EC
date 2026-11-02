/** Selection-bound private query state; neither aborted nor logged-out responses can publish stale data. */
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { consumptionApi, type CategoryId, type DetailResult, type AggregateQueryResult, type Granularity, type Period } from "../../lib/api/consumption";
import { Problem, subscribePrivateCleanup } from "../../lib/api/session";

type QueryState = { key: string; data: DetailResult | AggregateQueryResult | null; loading: boolean; error: string | null };

/** Fetch a full detail response, keyed by every filter and a retry generation, and clear it on session cleanup. */
export function useConsumptionQuery(category: CategoryId, period: Period | null, fetch = consumptionApi.detail, granularity: Granularity = "detail") {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<QueryState>({ key: "", data: null, loading: false, error: null });
  const epoch = useRef(0);
  const key = JSON.stringify([category, period?.start, period?.end, period?.timezone, granularity, attempt]);
  useEffect(() => {
    /** Discard data immediately and additionally guard promise completions from transports that ignore abort. */
    const generation = ++epoch.current;
    const controller = new AbortController();
    setState({ key, data: null, loading: Boolean(period), error: null });
    const clear = subscribePrivateCleanup(() => {
      /** Session changes invalidate both data and the still outstanding network operation. */
      epoch.current += 1; controller.abort(); setState({ key, data: null, loading: false, error: null });
    });
    if (period) void (granularity === "detail" ? fetch(category, period, controller.signal) : consumptionApi.aggregates(category, period, granularity, controller.signal)).then(data => {
      if (generation === epoch.current) setState({ key, data, loading: false, error: null });
    }).catch((error: unknown) => {
      if (generation === epoch.current && !controller.signal.aborted) setState({ key, data: null, loading: false,
        error: error instanceof Problem ? error.message : "No se pudo consultar el consumo." });
    });
    return () => { epoch.current += 1; controller.abort(); clear(); };
  }, [key, category, period?.start, period?.end, period?.timezone, fetch, granularity]);
  const retry = useCallback(() => { setAttempt(value => value + 1); }, []);
  // Render-time key check hides old values before effects run for a newly selected filter.
  return { ...(state.key === key ? state : { data: null, error: null, loading: Boolean(period) }), retry };
}
