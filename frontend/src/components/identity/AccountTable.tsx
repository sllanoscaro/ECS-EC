/** Approved administrative table; no password, hash, digest or deletion action is ever rendered. */
"use client";

import type { AccountView } from "../../lib/api/identity";

/** Show distinct loading/empty/error states and route actions through the parent's current revision. */
export function AccountTable({ items, busy, error, selfId, select }: { items: AccountView[]; busy: boolean; error: string; selfId: string; select: (account: AccountView, reset: boolean) => void }) {
  if (busy) return <p role="status">Cargando cuentas…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!items.length) return <p>No hay cuentas con estos filtros.</p>;
  return <table><caption>Cuentas registradas</caption><thead><tr><th>Correo</th><th>Perfil</th><th>Estado</th><th>Renovación pendiente</th><th>Acciones</th></tr></thead><tbody>{items.map((account) => <tr key={account.id}>
    <td>{account.email}</td><td>{account.role === "operador" ? "Operador" : "Administrador técnico"}</td><td>{account.status === "active" ? "Activo" : "Inactivo"}</td><td>{account.must_change_password ? "Sí" : "No"}</td>
    <td><button onClick={() => select(account, false)}>Editar</button>{account.id === selfId ? <a href="/cuenta/">Mi contraseña</a> : <button onClick={() => select(account, true)}>Restablecer contraseña</button>}</td>
  </tr>)}</tbody></table>;
}
