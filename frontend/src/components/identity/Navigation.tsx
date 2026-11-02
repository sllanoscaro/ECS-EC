/** Permission-aware navigation accepts links only from installed module composition. */
"use client";

import { useState } from "react";
import { useSession } from "./SessionProvider";

export type NavigationLink = { href: string; label: string; permission: string };

/** Show current allowed links; restricted sessions retain only account/logout actions. */
export function Navigation({ links = [] }: { links?: NavigationLink[] }) {
  const { status, session, logout } = useSession();
  const [error, setError] = useState("");
  async function leave() {
    /** Clear all tabs through the provider; never claim a failed server logout succeeded. */
    try { await logout(); window.location.assign("/ingreso/"); }
    catch { setError("No se pudo confirmar el cierre. Ingrese de nuevo para comprobarlo."); }
  }
  if (status === "loading") return <nav aria-label="Principal"><p role="status">Comprobando sesión…</p></nav>;
  if (!session) return <nav aria-label="Principal"><a href="/ingreso/">Ingresar</a></nav>;
  return <nav aria-label="Principal"><a href="/cuenta/">Mi cuenta</a>{!session.must_change_password && links.filter((link) => session.permissions.includes(link.permission)).map((link) => <span key={link.href}> · <a href={link.href}>{link.label}</a></span>)} · <button type="button" onClick={leave}>Salir</button><p>{error && <span role="alert">{error}</span>}</p></nav>;
}
