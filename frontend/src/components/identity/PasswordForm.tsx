/** Self-only renewal/logout UI; every successful credential change requires a fresh login. */
"use client";

import { useState, type FormEvent } from "react";
import { sessionApi } from "../../lib/api/session";
import { SessionGuard, useSession } from "./SessionProvider";

/** Render exact-character password fields and clean every secret after success or failure. */
export function PasswordForm() {
  const { session, invalidate } = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    /** Validate confirmation locally, change only the own credential, then discard all contexts. */
    event.preventDefault(); if (busy) return; setMessage(""); setBusy(true);
    try {
      if (next !== confirm) throw new Error("La confirmación no coincide.");
      if ([...next].length < 15 || [...next].length > 128) throw new Error("Use entre 15 y 128 caracteres.");
      await sessionApi.changePassword(current, next);
      invalidate(); window.location.assign("/ingreso/");
    } catch (error) { setMessage(error instanceof Error ? error.message : "No se pudo cambiar la contraseña."); }
    finally { setCurrent(""); setNext(""); setConfirm(""); setBusy(false); }
  }
  return <SessionGuard>
    {session && <section className="panel account-summary"><h2>Datos de acceso</h2><div className="account-summary-grid"><div><strong>Correo electrónico</strong><p>{session.account.email}</p></div><div><strong>Perfil</strong><p>{session.account.role === "operador" ? "Operador" : "Administrador técnico"}</p></div></div></section>}
    {session?.must_change_password && <p className="notice notice--warning" role="status">Debe renovar su contraseña inicial antes de continuar.</p>}
    <section className="panel account-security"><h2>Cambiar contraseña</h2>
      <form className="account-form" onSubmit={submit} aria-busy={busy}>
        <label className="account-current">Contraseña actual<input type="password" placeholder="Ingresa tu contraseña actual" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} required /></label>
        <label>Nueva contraseña<input type="password" placeholder="Crea una nueva contraseña" autoComplete="new-password" aria-describedby="password-policy" value={next} onChange={(event) => setNext(event.target.value)} required /><span id="password-policy" className="account-help">Entre 15 y 128 caracteres. Se permiten espacios.</span></label>
        <label>Confirmar nueva contraseña<input type="password" placeholder="Repite la nueva contraseña" autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></label>
        <p className="account-consequence">Al cambiarla, se cerrarán tus sesiones y deberás ingresar de nuevo.</p>
        <button className="primary-button account-submit" disabled={busy}>{busy ? "Guardando…" : "Cambiar contraseña"}</button>
        {message && <p role="alert" className="notice notice--error account-error">{message}</p>}
      </form>
    </section>
  </SessionGuard>;
}
