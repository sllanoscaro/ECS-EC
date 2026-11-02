/** Shared static document. Private module data must be obtained through the API. */
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = { title: "ECS-EC", description: "Monitoreo eléctrico del edificio" };

/** Render the Spanish document around a page; no runtime data or side effects. */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
