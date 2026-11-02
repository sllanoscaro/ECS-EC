/** Typed administrative identity client; only approved account/history projections cross this boundary. */
import { apiRequest, sessionActivityHeaders, type Activity, type Role } from "./session";

export type AccountView = { id: string; email: string; role: Role; status: "active" | "inactive"; must_change_password: boolean; revision: number; created_at: string; updated_at: string };
export type AccountDraft = { email: string; role: Role; status: "active" | "inactive"; initial_password?: string; new_password?: string };
export type AccountPage = { items: AccountView[]; next_cursor: string | null };
export type AccountMode = "create" | "edit" | "reset";
export type AdministrationEntry = {
  id: string; occurred_at: string; actor: { kind: "account" | "process" | "unauthenticated"; account_id: string | null; process_code: string | null };
  action: string; target: { module: string; entity_type: string; id: string | null; revision: number | null };
  result: "allowed" | "denied" | "rejected"; reason_code: string; operation_ref: string;
};
export type HistoryPage = { items: AdministrationEntry[]; next_cursor: string | null; cutoff_at: string };

/** Retain the exact contract ETag derived from the server's UUID/revision projection. */
export function accountTag(account: AccountView) { return `"identity:${account.id}:${account.revision}"`; }

export const identityApi = {
  /** Query the shared audit projection, preserving fixed cutoff in the signed continuation. */
  history(filters: Record<string, string>, activity: Activity = "background") {
    const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => Boolean(value)));
    return apiRequest<HistoryPage>(`/identity/administration-history?${query}`, { headers: sessionActivityHeaders(activity) });
  },
  /** List current accounts with explicit person/background activity and bounded server pagination. */
  list(filters: { role?: string; status?: string; cursor?: string }, activity: Activity = "background") {
    const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => Boolean(value)) as [string, string][]);
    return apiRequest<AccountPage>(`/identity/accounts?${query}`, { headers: sessionActivityHeaders(activity) });
  },
  /** Reload one account before resolving a revision conflict. */
  get(id: string) { return apiRequest<AccountView>(`/identity/accounts/${encodeURIComponent(id)}`, { headers: sessionActivityHeaders("interactive") }); },
  /** Create with an initial password only; renewal is selected exclusively by the server. */
  create(draft: AccountDraft) {
    return apiRequest<AccountView>("/identity/accounts", { method: "POST", body: JSON.stringify({ email: draft.email, role: draft.role, status: draft.status, initial_password: draft.initial_password }) });
  },
  /** Replace only editable fields and retain the previously received revision as If-Match. */
  update(account: AccountView, draft: AccountDraft) {
    return apiRequest<AccountView>(`/identity/accounts/${account.id}`, { method: "PUT", headers: { "If-Match": accountTag(account) }, body: JSON.stringify({ email: draft.email, role: draft.role, status: draft.status }) });
  },
  /** Reset another account without returning or retaining its earlier credential. */
  reset(account: AccountView, draft: AccountDraft) {
    return apiRequest<AccountView>(`/identity/accounts/${account.id}/password-reset`, { method: "POST", headers: { "If-Match": accountTag(account) }, body: JSON.stringify({ new_password: draft.new_password }) });
  },
};
