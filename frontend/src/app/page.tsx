/** Daily dashboard shell; current private values are fetched only after session authorization. */
import { Dashboard } from '../components/consumption/Dashboard';
/** Export a private-data-free page around the current consumption dashboard. */
export default function Home() {
  return <main><h1>Resumen del edificio</h1><Dashboard /></main>;
}
