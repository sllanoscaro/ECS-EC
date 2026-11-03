/** Public static own-account shell; the client guard controls runtime private rendering. */
import { PasswordForm } from "../../components/identity/PasswordForm";

/** Render renewal/self-password/logout without administrative role editing. */
export default function AccountPage() { return <main><p className="account-breadcrumb">ECS-EC / Mi cuenta</p><h1>Mi cuenta</h1><p className="account-description">Revisa tu acceso y actualiza tu contraseña.</p><PasswordForm /></main>; }
