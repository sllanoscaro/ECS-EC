/** Same-origin004 client; exact monetary strings and persisted server results are authoritative. */
import { apiRequest, sessionActivityHeaders } from "./session";
import type { CalculationDetail, CalculateRequest, SupplyDetail, EnergyDistribution, CostsReadiness } from "./costs-types";
export type * from "./costs-types";

import type { CycleDetail, CyclePage, BillPage, ProfilePage } from "./costs-types";
/** UI vocabulary for the generated immutable cycle contract. */
export type Cycle = CycleDetail;

/** Stable strong supply tag, derived exclusively from its returned identity/revision. */
export function supplyTag(supply: SupplyDetail) { return `"costs:supply:${supply.id}:${supply.revision}"`; }

export const costsApi = {
  readiness(signal?: AbortSignal) { return apiRequest<CostsReadiness>('/costs/readiness', {signal, headers: sessionActivityHeaders("interactive")}); },
  distribution(id: string, signal?: AbortSignal) {
    return apiRequest<EnergyDistribution>(`/costs/calculations/${encodeURIComponent(id)}/distribution`, { signal, headers: sessionActivityHeaders("interactive") });
  },
  /** Read a deterministic cycle page; no query creates calculations or extends evidence retention. */
  cycles(filters: Record<string, string> = {}, signal?: AbortSignal) {
    return apiRequest<CyclePage>(`/costs/cycles?${new URLSearchParams(filters)}`, { signal, headers: sessionActivityHeaders("interactive") });
  },
  /** Read bounded retained-cycle history using the server's exact selected pair and signed continuation. */
  history(filters: Record<string, string> = {}, signal?: AbortSignal) { return apiRequest<CyclePage>(`/costs/history?${new URLSearchParams(filters)}`, { signal, headers: sessionActivityHeaders("interactive") }); },
  /** Find one actual cycle without silently truncating older histories at the first page. */
  async cycle(id: string, signal?: AbortSignal): Promise<Cycle | null> {
    let cursor: string | null = null;
    do {
      const page: CyclePage = await costsApi.cycles(cursor ? { cursor } : {}, signal);
      const cycle = page.items.find(item => item.id === id);
      if (cycle) return cycle;
      cursor = page.next_cursor;
    } while (cursor);
    return null;
  },
  /** Read a stable calculation revision, including its captured source/profile evidence. */
  calculation(id: string, signal?: AbortSignal) {
    return apiRequest<CalculationDetail>(`/costs/calculations/${encodeURIComponent(id)}`, { signal, headers: sessionActivityHeaders("interactive") });
  },
  /** Read administrative supply configuration, never treat dependency errors as a missing supply. */
  supply(signal?: AbortSignal) { return apiRequest<SupplyDetail>("/costs/supply", { signal, headers: sessionActivityHeaders("interactive") }); },
  /** Explicit new operation or same-body retry; server authorization precedes idempotent replay. */
  calculate(body: CalculateRequest, key: string) {
    return apiRequest<CalculationDetail>("/costs/calculations", { method: "POST", headers: { ...sessionActivityHeaders("interactive"), "Idempotency-Key": key }, body: JSON.stringify(body) });
  },
};

import type { BillInput, BillDetail, ComparisonRequest, ComparisonDetail, SupplyInput, ProfileInput, ProfileDetail } from "./costs-types";
/** Send an explicit financial mutation using the common memory-only session/CSRF context. */
function mutate<T>(path: string, body: unknown, key: string, method = "POST", headers: Record<string, string> = {}) {
  return apiRequest<T>(path, { method, headers: { ...sessionActivityHeaders("interactive"), "Idempotency-Key": key, ...headers }, body: JSON.stringify(body) });
}

export const financialApi = {
  /** List immutable document revisions; every quantity remains a string or explicit null. */
  bills(cycleId: string, signal?: AbortSignal, cursor?: string) { return apiRequest<BillPage>(`/costs/bills?${new URLSearchParams({ cycle_id: cycleId, ...(cursor ? { cursor } : {}) })}`, { signal, headers: sessionActivityHeaders("interactive") }); },
  /** Read a current or selected historical document without creating a comparison. */
  bill(id: string, revision?: number) { return apiRequest<BillDetail>(`/costs/bills/${id}${revision ? `?revision=${revision}` : ""}`, { headers: sessionActivityHeaders("interactive") }); },
  /** Create/correct a bill, preserving its exact last-read revision as a strong precondition. */
  saveBill(body: BillInput, key: string, previous?: BillDetail | null) {
    return mutate<BillDetail>(`/costs/bills${previous ? `/${previous.id}` : ""}`, body, key, previous ? "PUT" : "POST", previous ? { "If-Match": `"costs:bill:${previous.id}:${previous.revision}"` } : {});
  },
  /** Persist only an explicitly confirmed immutable pair selection. */
  compare(body: ComparisonRequest, key: string) { return mutate<ComparisonDetail>("/costs/comparisons", body, key); },
  /** Read a stable historical comparison independently from current revisions. */
  comparison(id: string) { return apiRequest<ComparisonDetail>(`/costs/comparisons/${encodeURIComponent(id)}`, { headers: sessionActivityHeaders("interactive") }); },
  /** Create/update the single supply using the server's strong tag, never an inferred empty state. */
  saveSupply(body: SupplyInput, key: string, previous: SupplyDetail | null) {
    return mutate<SupplyDetail>("/costs/supply", body, key, "PUT", previous ? { "If-Match": supplyTag(previous) } : { "If-None-Match": "*" });
  },
  /** Read complete profile revisions and both saved/published identities for concurrency and selection. */
  profiles(signal?: AbortSignal, cursor?: string) { return apiRequest<ProfilePage>("/costs/profiles" + (cursor ? "?cursor=" + encodeURIComponent(cursor) : ""), { signal, headers: sessionActivityHeaders("interactive") }); },
  /** Append a full-calendar revision against its explicit saved predecessor. */
  saveProfile(body: ProfileInput, key: string) { return mutate<ProfileDetail>("/costs/profiles", body, key); },
};
