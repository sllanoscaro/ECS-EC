/** Same-origin identity client. CSRF/private state lives in memory; HttpOnly bearers stay with the browser. */

export type Role = "operador" | "administrador_tecnico";
export type SessionView = {
  account: { id: string; email: string; role: Role };
  session_state: "normal" | "password_change_required";
  must_change_password: boolean;
  absolute_expires_at: string;
  idle_expires_at: string;
  csrf_token: string;
  permissions: string[];
};
export type Activity = "interactive" | "background";
type FailureListener = (problem: Problem) => void;
const cleanup = new Set<() => void>();
const failures = new Set<FailureListener>();
let csrfToken: string | undefined;
let generation = 0;

export class Problem extends Error {
  /** Carry safe server codes/details and Retry-After; never attach request bodies or credentials. */
  constructor(public status: number, public code: string, message: string, public retryAfter = 0) {
    super(message);
  }
}

/** Register cleanup of a module's private view; return an unsubscribe callback. */
export function subscribePrivateCleanup(listener: () => void) {
  cleanup.add(listener);
  return () => { cleanup.delete(listener); };
}

/** Register session-invalidating failures without persisting identity or secrets. */
export function subscribeSessionFailure(listener: FailureListener) {
  failures.add(listener);
  return () => { failures.delete(listener); };
}

/** Invalidate outstanding private responses and erase CSRF and registered view data. */
export function clearPrivateData() {
  generation += 1;
  csrfToken = undefined;
  for (const listener of cleanup) listener();
}

/** Mark user-initiated actions explicitly; polling/revalidation uses background by default. */
export function sessionActivityHeaders(activity: Activity = "background") {
  return { "X-Session-Activity": activity };
}

/** Restrict return destinations to installed relative routes, without encoded origins or unvalidated query. */
export function safeReturn(value: string | null, routes = ["/cuenta/", "/administracion/usuarios/", "/administracion/historial/"]) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\%\u0000-\u0020]/.test(value)) return "/cuenta/";
  try {
    const url = new URL(value, "https://local.invalid");
    if (url.origin !== "https://local.invalid" || url.search || url.hash || !routes.includes(url.pathname)) return "/cuenta/";
    return url.pathname;
  } catch { return "/cuenta/"; }
}

/** Fetch approved JSON without caching; every API call still authorizes on the server. */
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const epoch = generation;
  const headers = new Headers(options.headers);
  if (!headers.has("X-Session-Activity")) headers.set("X-Session-Activity", "background");
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET" && csrfToken && !headers.has("X-CSRF-Token")) headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: "same-origin", cache: "no-store" });
  if (epoch !== generation) throw new Problem(401, "session_required", "Debe iniciar sesión de nuevo.");
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const problem = new Problem(response.status, body.code ?? "unavailable", body.detail ?? "No se pudo completar la solicitud.", Number(response.headers.get("Retry-After") ?? 0));
    if (response.status === 401 || response.status === 403) {
      clearPrivateData();
      for (const listener of failures) listener(problem);
    }
    throw problem;
  }
  if (epoch !== generation) throw new Problem(401, "session_required", "Debe iniciar sesión de nuevo.");
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

export const sessionApi = {
  /** Read current metadata without renewing activity; CSRF is held only in this module's memory. */
  async read(): Promise<SessionView> {
    const value = await apiRequest<SessionView>("/auth/session");
    csrfToken = value.csrf_token;
    return value;
  },
  /** Obtain independent preauth then submit exact credentials; never persist a password. */
  async login(email: string, password: string): Promise<SessionView> {
    const context = await apiRequest<{ csrf_token: string }>("/auth/csrf");
    const value = await apiRequest<SessionView>("/auth/login", { method: "POST", headers: { "X-CSRF-Token": context.csrf_token }, body: JSON.stringify({ email, password }) });
    csrfToken = value.csrf_token;
    return value;
  },
  /** Revoke the current cookie session through its CSRF-protected endpoint. */
  async logout() { await apiRequest<void>("/auth/logout", { method: "POST" }); },
  /** Change only the caller's password; confirmation is client-only and success requires login again. */
  async changePassword(current_password: string, new_password: string) {
    await apiRequest<void>("/auth/password", { method: "POST", body: JSON.stringify({ current_password, new_password }) });
  },
};
