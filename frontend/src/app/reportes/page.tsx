/** Static005 shell; future private requests use the current006 session at runtime. */
"use client";
import { SessionGuard } from "../../components/identity/SessionProvider";

/** Prepare the guarded route without advertising an unimplemented download operation. */
export default function ReportsPage() {
  return <main><h1>Reportes PDF</h1><SessionGuard permission="reports.generate">
    <p>La generación de reportes PDF todavía no está disponible.</p>
  </SessionGuard></main>;
}
