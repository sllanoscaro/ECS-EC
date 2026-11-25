/**008 runtime authenticated history on a fully static Next export route. */
import {DeliveryList} from '../../components/notifications/DeliveryList';
/**No account, delivery capture or recipient data is evaluated during the static build. */
export default function NotificationsPage(){return <main className="notifications-page"><h1>Notificaciones</h1><p className="notification-intro">Contenido enviado, períodos y resultados de cada intento.</p><DeliveryList/></main>;}
