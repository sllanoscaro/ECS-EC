/** Static001 shell; every private value is loaded through the authenticated API. */
import { ConsumptionView } from "../../components/consumption/ConsumptionView";

/** Expose the seven-category consumption view without private data in the export. */
export default function ConsumptionPage() { return <main><h1>Consumo eléctrico</h1><ConsumptionView /></main>; }
