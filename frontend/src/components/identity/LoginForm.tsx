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
    setBusy(true); setMessage("");
    try {
      const result = await sessionApi.login(email, password);
      accept(result);
      window.location.assign(result.must_change_password ? "/cuenta/" : safeReturn(new URLSearchParams(window.location.search).get("retorno")));
    } catch (error) {
      setMessage(error instanceof Problem ? error.message : "No se pudo conectar. Intente de nuevo.");
      if (error instanceof Problem && error.status === 429) { setRemaining(error.retryAfter); setWaitUntil(Date.now()+error.retryAfter*1000); }
    } finally { setPassword(""); setBusy(false); }
  }
  if (status === "loading") return <p role="status">Comprobando sesión…</p>;
  if (session) return <p>Sesión iniciada. <a href="/cuenta/">Ir a mi cuenta</a>.</p>;
  return <form onSubmit={submit}>
    <p><label>Correo<input type="email" name="email" autoComplete="username" maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} required /></label></p>
    <p><label>Contraseña<input type="password" name="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label></p>
    <button disabled={busy || remaining > 0}>{busy ? "Ingresando…" : "Ingresar"}</button>
    {remaining > 0 && <p role="status">Espere {remaining} segundos.</p>}
    {message && <p role="alert">{message}</p>}
  </form>;
}
