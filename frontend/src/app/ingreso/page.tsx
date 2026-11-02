/** Public static login shell; all session data is obtained only after browser hydration. */
import { LoginForm } from "../../components/identity/LoginForm";

/** Render accessible login without an embedded account or credential. */
export default function LoginPage() { return <main><h1>Ingresar</h1><LoginForm /></main>; }
