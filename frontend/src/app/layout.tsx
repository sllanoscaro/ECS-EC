/** Shared static document. Private module data must be obtained through the API. */
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SessionProvider } from "../components/identity/SessionProvider";
import { Navigation } from "../components/identity/Navigation";
import "./globals.css";

export const metadata: Metadata = { title: "ECS-EC", description: "Monitoreo eléctrico del edificio" };

/** Render the Spanish document around a page; no runtime data or side effects. */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="es"><body><SessionProvider><Navigation links={[{ href: "/administracion/usuarios/", label: "Usuarios", permission: "identity.accounts.read" }, { href: "/administracion/historial/", label: "Historial", permission: "administration.history.read" }]} />{children}</SessionProvider></body></html>;
}
