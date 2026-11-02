/** Public static own-account shell; the client guard controls runtime private rendering. */
import { PasswordForm } from "../../components/identity/PasswordForm";

/** Render renewal/self-password/logout without administrative role editing. */
export default function AccountPage() { return <main><h1>Mi cuenta</h1><PasswordForm /></main>; }
