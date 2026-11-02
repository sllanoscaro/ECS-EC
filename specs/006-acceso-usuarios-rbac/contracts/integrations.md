# Contratos internos de identidad y autorización

Propietario: spec-006. Complementa [HTTP](http.md), [coordinación](coordination.md) y
[modelo](../data-model.md). Puertos dentro del monolito, no servicios remotos.

## Puertos proporcionados

| Puerto | Entrada confiable | Resultado/efectos |
| --- | --- | --- |
| `Identity.resolve_session` | Cookie opaca y contexto de petición/actividad | Principal efímero actual o error; revisa DB, estado, versión, expiración y renovación. UoW breve propia, sin locks retenidos al consumidor. |
| `Identity.authorize(principal, action, building_id)` | Principal resuelto en esta petición, acción registrada y edificio del servidor | Permite o deniega por matriz fija. Si la operación abre otra fase durable, revalidar identidad actual allí; nunca aceptar roles enviados por usuario. |
| `Identity.require_report_access(principal, building_id)` | Igual que authorize | Alias que exige `reports.read` y sesión normal; POST de generación usa además `reports.generate`. No necesita permiso administrativo. |
| `Identity.resolve_recipient` | UUID de cuenta y conjunto tipado de permisos requeridos | Estado, correo vigente, perfil, auth_version y elegibilidad funcional; sin sesión humana requerida. Uso interno autorizado, nunca endpoint público. |
| `Identity.mutate_account` | Comando validado, actor de servidor, revisión esperada y UoW coordinada | Cambio/invalidation/auditoría/eventos atómicos; aplica guardia y participantes. |
| `Identity.register_participant` | Implementación del protocolo neutral | Registro en composición antes de servir tráfico; duplicados/rangos incompatibles impiden iniciar. Cero participantes es válido. |

Principal contiene UUID de cuenta, referencia interna de sesión, auth_version, perfil,
estado de renovación y contexto del edificio, nunca contraseña, hash o bearer. No se
serializa como credencial ni se mantiene entre requests. Un principal técnico de SFTP o
Programador no satisface los puertos humanos. El edificio se obtiene de configuración y
recursos confiables; un UUID ajeno o acción desconocida se deniega por defecto.

`resolve_recipient` consulta cuenta vigente, no cookies ni última sesión. Una cuenta
inactiva, perfil inválido, renovación pendiente o sin todos los permisos requeridos no
es elegible. Es una decisión de integración de 008: no añade permisos a la matriz humana.
El resultado incluye revisión/auth_version para revalidación y preview; dirección solo
en adaptadores internos autorizados, nunca en logs/resúmenes de otros destinatarios.
008 debe revalidarlo bajo sus locks inmediatamente antes del inicio durable.

## Matriz fija de acciones

Ambos perfiles normales incluyen las acciones de lectura; admin añade administración.
Sesión restringida solo admite las tres primeras acciones indicadas. El catálogo de
acciones se registra explícitamente; incorporar un módulo no permite acciones por prefijo
ni habilita permisos personalizados.

| Acción | Operador | Administrador | Uso |
| --- | --- | --- | --- |
| `session.read`, `session.logout`, `account.password.change` | Sí, también restringida | Sí, también restringida | Identidad mínima, cierre y contraseña propia. |
| `consumption.read` | Sí | Sí | Catálogo, detalle y agregados de 001/002. |
| `costs.read` | Sí | Sí | Ciclos, cálculos, boletas, comparación existente e historial; referencias de negocio incluidas. |
| `reports.read`, `reports.generate` | Sí | Sí | Estado, generación y descarga PDF de 005. |
| `identity.accounts.read`, `identity.accounts.manage` | No | Sí | Listado/detalle y alta/edición/reset de otras cuentas. |
| `administration.history.read` | No | Sí | Historial funcional administrativo común. |
| `consumption.configuration.read`, `consumption.configuration.manage` | No | Sí | Configuración de fuentes/correspondencias de 001. |
| `costs.configuration.read`, `costs.configuration.manage` | No | Sí | Suministro y perfiles/vigencias BT4.3 de 004. |
| `costs.bills.manage`, `costs.calculations.create`, `costs.comparisons.create` | No | Sí | Registro/corrección documental, recálculo y comparación persistidos. |

La política se prueba por acción y por ruta, no por método HTTP. Las acciones de
notificaciones se incorporan explícitamente conforme a su contrato al registrar 008:
entregas propias y contenido aún autorizado para Operador; reglas, catálogo/destinatarios,
preview/activación/pausa/reenvío e historial completo para admin. No existe un permiso
genérico que permita leer objetos de otro destinatario. El entorno técnico de 007
mantiene autenticación externa propia, sin otorgar estas acciones a Programador.

## Mapa a interfaces propietarias

| Propietario y contrato | Consultas humanas permitidas | Administración/integración |
| --- | --- | --- |
| [001 HTTP](../../001-visualizar-consumo-categorias/contracts/http.md) | GET `/consumption/catalog` y `/consumption/categories/{category_id}/detail`: consumption.read. | GET/PUT `/consumption/configuration`: acciones configuration. Formulario `/administration/consumption/` sigue siendo de 001. |
| [002 HTTP](../../002-registro-retencion-consumo/contracts/http.md) | GET `/consumption/categories/{category_id}/aggregates`: consumption.read. | No inventar endpoint público de ingesta, purga o retención; sus operaciones internas siguen usando identidad de proceso y validaciones de 002. |
| [003 SFTP](../../003-simulador-pas600-sftp/contracts/sftp-reception.md) | Ninguna autorización SFTP derivada del perfil humano. | Publicación automatizada usa identidad técnica y contrato propio, sin sesión web. Parámetros existentes solo se administran donde su propietario los exponga. |
| [004 HTTP](../../004-costos-tarifa-bt43/contracts/http.md) | GET ciclos, cálculos, boletas, comparaciones e historial: costs.read. | GET perfiles/suministro y POST/PUT de configuración: costs.configuration; POST/PUT boletas: bills.manage; POST cálculos/comparaciones: create correspondiente. |
| [005 HTTP](../../005-generar-reportes-pdf/contracts/http.md) | POST `/reports`: reports.generate; GET estado/descarga: reports.read. | Autorizar antes de replay idempotente y de cada descarga. No servir BYTEA como archivo público estático. |
| [008 HTTP](../../008-notificaciones-programables/contracts/openapi.json) | Entregas propias y contenidos aún permitidos, cuando exista el módulo. | 008 implementa permisos de objetos, su participante y pruebas reales antes de despachar; no es prerrequisito de 006. |
| [007 spec](../../007-observabilidad-externa/spec.md) | Ningún acceso a visores por perfil humano. | Programador autenticado en entorno técnico; credenciales no se convierten en cookie funcional. |

FR-019 administra las configuraciones editables de fuentes/correspondencias de 001 y
suministro/perfiles BT4.3 de 004 mediante sus interfaces reales. La separación mínima de
recepción de 15 minutos y la conservación mínima de 12 meses son restricciones obligatorias
de 002, sin edición web en 006. Sus validaciones se comprueban por separado mediante los
puertos/validadores reales del propietario, sin crear endpoints de parámetros o retirada.
El caso administrativo inválido US4.4 usa una fuente asignada a dos categorías en 001;
debe rechazar la solicitud sin cambiar la configuración anterior. El Administrador no
puede saltar las restricciones de 002, editar mediciones arbitrariamente ni ejecutar el
simulador remoto.

## Integración del cliente y actividad

`frontend/src/lib/api/session.ts` proporciona `sessionActivityHeaders(activity)` con
valores `interactive|background` y valor predeterminado `background`. Los clientes de
consulta de consumo, costos y reportes reutilizan ese helper al incorporarse: navegación,
Consultar, Actualizar y cambios de filtros iniciados por la persona declaran `interactive`;
sondeos y revalidaciones automáticas declaran `background`. Su conexión a proveedores
reales pertenece a la integración de US2, sin condicionar el acceso local de US1.

La cabecera nunca es autorización ni permite revivir o superar la duración absoluta de
una sesión. `/auth/session` permanece sin actualización de actividad, incluso si recibe
`interactive`; las revalidaciones del proveedor de sesión no cuentan como navegación de
datos iniciada por la persona. [HTTP](http.md#sesión-y-actividad) fija los límites y
[quickstart](../quickstart.md) los casos de validación temporal.

## Consumo de capacidades comunes

- `core` de [009](../../009-fundaciones-plataforma/plan.md): configuración validada, reloj
  UTC inyectable, DB/UoW, errores saneados y composición. No copiar sus implementaciones.
- [FunctionalAudit/EventWriter](../../009-fundaciones-plataforma/contracts/integrations.md):
  cambio de cuenta, invalidación y participantes comparten UoW; eventos tipados por UUID/
  revisión. Las denegaciones posteriores a rollback usan UoW nueva. El historial de 006
  consulta la evidencia común con filtros/proyección permitidos, no crea otro almacén.
- Identidad aporta catálogo de acciones administrativas y resultados; cada módulo
  registra sus cambios, versiones y `administration.changed` una sola vez en su UoW.
  La dependencia común de seguridad registra solicitudes administrativas denegadas antes
  de entrar al módulo. Una referencia de operación evita duplicar el intento entre capas.
- El emisor de [007](../../007-observabilidad-externa/research.md), cuando esté disponible,
  recibe operación/etapa/resultado/código y correlación saneada de ingreso, autorización,
  mutación y recuperación. No enviar contraseña, correo, cookies, tokens, IP o payloads.
  Su caída/cola llena no cambia permisos ni commits de identidad; no usar logs como
  sustituto de historial funcional. No implementar ese emisor dentro de 006.

## Límites de frescura y de transacción

La admisión de una petición protegida usa lectura actual READ COMMITTED de sesión/cuenta.
La UoW de esa comprobación termina antes de adquirir recursos de negocio: no bloquear
cuenta antes de las reglas de 008. Las operaciones de identidad vuelven a autorizar al
actor y su sesión original tras adquirir sus locks ordenados, con reloj actualizado;
la sesión puede haber sido cerrada sin que cambiara auth_version. Las operaciones de otros dominios con fases
durables revalidan allí según su contrato, sin reutilizar una captura antigua para permisos.

Una solicitud ya autorizada antes de un cambio puede terminar; la siguiente admisión
iniciada después del commit de invalidación se rechaza. Descarga de PDF es una nueva
petición autorizada, incluso si el resultado se generó antes. Un PDF ya descargado conserva
el comportamiento sin conexión de 005. La captura energética/financiera REPEATABLE READ
de reports no sustituye la consulta vigente de identidad previa a capturar o descargar.

## Preparación inicial y recuperación operativa

CLI prevista: `uv run ecs-ec identity bootstrap-admin --email <correo>`; contraseña leída
dos veces con getpass desde TTY. Solo funciona si no hay cuentas; dos ejecuciones
concurrentes se serializan y solo una crea. Exige configuración/DB válidas, perfil
administrativo activo fijo y renovación. No imprime credenciales ni acepta contraseña
como argumento. Si la instalación ya tiene cuentas, rechaza sin cambios.

`uv run ecs-ec identity recover-admin --email <correo> --reason <motivo>` requiere acceso
operativo al host/contenedor y restablece solo una cuenta administrativa actualmente
activa. Motivo obligatorio, saneado y acotado a 500 caracteres; contraseña por TTY. No
crea/promueve/reactiva cuentas. Incrementa revisión/auth_version, revoca sesiones,
exige renovación y deja actor de proceso y auditoría. No hay endpoint remoto equivalente.
La autorización de acceso al host y respaldo previo forman parte de operación de 009;
este contrato define la herramienta de identidad y sus efectos.
