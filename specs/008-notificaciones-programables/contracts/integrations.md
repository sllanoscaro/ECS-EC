# Contratos internos y externos

Diseño de spec-008; todos los puertos de negocio se implementan dentro del monolito.
[openapi.json](openapi.json) define HTTP y [data-model.md](../data-model.md) la persistencia.

## Puertos funcionales

| Puerto | Entrada | Resultado/efectos |
| --- | --- | --- |
| `Identity.resolve_recipient` | Cuenta y permisos requeridos | Estado, correo vigente y elegibilidad, sin identidad técnica como cuenta funcional |
| `Consumption.latest_admissible_window` | Categoría, resolución, zona, activación y cursor válido | Última ventana completa disponible o estado no evaluable, con evidencia y revisión |
| `Consumption.source_status` | Categoría y corte | Fuente configurada, base CAT-01, última aceptación de datos nuevos; rechazos/duplicados no la avanzan |
| `FunctionalSummary.read` | Tipos, `[inicio,fin)`, corte y permisos | Resumen de recepción, calidad y cambios con cobertura, sin cuerpos de entrada ni señales técnicas |
| `FunctionalAudit.append` | Actor/proceso, acción, referencia, fecha, resultado | Registro transaccional y versionado de modificación, denegación o reenvío |
| `Clock` | Sin parámetros | Instante UTC y tiempo monotónico; inyectable solo en pruebas internas |

`latest_admissible_window` no recalcula CAT-01 con otra suma: consume el total medido o
calculado definido por specs-001/002. Para `intervalo`, la resolución se valida contra la
serie configurada. Hora/día/mes/año usan límites de la zona de regla y cobertura real.
No escalar una ventana parcial para estimar un total. Las categorías sin fuente son no
evaluables; la base calculada de CAT-01 no vacía cuenta como fuente lógica.

## Eventos durables de aplicación

Los productores escriben el evento en la misma transacción PostgreSQL que su resultado
funcional; no se publica por HTTP ni se crea un broker. Esquema de sobre:

| Campo | Contrato |
| --- | --- |
| `event_id` | UUID estable asignado por el productor confiable |
| `type` | `consumption.accepted`, `reception.completed`, `cost.failed`, `pdf.failed`, `administration.changed`, `source.changed`, `identity.changed` |
| `source_module`, `source_entity_id`, `source_revision` | Identidad de procedencia y deduplicación |
| `occurred_at`, `recorded_at` | UTC; diferenciar cambio/recepción del período medido |
| `category_id`, `measurement_window` | Opcionales según tipo, nunca inferidos de recorded_at |
| `accepted_new_data` | Booleano para reiniciar silencio solo con aceptación de novedades |
| `functional_result`, `safe_payload` | Campos aprobados por tipo; sin excepciones ni secretos |
| `correlation_ref` | Referencia opaca generada internamente para enlazar etapas |

Consumo aceptado dispara revisión de la ventana más reciente; recepción rechazada y
fallos de costo/PDF pueden disparar eventos puntuales; cambios administrativos alimentan
resumen autorizado. Identidad/fuente cambian elegibilidad/ausencias. Reprocesar identidad
ya conocida no produce otra ocurrencia. El resultado de correo no es un productor de
alertas por el propio correo: su fallo queda en historial, evitando recursión.

Eventos históricos no reabren ventanas cerradas antes de activación o ya superadas por
el cursor válido. Las correcciones de esas ventanas permanecen en historial/resumen.
Para ausencia, evaluar también por reloj desde última aceptación nueva o activación;
plazo explícito >=15 minutos, sin interpretar la separación mínima de recepción como SLA.

## Calendario

1. Vista previa recibe la misma programación que se guardará. Devuelve siguientes tres
   ocurrencias con zona, fecha nominal, fecha UTC resuelta, ventana y versión de tzdata.
   También devuelve un token opaco ligado a hash de configuración y versiones de permisos.
2. Intervalos usan `starts_at + n * duración` en UTC. La siguiente fecha es la primera
   estrictamente posterior a activación, respetando `starts_at`. No se recuperan fechas
   previas a activación como atrasos nuevos.
3. Calendario diaria/semanal/mensual/anual conserva intención local y ancla nominal.
   Hora repetida: primera (`fold=0`). Hora inexistente: primer instante válido posterior
   al hueco, no simplemente hora solicitada más duración del cambio. Día mensual/anual
   inexistente: último válido de ese mes, manteniendo ancla original para el mes siguiente.
4. Una sola clave lógica por slot. Registrar política y versión de tzdata con el resultado.
   Una actualización de tzdata recalcula únicamente futuros no materializados y exige
   nueva vista previa si cambió el resultado de una activación aún no confirmada.
5. Resumen diario 06:00 usa `[06:00 lógica anterior,06:00 actual)`, que puede durar 23/25 h.
   En la primera ocurrencia se calcula la anterior lógica sin enviar ese correo anterior;
   si `starts_at` impide una anterior, el primer límite es `starts_at` y se identifica la
   ventana inicial. Recepción/cambios se filtran por sus fechas de negocio, mediciones
   declaran sus propios períodos. El corte se conserva y no se desplaza durante reintentos.
6. Tras reinicio, materializar slots debidos en forma acotada y consolidar solo entregas
   nunca intentadas. No mezclar períodos ya intentados en la ventana de recuperación.

La vista previa no envía correo ni activa reglas. Activar revalida datos y token: un
preview vencido o configuración/permisos cambiados produce conflicto y pide recalcular.
Token expira a los cinco minutos o al pasar su primera ocurrencia, lo que suceda antes.

## Contrato SMTP

Entrada del adaptador: identidad de entrega/intento, un destinatario vigente, remitente
configurado, asunto y cuerpos texto/HTML escapados, `Message-ID` y ambiente de transporte.
Un solo destinatario en To/envelope; no CC/BCC de otras cuentas. Dominio de Message-ID
proviene del remitente autorizado, no de texto libre del usuario.

| Resultado | Evidencia mínima | Política |
| --- | --- | --- |
| `accepted` | Respuesta positiva final a DATA | Aceptada por servicio, sin prometer buzón/lectura |
| `not_accepted_transient` | Fallo antes de transferencia con certeza o rechazo temporal explícito | Reintentar en misma entrega, máximo tres |
| `not_accepted_permanent` | Rechazo definitivo o configuración/TLS/autenticación inválida | Fallida, sin reintento automático |
| `unknown` | Transferencia pudo aceptarse pero falta confirmación | Indeterminada, solo decisión manual |

Un timeout posterior a DATA sin respuesta es desconocido. Si DATA fue aceptado y solo
QUIT falla, conservar aceptación. Si el proceso muere antes de persistir confirmación,
solo evidencia inequívoca del relay permite resolver; de otro modo indeterminada.
No presumir que el relay permite consultar por Message-ID ni deduplica mensajes.

En producción exigir STARTTLS y certificado/hostname verificados, sin downgrade a texto
claro; secretos de credenciales fuera de Git. En local `local_prueba` usa Mailpit: éxito
significa aceptación del capturador, jamás entrega externa. Adaptador determinista de
pruebas conserva los mismos estados/permisos, sin exponer un endpoint de fallo público.

Cuatro plazas de envío iniciales, timeout por operación de socket de 10 s y presupuesto
de intento de 30 s como configuración inicial a validar. El adaptador actualiza el timeout
con el presupuesto restante antes de cada etapa. Una tarea de executor aún activa no
libera su plaza ni se duplica por timeout del llamador; sin resultado queda indeterminada.
La selección inicial alterna cuotas de tres urgentes y un periódico vencido cuando ambas
colas tienen trabajo; si una está vacía la otra ocupa todas las plazas. No reservar plazas
para envíos futuros ni reclamar más entregas que capacidad disponible.
Reintentos esperan 1 min tras final del primero y 5 min tras final del segundo. Fallos
SMTP no ocupan locks de mediciones, consultas, costos ni PDF.

## Recuperación e idempotencia

- Reclamar entregas únicamente después de reservar plaza. Transacción corta revalida
  versión/activación, cuenta, destinatario, correo y permisos; inicia intento e incrementa
  contador. Mutaciones de regla e identidad comparten orden de bloqueos regla -> cuenta -> entrega.
- Al iniciar, no liberar `en_intento` como pendiente sin evidencia de no aceptación. Nunca
  reutilizar un intento de un proceso anterior como si no hubiera comenzado.
- Recuperación periódica agrupa versión/cuenta, registra lote y miembros originales,
  cancela originales con razón de consolidación y crea una sola entrega. Incluye solo
  vencidas `attempt_count=0` todavía elegibles; conserva lista de ventanas y huecos.
- El reenvío exige estado fallido/indeterminado, administrador, motivo y reconocimiento
  de posible repetición; crea una entrega vinculada. La regla debe seguir vigente y
  el contenido seguir autorizado. Una regla pausada no habilita envío por reenvío manual.
- API mutante usa `Idempotency-Key`; misma clave/cuerpo devuelve recurso original, cambio
  de cuerpo devuelve 409. Ediciones/acciones sobre regla exigen `If-Match` con revisión
  actual. Un reintento HTTP no equivale a un nuevo reenvío autorizado. Tras autenticar y
  autorizar, resolver primero una clave idempotente ya confirmada y luego las precondiciones
  de una operación nueva; persistir la clave con el cambio, durante el plazo funcional.

## Señales y acceso técnico

Loguru usa JSON con `timestamp`, entorno, versión, operación/etapa, severidad, resultado,
`duration_seconds` y referencias opacas de correlación. `diagnose=False`; exclusión antes
de emitir. No registrar emails, nombres, valores de consumo/facturación, cuerpos SMTP,
archivos, cookies, credenciales ni variables locales de excepciones.

Observaciones terminales distinguen operaciones lógicas, evaluaciones e intentos:

| Evento | Hecho medido | Dimensiones permitidas |
| --- | --- | --- |
| `notification.operation.completed` | Una operación finalizada de API/evaluación/despacho | entorno, versión, función y resultado |
| `notification.delivery.attempt.completed` | Un intento SMTP, no una notificación única | entorno, transporte y resultado |
| `notification.scheduler.tick` | Salud/retardo del ciclo | entorno y función |
| `telemetry.heartbeat` | Secuencia y pérdidas acumuladas del productor | entorno e instancia acotada |

Loki/LogQL obtiene conteos por ventana, errores inesperados/operaciones finalizadas y
distribuciones de duración; rechazo previsto tiene resultado propio. Denominador cero
o cobertura desconocida => no calculable. Recibos de cola o eventos de reintento no
cuentan como operaciones originales adicionales. Para recepción, reutilizar unidades
operación/archivo/registro y conteos de aceptación de spec-007.

Un heartbeat cada 15 s con secuencia creciente, contador acumulado de descartes y último
éxito observable permite marcar huecos o interrupción; después de 45 s sin señal se
muestra cobertura desconocida, nunca cero. No usar `or vector(0)` para ocultar ausencia.
Loguru alimenta una cola propia acotada de 1024 eventos y máximo 16 KiB por evento ya
saneado. Productor usa inserción no bloqueante; al llenarse descarta señal e incrementa
contador local de pérdida, publicado en el siguiente heartbeat. El recolector persiste
checkpoints de secuencia/pérdida fuera del camino funcional; un reinicio con checkpoint
incompleto declara cobertura desconocida. No descarta datos de negocio.
La salida del recolector y logs Docker también tienen buffers y almacenamiento rotativo
acotados; una pérdida no reconstruible vuelve desconocida la ventana afectada.

No hay muestreo de logs de referencia. Traces OTel: 100 % en pruebas y inicialmente en
producción con exportador por lotes/cola limitada a 2048 spans y timeout de exportación
de 5 s; caída de Jaeger no bloquea negocio. Persistir contexto opaco confiable o usar
span links para trabajo diferido; cada intento tiene span propio. No instrumentar secretos.

Política técnica inicial: 7 días de logs/métricas derivadas Loki y 7 días de trazas
persistidas Jaeger; 24 h en perfiles desechables de prueba. Backend Jaeger de instancia
única con almacenamiento persistente compatible (Badger), volumen y limpieza con TTL
verificado. Versiones/configuración fijadas al implementar. Estas son decisiones operativas,
no el mínimo funcional de 12 meses. Las consultas muestran período conservado y pérdidas.

Grafana/Jaeger y sus fuentes quedan en red técnica privada. El acceso humano de diagnóstico
usa cuenta externa Programador de solo lectura, con autorización de entorno revisada en
cada consulta; identidades colectoras solo escriben. Revocar Programador impide la siguiente
consulta, sin depender de una sesión funcional. Operador y Administrador técnico carecen
de ese acceso. Ni puertos de Loki/Jaeger ni endpoint de ingesta se publican sin autenticación.
La puerta técnica usa Nginx con Basic Auth sobre TLS, archivo de Programadores por entorno
y comprobación en cada solicitud sin caché de autorización. Reemplazar el archivo al revocar
debe denegar la siguiente consulta, incluso con sesión de visor abierta. Grafana limita
acciones a Viewer; la puerta permite rutas de consulta (también POST de consulta del visor)
y deniega administración. Las ingestas usan rutas/redes separadas con credenciales técnicas
de escritura, nunca las de consulta humana. En local la puerta se publica solo en loopback
y conserva la autenticación. Estos controles no añaden lógica funcional independiente.
El procedimiento de acceso se documentará en `deploy/README.md`; no se implementa un visor
técnico en las páginas funcionales ni se añade contenido técnico a los correos.
