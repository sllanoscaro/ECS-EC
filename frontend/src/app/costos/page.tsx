/** Static004 shell; all financial values are loaded through authenticated runtime API requests. */
import { CostsView } from "../../components/costs/CostsView";

/** Mount the functional costs query without private data in the exported HTML. */
export default function CostsPage() { return <main><h1>Costos BT4.3</h1><CostsView /></main>; }
