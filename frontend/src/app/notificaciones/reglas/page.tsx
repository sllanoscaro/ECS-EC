/**008 static administrative shell; configuration/accounts are loaded at runtime through the authenticated API. */
import {RuleList} from '../../../components/notifications/RuleList';

/**Open the installed rule workspace without private build-time data or dynamic UUID routes. */
export default function NotificationRulesPage(){return <main className="notifications-page"><h1>Reglas de notificación</h1><p className="notification-intro">Correo periódico y alertas del edificio, con fechas y destinatarios explícitos.</p><RuleList/></main>;}
