/** Public static login shell; all session data is obtained only after browser hydration. */
import { LoginForm } from "../../components/identity/LoginForm";

/** Center the approved public form; session state never adds private navigation to this route. */
export default function LoginPage() {
  return <main id="login-content" className="login-main" tabIndex={-1}>
    <section className="login-panel" aria-labelledby="login-title">
      <img className="login-logo" src="/brand/electro-conforma.svg" alt="Electro Conforma" width={516} height={190} />
      <header className="login-heading"><p className="login-system">ECS-EC</p><h1 id="login-title">Ingresar</h1><p className="login-description">Accede al monitoreo eléctrico del edificio.</p></header>
      <LoginForm />
      <p className="login-help">Para restablecer tu contraseña, contacta al administrador técnico.</p>
    </section>
  </main>;
}
