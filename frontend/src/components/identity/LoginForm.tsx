/** Accessible account login; exact password values are never cached or retained after submit. */
"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Problem, safeReturn, sessionApi } from "../../lib/api/session";
import { useSession } from "./SessionProvider";

/** Obtain preauth through the client and navigate only to an installed local destination. */
export function LoginForm() {
  const { status, session, accept } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [rateLimited, setRateLimited] = useState(false);
  const [busy, setBusy] = useState(false);
  const [waitUntil, setWaitUntil] = useState(0);
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    /** Count down Retry-After without making automatic authentication attempts. */
    if (!waitUntil) return;
    const timer = setInterval(() => { setRemaining(Math.max(0, Math.ceil((waitUntil-Date.now())/1000))); }, 1000);
    return () => { clearInterval(timer); };
  }, [waitUntil]);

  async function submit(event: FormEvent) {
    /** Submit once, preserve non-secret email on errors and clear the password unconditionally. */
    event.preventDefault();
    if (busy || remaining > 0) return;
    setBusy(true); setMessage(""); setRateLimited(false);
    try {
      const result = await sessionApi.login(email, password);
      accept(result);
      window.location.assign(result.must_change_password ? "/cuenta/" : (new URLSearchParams(window.location.search).has("retorno") ? safeReturn(new URLSearchParams(window.location.search).get("retorno")) : "/"));
    } catch (error) {
      setMessage(error instanceof Problem ? error.message : "No se pudo conectar. Intente de nuevo.");
      if (error instanceof Problem && error.status === 429) { setRateLimited(true); setRemaining(error.retryAfter); setWaitUntil(Date.now()+error.retryAfter*1000); }
    } finally { setPassword(""); setBusy(false); }
  }
  if (status === "loading") return <p className="login-state" role="status">Comprobando sesión…</p>;
  if (session) return <p className="login-state">Sesión iniciada. <a href="/cuenta/">Ir a mi cuenta</a>.</p>;
  return <form className="login-form" onSubmit={submit} aria-busy={busy}>
    <div className="login-field"><label htmlFor="login-email">Correo electrónico</label><input id="login-email" type="email" name="email" placeholder="nombre@ejemplo.cl" autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} required /></div>
    <div className="login-field"><label htmlFor="login-password">Contraseña</label><input id="login-password" type="password" name="password" placeholder="Ingresa tu contraseña" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></div>
    <button className="primary-button login-submit" type="submit" disabled={busy || remaining > 0}>{busy ? "Ingresando…" : "Ingresar"}</button>
    {message && <p className={`notice ${rateLimited ? 'notice--warning' : 'notice--error'}`} role="alert">{message}</p>}
    {remaining > 0 && <p className="login-wait" role="status">Espere {remaining} segundos.</p>}
  </form>;
}
