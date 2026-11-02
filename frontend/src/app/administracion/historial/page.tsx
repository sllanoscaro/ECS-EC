/** Static administrative history shell; all functional evidence is obtained through the protected API. */
import { AdministrationHistory } from "../../../components/identity/AdministrationHistory";

/** Present the read-only shared history without exporting any actor or private record. */
export default function HistoryPage() { return <main><h1>Historial administrativo</h1><AdministrationHistory /></main>; }
