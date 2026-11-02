/** Static004 administrative shell, sharing006 session/navigation and the same application. */
import { CostsView } from "../../../components/costs/CostsView";

/** Present explicit administrative operations only after the current session guard approves access. */
export default function CostsAdministrationPage() { return <main><h1>Administración de costos</h1><CostsView administrative /></main>; }
