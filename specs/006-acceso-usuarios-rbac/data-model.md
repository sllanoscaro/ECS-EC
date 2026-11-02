# Data Model: Identidad, sesiones y administración

Diseño lógico para [spec.md](spec.md) y [plan.md](plan.md). Convenciones de UUID,
UTC/timestamptz y UoW según [arquitectura](../../docs/architecture.md). Estas tablas y su
migración pertenecen a 006; la auditoría/eventos siguen perteneciendo a 009.

## Cuenta y credencial personal (`identity_account`)

| Campo | Tipo/regla |
| --- | --- |
| `id` | UUID generado por la aplicación; identidad permanente. |
| `email` | Dirección normalizada para presentación administrativa. |
| `email_key` | Clave canónica no nula, UNIQUE entre todas las cuentas. |
| `role` | CHECK: `operador` o `administrador_tecnico`, exactamente uno. |
| `status` | CHECK: `active` o `inactive`. |
| `password_hash` | PHC Argon2id con salt/parámetros; nunca se serializa ni audita. |
| `must_change_password` | Booleano no nulo; true en alta y restablecimiento. |
| `auth_version` | BIGINT positivo, inicialmente 1; invalida sesiones previas. |
| `revision` | BIGINT positivo, inicialmente 1; concurrencia de la cuenta y procedencia de eventos. |
| `created_at`, `updated_at`, `password_changed_at` | UTC; último cambio efectivo de cuenta/credencial. |
| `created_by`, `updated_by` | Referencia confiable de cuenta o proceso bootstrap/recuperación. |

La credencial se conserva en la misma fila para que su cambio y la versión de acceso
sean atómicos. Consultas de repositorio tienen proyecciones explícitas: el hash nunca es
parte de `AccountView`, `SessionView`, listados, historial, eventos, logs o PDF.

Normalizar correo con la función de [research R2](research.md#r2-credenciales-y-correo).
Límite de entrada: 320 caracteres Unicode antes de validación; después rigen los límites
de sintaxis de `email-validator`. No truncar. Se permiten mayúsculas y espacios exteriores
sin alterar identidad. Un cambio únicamente de presentación que deja la dirección
normalizada igual es no-op. Contraseña: 15..128 puntos de código, espacios incluidos,
UTF-8 exacto, sin clases obligatorias; entradas fuera del rango se rechazan completas.

No hay tabla editable de roles/permisos ni endpoint para asignar permisos individuales.
La matriz fija vive en `identity/permissions.py`; un valor desconocido siempre deniega.
Índices: unicidad `email_key`, `(status,role,id)` para listado/conteo e `id` PK.

## Sesión (`identity_session`)

| Campo | Tipo/regla |
| --- | --- |
| `id` | UUID interno, distinto del secreto; no necesita publicarse. |
| `token_digest` | SHA-256 de 32 bytes aleatorios base64url; UNIQUE. No guardar bearer. |
| `account_id` | FK a cuenta, ON DELETE RESTRICT. |
| `auth_version` | Copia de la versión de cuenta al autenticar. |
| `mode` | `normal` o `password_change_required`; nunca lo determina el cliente. |
| `created_at`, `last_activity_at` | UTC; actividad inicialmente igual al ingreso. |
| `absolute_expires_at` | `created_at + 8 horas`, inmutable. |
| `idle_expires_at` | Inicialmente `created_at + 30 minutos`, nunca mayor al límite absoluto. |
| `revoked_at`, `revocation_code` | Nulos mientras no se revoque; código acotado, sin texto libre. |
| `csrf_key_id` | Versión de la clave externa para derivar CSRF; no es la clave. |

Índices: digest único; `(account_id,revoked_at)`; expiraciones para limpieza. Relación
cuenta 1:N sesiones; cerrar una no cierra las demás. No existe permiso durable en la
sesión: en cada petición se resuelve la cuenta actual.

Es válida si, al instante del servidor: no revocada, cuenta activa, perfil reconocido,
versiones iguales, `now < absolute_expires_at` y `now < idle_expires_at`. La igualdad con
un límite ya vence. Un login inicial/reset crea `password_change_required`; solo
introspección mínima, contraseña propia y cierre están disponibles. No permite consultas
del edificio ni administración, incluso si la cuenta tiene perfil administrativo.

La resolución y actualización condicional de actividad usan una UoW corta READ COMMITTED:
comprobar todos los predicados antes de tocar la sesión, nunca limpiar `revoked_at` ni
revivir una fila vencida. Actualizaciones concurrentes usan el máximo de actividad
confirmada; no reducen el último instante ni extienden el límite absoluto. Se usa reloj
confiable del servidor, no timestamps del navegador. El polling/introspección no cuenta
como actividad, según [HTTP](contracts/http.md#sesión-y-actividad).
Los clientes de consulta declaran interactive mediante `sessionActivityHeaders(activity)`
solo para acciones iniciadas por la persona; el helper usa background por defecto para
sondeos/revalidaciones. `/auth/session` nunca toca actividad, incluso con interactive.
Con ingreso al minuto0 y consulta interactiva válida al29, el límite inactivo pasa al59
sin superar el absoluto; solo sondeos no evitan vencer al30. Ninguna indicación del
cliente autoriza a revivir una sesión o prolongarla más allá de ocho horas.
Después de esperar locks se vuelve a obtener el instante actual antes de comprobar
vencimiento/actividad; no usar una hora capturada antes de la espera ni el timestamp
fijo del inicio de transacción para decidir vigencia después de quedar bloqueado.

## Presesión (`identity_preauth`)

`id` UUID, `token_digest` único, `created_at`, `expires_at=created_at+10min`,
`consumed_at|null`, `csrf_key_id`. Sin `account_id`, rol o permiso. Cookie separada
`ecs_ec_preauth`; token CSRF derivado con namespace propio. GET del contexto reutiliza
una presesión vigente sin prolongarla o crea una nueva si falta/venció. Login válido
consume la fila y crea sesión con un secreto independiente en la misma UoW. Dos logins
que reutilicen la presesión no pueden consumirla dos veces.

## Intentos (`identity_login_bucket`)

`bucket_key` PK: HMAC-SHA-256 con clave externa estable de la pareja correo canónico y
origen IP canónico, codificados con longitudes para evitar colisiones por concatenación.
No guardar contraseña, IP ni correo en esta tabla. No tiene FK de cuenta, para aplicar
la misma regla a desconocidas. `failed_at` es lista tipada de instantes UTC de los fallos
de la ventana móvil; máximo cinco. `blocked_until|null`, `updated_at`, `key_id`.

Eliminar de la lista los instantes `<=now-15min`. En el quinto fallo fijar
`blocked_until=now+15min`. Mientras `now<blocked_until`, no autenticar ni añadir fallos ni
extender ese plazo. Al alcanzarlo, limpiar espera/fallos y comenzar una ventana nueva.
Un éxito fuera de espera limpia ambos. Persistir el resultado de rechazo aunque no se
cree sesión. Actualización por fila bajo lock, creación concurrente por upsert y lock.

El hashing se ejecuta antes de locks sobre una captura de cuenta/hash/versión; la UoW
final bloquea bucket → presesión → cuenta (FOR SHARE si existe) → sesión nueva y revalida.
Tras adquirir locks obtiene de nuevo el reloj para espera, vigencia de presesión y
emisión, sin reutilizar el instante previo al hashing o a la espera de locks.
Un cambio de versión/hash/correo/estado durante Argon2 rechaza el resultado anterior con
mensaje general. Ninguna mutación de identidad adquiere buckets o presesiones, lo que
evita inversión con su protocolo de coordinación. Si ya hay espera se rechaza sin Argon2.

## Guardia de invariantes (`identity_guard`)

Una sola fila `id=1` creada por migración. Todas las altas y mutaciones de cuenta, incluida
contraseña propia, bootstrap y recuperación, adquieren FOR UPDATE antes de recursos de
participantes/cuentas. Nunca borrarla ni exponerla por API. Serializa mutaciones de
identidad, no lecturas, cálculo de hashes o SMTP.

Dentro de la sección bloqueada, contar cuentas `active/administrador_tecnico` y evaluar
el estado posterior. Rechazar degradación/desactivación que deje cero. Bootstrap admite
solo una base sin cuentas; crea administrador activo con renovación obligatoria. La
recuperación opera sobre administrador ya activo, nunca promueve ni crea cuentas.
El invariante se comprueba en el servicio para todas las vías, incluida CLI, y se prueba
con conexiones independientes PostgreSQL; un mutex del proceso no es suficiente.

## Revisión, transiciones y atomicidad

| Operación | Estado/efectos confirmados |
| --- | --- |
| Alta administrativa | Cuenta activa o inactiva, perfil válido, revisión/auth_version 1, renovación true; auditoría/eventos. |
| Bootstrap | Solo instalación vacía; administrador activo, renovación true, proceso confiable como actor. |
| Ingreso válido | Sesión normal o restringida según cuenta, presesión consumida, bucket limpio. No cambia revisión de cuenta. |
| PUT sin cambio efectivo | Con precondición vigente devuelve cuenta actual; no revisión, evento ni revocación nuevos. |
| Cambio correo/perfil/estado | revision y auth_version +1; revocar todas las sesiones; aplicar participantes y auditoría/eventos. |
| Reactivación | Mismas reglas de cambio; sesiones viejas siguen revocadas, exige login nuevo. |
| Reset por otro admin o recuperación | Hash nuevo, renovación true, revision/auth_version +1 y revocación total. |
| Contraseña propia | Verificar actual y nueva distinta; renovación false, revision/auth_version +1 y revocación total, incluida sesión actual. |
| Cierre | Revocar solo sesión utilizada; no cambia cuenta ni otras sesiones. |
| Vencimiento | Inelegible desde el instante límite, incluso sin job que marque la fila. |
| Rechazo/conflicto | Sin cambios de cuenta ni efectos parciales; auditoría de intento administrativo en UoW nueva. |

PUT/reset administrativos requieren revisión previa por ETag/If-Match. Alta no tiene
revisión anterior; cambio propio y recuperación usan la versión capturada internamente
antes de Argon2, revalidada bajo locks, sin exigir If-Match público a `/auth/password`.
Toda mutación usa autorización vigente del actor tras locks y
[coordinación](contracts/coordination.md). En HTTP se vuelve a comprobar también la
sesión original: no revocada, no vencida, modo admitido y versión vigente, usando un
instante nuevo después de los locks. La fila de esa sesión se bloquea después de cuentas,
junto con las sesiones afectadas por UUID; CLI usa actor de proceso confiable.
Los hashes se preparan sin mantener transacción abierta; la validación de contraseña
actual se revalida contra la misma versión al confirmar. Si no coincide, rechazar y no
cambiar la credencial.
Identidad puede coordinar otros dominios con cero participantes o participantes registrados;
no importa tablas ajenas ni hace commit separado dentro de un participante.

## Auditoría/eventos compartidos

No crear una tabla alternativa en identidad. Usar
[FunctionalAudit/EventWriter](../009-fundaciones-plataforma/contracts/integrations.md)
con `actor_kind=account|process|unauthenticated`, referencia confiable cuando exista,
acción, destino, resultado, instante UTC, revisión y correlación. `identity.changed`
se emite por cambio efectivo de cuenta, incluidos alta, credenciales y recuperación;
`administration.changed` adicional para altas/ediciones/reset administrativos y operación
de recuperación/bootstrap. Procedencia: módulo `identity`, UUID de cuenta y revisión.

Payload aprobado: cuenta UUID, revisión, nombres de campos cambiados, estado/perfil y
bandera de renovación cuando corresponda. Sin direcciones completas, hash, contraseña,
cookie, CSRF, IP o excepciones. Las denegaciones son auditoría, no eventos de cambio de
cuenta. Los módulos ajenos conservan su revisión/identidad de evento y producen su propio
cambio administrativo, sin duplicación desde el middleware de identidad.

La vista de historial devuelve eventos administrativos permitidos con actor estable,
fecha, acción, destino y resultado. Para actor sin sesión válida usa `unauthenticated`,
sin convertir un ID/correo del cuerpo en actor. Fallo de DB impide confirmar; responder
503 sin afirmar durabilidad de un cambio o intento no registrado.

## Conservación y secretos

Cuentas se desactivan y conservan permanentemente para referencias históricas; no hay
DELETE ni cascada. Auditoría/eventos y referencias protegidas conservan al menos 12 meses
calendario según 009, ampliables por dependientes; consultar no reinicia plazos.
Sesiones, presesiones e intentos son estado técnico de acceso, no historia funcional:
limpieza acotada de presesiones vencidas/consumidas y sesiones revocadas/vencidas tras
24 horas; buckets solo cuando no tengan espera activa ni fallos dentro de ventana y
hayan pasado 24 horas sin actualización. La validez nunca depende de la limpieza.

Claves HMAC de CSRF y buckets se provisionan externamente; no van en DB/lockfiles/git ni
export estático. Rotación de CSRF invalida contextos emitidos con la clave retirada y
exige nuevo ingreso; no reutilizar una clave aleatoria distinta en cada reinicio.
Rotación de buckets conserva la clave anterior de búsqueda al menos 30 minutos y migra
su estado bajo lock a la nueva, sin borrar una espera activa. Documentar el procedimiento
en operación. Backups contienen hashes y estado de acceso y usan la protección de 009.
