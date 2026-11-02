/** Static administrative shell; its guarded client loads current private data only at runtime. */
import { AccountAdministration } from "../../../components/identity/AccountAdministration";

/** Present account management without user data in the exported HTML. */
export default function AccountsPage() { return <main><h1>Usuarios</h1><AccountAdministration /></main>; }
