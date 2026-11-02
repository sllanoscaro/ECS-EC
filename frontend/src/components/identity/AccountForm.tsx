/** Account create/edit/reset form with local confirmation and unconditional credential cleanup. */
"use client";

import { useState, type FormEvent } from "react";
import { type AccountDraft, type AccountMode, type AccountView } from "../../lib/api/identity";
import { Problem, type Role } from "../../lib/api/session";

/** Render only allowed account attributes; self password reset is provided by the personal page. */
export function AccountForm({ account, mode = "create", save }: { account?: AccountView; mode?: AccountMode; save: (draft: AccountDraft) => Promise<void> }) {
  const [email, setEmail] = useState(account?.email ?? "");
  const [role, setRole] = useState<Role>(account?.role ?? "operador");
  const [status, setStatus] = useState<"active" | "inactive">(account?.status ?? "active");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    /** Keep editable non-secret fields on conflicts, while clearing every credential after any result. */
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      if (mode !== "edit") {
        if (password !== confirm) throw new Error("La confirmación no coincide.");
        if ([...password].length < 15 || [...password].length > 128) throw new Error("Use entre 15 y 128 caracteres.");
      }
      const draft: AccountDraft = { email, role, status };
      if (mode === "create") draft.initial_password = password;
      if (mode === "reset") draft.new_password = password;
      await save(draft);
      setMessage("Cambio confirmado.");
    } catch (error) {
      setMessage(error instanceof Problem || error instanceof Error ? error.message : "No se pudo confirmar el cambio. Recargue antes de repetirlo.");
    } finally { setPassword(""); setConfirm(""); setBusy(false); }
  }

  return <form onSubmit={submit}>
    <h2>{mode === "create" ? "Nueva cuenta" : mode === "edit" ? "Editar cuenta" : "Restablecer contraseña"}</h2>
    {mode !== "reset" && <><p><label>Correo<input type="email" value={email} maxLength={320} autoComplete="off" onChange={(event) => setEmail(event.target.value)} required /></label></p>
      <p><label>Perfil<select value={role} onChange={(event) => setRole(event.target.value as Role)}><option value="operador">Operador</option><option value="administrador_tecnico">Administrador técnico</option></select></label></p>
      <p><label>Estado<select value={status} onChange={(event) => setStatus(event.target.value as "active" | "inactive")}><option value="active">Activo</option><option value="inactive">Inactivo</option></select></label></p></>}
    {account && <p>Revisión {account.revision}. Los cambios efectivos invalidan todas las sesiones de esta cuenta.</p>}
    {mode !== "edit" && <><p>La contraseña inicial debe tener entre 15 y 128 caracteres, incluidos espacios. El titular deberá renovarla.</p>
      <p><label>Contraseña inicial<input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label></p>
      <p><label>Confirmar contraseña<input type="password" autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></label></p></>}
    <button disabled={busy}>{busy ? "Guardando…" : mode === "create" ? "Crear cuenta" : mode === "edit" ? "Guardar cambios" : "Restablecer contraseña"}</button>
    {message && <p role="status">{message}</p>}
  </form>;
}
