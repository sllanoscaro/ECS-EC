/**005 static route; every request and download is authorized at runtime by006. */
'use client';
import {SessionGuard} from '../../components/identity/SessionProvider';
import {ReportForm} from '../../components/reports/ReportForm';
/** Mount calendar selection inside the existing authenticated application and visual system. */
export default function ReportsPage(){return <main><h1>Reportes PDF</h1><SessionGuard permission="reports.generate" returnTo="/reportes/"><ReportForm/></SessionGuard></main>;}
