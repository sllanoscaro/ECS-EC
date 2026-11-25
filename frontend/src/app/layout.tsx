/** Shared static document. Private module data must be obtained through the API. */
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SessionProvider } from "../components/identity/SessionProvider";
import { ApplicationFrame } from "../components/identity/ApplicationFrame";
import "./globals.css";

export const metadata: Metadata = { title: "ECS-EC", description: "Monitoreo eléctrico del edificio" };

/** Render the Spanish document around a page; no runtime data or side effects. */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="es"><body><SessionProvider><ApplicationFrame links={[{ href: "/", label: "Dashboard", permission: "consumption.read" }, { href: "/consumption/", label: "Consumo", permission: "consumption.read" }, { href: "/costos/", label: "Costos", permission: "costs.read" }, { href: "/reportes/", label: "Reportes", permission: "reports.generate" }, { href:"/notificaciones/", label:"Notificaciones", permission:"notifications.deliveries.read" }, { href:"/notificaciones/reglas/", label:"Reglas de notificación", permission:"notifications.rules.manage" }, { href: "/administracion/costos/", label: "Configuración de costos", permission: "costs.configuration.manage" }, { href: "/administracion/consumo/", label: "Fuentes de consumo", permission: "consumption.configuration.manage" }, { href: "/administracion/usuarios/", label: "Usuarios", permission: "identity.accounts.read" }, { href: "/administracion/historial/", label: "Historial administrativo", permission: "administration.history.read" }]}>{children}</ApplicationFrame></SessionProvider></body></html>;
}
