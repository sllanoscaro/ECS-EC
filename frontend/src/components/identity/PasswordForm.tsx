/** Self-only renewal/logout UI; every successful credential change requires a fresh login. */
"use client";

import { useState, type FormEvent } from "react";
import { Problem, sessionApi } from "../../lib/api/session";
import { SessionGuard, useSession } from "./SessionProvider";

/** Render exact-character password fields and clean every secret after success or failure. */
export function PasswordForm() {
  const { session, invalidate, logout } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    /** Validate confirmation locally, change only the own credential, then discard all contexts. */
    event.preventDefault(); setMessage(""); setBusy(true);
    try {
      if (next !== confirm) throw new Error("La confirmación no coincide.");
      if ([...next].length < 15 || [...next].length > 128) throw new Error("Use entre 15 y 128 caracteres.");
      await sessionApi.changePassword(current, next);
      invalidate(); window.location.assign("/ingreso/");
    } catch (error) { setMessage(error instanceof Error ? error.message : "No se pudo cambiar la contraseña."); }
    finally { setCurrent(""); setNext(""); setConfirm(""); setBusy(false); }
  }
  async function leave() {
    /** Confirm durable logout; report uncertain failures while still clearing local private state. */
    try { await logout(); window.location.assign("/ingreso/"); }
    catch (error) { setMessage(error instanceof Problem ? error.message : "No se pudo confirmar el cierre."); }
  }
  return <SessionGuard>
    {session && <p>{session.account.email} · {session.account.role === "operador" ? "Operador" : "Administrador técnico"}</p>}
    {session?.must_change_password && <p role="status">Debe renovar su contraseña inicial antes de continuar.</p>}
    <form onSubmit={submit}>
      <p>La nueva contraseña debe tener entre 15 y 128 caracteres. Se permiten espacios.</p>
      <p><label>Contraseña actual<input type="password" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} required /></label></p>
      <p><label>Nueva contraseña<input type="password" autoComplete="new-password" value={next} onChange={(event) => setNext(event.target.value)} required /></label></p>
      <p><label>Confirmar nueva contraseña<input type="password" autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></label></p>
      <button disabled={busy}>{busy ? "Guardando…" : "Cambiar contraseña"}</button>
    </form>
    <p><button type="button" onClick={leave}>Cerrar sesión</button></p>
    {message && <p role="alert">{message}</p>}
  </SessionGuard>;
}
