/** Runtime session context mounted before private pages; never embeds a user's data in static export. */
"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { clearPrivateData, Problem, sessionApi, subscribeSessionFailure, type SessionView } from "../../lib/api/session";

type Status = "loading" | "anonymous" | "authenticated" | "error";
type SessionContext = {
  status: Status; session: SessionView | null; error: string | null;
  revalidate: () => Promise<void>; accept: (session: SessionView) => void;
  invalidate: () => void; logout: () => Promise<void>;
};
const Context = createContext<SessionContext | null>(null);

/** Resolve current server state and erase old views before pageshow/focus or cross-tab invalidation. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ status: Status; session: SessionView | null; error: string | null }>({ status: "loading", session: null, error: null });
  const sequence = useRef(0);
  const channel = useRef<BroadcastChannel | null>(null);

  const clear = useCallback(() => {
    /** Cancel stale responses and clear all registered private contexts. */
    sequence.current += 1;
    document.documentElement.setAttribute("data-identity-pending", "");
    clearPrivateData();
    setState({ status: "anonymous", session: null, error: null });
  }, []);
  const revalidate = useCallback(async () => {
    /** Hide previous identity before network validation; a network error grants no access. */
    const request = ++sequence.current;
    document.documentElement.setAttribute("data-identity-pending", "");
    clearPrivateData();
    setState({ status: "loading", session: null, error: null });
    try {
      const session = await sessionApi.read();
      if (request === sequence.current) setState({ status: "authenticated", session, error: null });
    } catch (error) {
      if (request === sequence.current) setState({ status: error instanceof Problem && error.status === 401 ? "anonymous" : "error", session: null, error: error instanceof Problem ? error.message : "No se pudo comprobar la sesión." });
    }
  }, []);
  const invalidate = useCallback(() => {
    /** Notify other tabs using a fixed signal with no account, bearer or CSRF value. */
    clear();
    channel.current?.postMessage("changed");
  }, [clear]);
  const accept = useCallback((session: SessionView) => {
    /** Apply a fresh successful login response after discarding all previous view data. */
    sequence.current += 1;
    setState({ status: "authenticated", session, error: null });
  }, []);
  const logout = useCallback(async () => {
    /** Always clear local private data; a failed durable logout remains an explicit error. */
    try { await sessionApi.logout(); } finally { invalidate(); }
  }, [invalidate]);

  useEffect(() => {
    /** Subscribe to browser activation and fixed cross-tab signals; remove all listeners on unmount. */
    void revalidate();
    const activate = () => { void revalidate(); };
    const hide = () => { document.documentElement.setAttribute("data-identity-pending", ""); };
    window.addEventListener("pageshow", activate);
    window.addEventListener("focus", activate);
    window.addEventListener("pagehide", hide);
    const failure = subscribeSessionFailure((problem) => { if (problem.status === 401) clear(); else void revalidate(); });
    if (typeof BroadcastChannel !== "undefined") {
      channel.current = new BroadcastChannel("ecs-ec-session");
      channel.current.onmessage = (message) => { if (message.data === "changed") { clear(); void revalidate(); } };
    }
    return () => { sequence.current += 1; window.removeEventListener("pageshow", activate); window.removeEventListener("focus", activate); window.removeEventListener("pagehide", hide); failure(); channel.current?.close(); channel.current = null; };
  }, [clear, revalidate]);

  useLayoutEffect(() => {
    /** Reveal private DOM only after the verified identity and cleaned children have committed. */
    if (state.status === "authenticated") document.documentElement.removeAttribute("data-identity-pending");
  }, [state]);

  useEffect(() => {
    /** Revalidate at the earliest known expiry; server time and limits remain authoritative. */
    if (!state.session) return;
    const expiry = Math.min(Date.parse(state.session.idle_expires_at), Date.parse(state.session.absolute_expires_at));
    const timer = setTimeout(() => { void revalidate(); }, Math.max(0, expiry - Date.now()));
    return () => { clearTimeout(timer); };
  }, [state.session, revalidate]);

  return <Context.Provider value={{ ...state, revalidate, accept, invalidate, logout }}>{children}</Context.Provider>;
}

/** Read the mounted runtime context; fail explicitly when a page is outside the provider. */
export function useSession() {
  const context = useContext(Context);
  if (!context) throw new Error("SessionProvider is required");
  return context;
}

/** Render private content only after a current session and optional current permission are known. */
export function SessionGuard({ permission, children }: { permission?: string; children: ReactNode }) {
  const { status, session, error } = useSession();
  if (status === "loading") return <p role="status">Comprobando sesión…</p>;
  if (status === "error") return <p role="alert">{error}</p>;
  if (!session) return <p>Debe <a href="/ingreso/">iniciar sesión</a>.</p>;
  if (session.must_change_password && permission) return <p>Debe <a href="/cuenta/">renovar su contraseña</a>.</p>;
  if (permission && !session.permissions.includes(permission)) return <p role="alert">Acceso denegado.</p>;
  return <section data-private-content>{children}</section>;
}
