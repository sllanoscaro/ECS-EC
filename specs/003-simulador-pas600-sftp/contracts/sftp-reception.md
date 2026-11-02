# Contrato SFTP y adaptación a consumo

[Perfil](pas600-profile.md), [modelo](../data-model.md), [CLI](cli.md).
Interfaces de 003, sin endpoint HTTP de inyección ni confirmación nueva del backend.
El simulador es cliente externo; el receptor/adaptador se ejecuta dentro del monolito.

## Identidad y configuración

El listener SFTP del `lifespan` 009 usa puerto configurable (local 2222), host key persistida
y configuración privada de bindings. Solo subsistema SFTP: sin shell, comandos SSH,
forwarding ni acceso fuera de la raíz virtual del binding. Autenticación por contraseña
(verificador protegido) o clave pública autorizada; secretos externos a manifiestos e informes.
La identidad técnica de integración está limitada a edificio/publicador/directorio,
no obtiene roles humanos de 006 ni derechos técnicos de 007. El contenido no autoriza
un proceso: verificar publicador y correspondencias contra el binding confiable.

Cliente exige `known_hosts` o pin de clave previamente verificado. Host desconocido o
cambiado detiene prueba/envío; no hay aceptación automática, ni `known_hosts=None`.
El procedimiento local obtiene la pública del receptor desde su archivo montado por la
persona administradora, no confía en una clave obtenida de la red sin comparación.
Configuración inicial admite ECDH P-256 y AES-CTR del apéndice E con MAC compatible;
no habilitar algoritmos heredados débiles para aparentar fidelidad. Algoritmos exactos
se verifican con la biblioteca/entorno al implementar y con equipo antes del despliegue físico.

## `sftp-session-batch-v1`

1. Antes de conectar, congelar lista completa de archivos, nombres, tamaños y SHA-256.
   Una sesión SFTP corresponde exclusivamente a una publicación/ciclo.
2. Abrir cada nombre nativo como archivo nuevo de la sesión, escribir secuencialmente y
   esperar `SSH_FXP_STATUS OK` a su CLOSE explícito. El receptor guarda en staging privado,
   verifica que se escribió un prefijo contiguo desde offset cero sin huecos y hace fsync.
   No sobreescribir archivos de otra sesión ni permitir symlinks/traversal.
3. Al terminar **todos** los CLOSE confirmados y sin operaciones pendientes, el cliente
   emite SSH CHANNEL_EOF del subsistema y espera su cierre. El receptor sella solo por
   ese evento limpio, con cero handles abiertos y cero errores. Crea manifiesto durable
   y encola el lote. El `exit` genérico de la biblioteca no es prueba suficiente.
4. Si falla cualquier apertura/escritura/cierre, abortar canal/conexión sin EOF normal;
   todos los archivos quedan no sellados. Un `finally` o context manager no puede emitir
   un EOF limpio que convierta un prefijo en lote completo. Probar esa ruta explícitamente.
5. Una caída o reinicio nunca promueve sesiones `receiving` por mtime/tamaño ni por el
   parser; pasan a `aborted`, conservando evidencia/bytes. Solo publicaciones selladas
   son procesables. Reintentar siempre la lista completa, incluso archivos transferidos.

El servidor no recibe el informe de control ni un manifest del simulador. Su manifiesto
se construye internamente de las operaciones SFTP y nombres/contenidos nativos. La
completitud del conjunto depende del cliente que cumple la convención. Los índices
se validan contra huecos observables, pero no revelan cuántos archivos aún no llegaron.
No es una conducta de firmware demostrada por DOCA0172EN-19. Conectar hardware requiere
captura que pruebe esta frontera; si reutiliza sesiones, desconecta sin EOF o interrumpe
publicaciones de otro modo, debe acordarse otra frontera verificable antes de habilitarlo.
El contrato local solicitado queda definido sin modificar el formato del fabricante.

Una prueba de conexión autentica y comprueba permisos escribiendo/eliminando un probe
reservado fuera del espacio de archivos PAS600; no contiene mediciones ni entra al parser.
Una sesión vacía no crea actualización; categorías sin medidor no generan archivos vacíos.

## Cadencia, reintentos y parada del cliente

Separación inicial `publication_gap_seconds=900`, nunca menor; distinta de muestreo.
Candado por destino/publicador, un solo envío activo y espera desde el fin real del
intento anterior hasta el inicio del siguiente. Se cuenta el intento completo de todos
los archivos, también cuando falla. Por simplicidad se separan todos los ciclos del
publicador, lo que garantiza la restricción por categoría. Reanudación espera nuevamente
el intervalo completo con reloj monotónico; no usa adelantos de UTC para acortarlo.

Tres intentos totales por publicación por defecto, configurable con entero >=1.
Timeout/desconexión/indisponibilidad: reintento limitado, mismos bytes/nombres/semántica.
Autenticación, host key, permisos, configuración o cuota: detener hasta corrección;
no consumir un ciclo infinito de conexiones. Tras agotar intentos conservar archivos,
informe y estado `failed`, permitiendo reenvío explícito con un presupuesto nuevo registrado
sin borrar historial ni evitar la cadencia. `SIGINT`/`SIGTERM` impiden nuevos ciclos;
finalizar el actual bajo timeout o abortarlo sin EOF limpio y registrar el resultado.

`file_status: generated|pending|transferred|failed`; `transferred` solo con CLOSE OK.
Un intento conserva además `session_end: clean|aborted|unknown` y estado de publicación
`pending|transferred|failed|uncertain`. CLOSE puede llegar antes de perderse EOF: un archivo
transferido no garantiza publicación sellada. Ni siquiera `transferred/clean` implica
mediciones aceptadas. No inventar un ACK funcional desde SFTP.

## `Acquisition.process_sealed` — puerto interno 003

Entrada: ID de publicación sellada, binding/revisión, proceso autorizado, UoW/reloj 009.
Salida: evaluación durable con resultados por archivo/posición y referencia a recepción 002.

1. Reclamar trabajo durable con exclusión PostgreSQL; cargar bytes inmutables y validar
   perfil/origen/nombres. Orden estable: grupo nativo, índice, serie/tópico y posición.
2. Parsear archivos independientemente. Estructura ilegible = `file_unreadable`; conservar
   tamaño/hash/causa y continuar archivos independientes. Registro inválido = diagnóstico
   por posición. CSV Error 19/NaN y JSON inválidos no se convierten en cero.
3. Resolver correspondencias con 001 sin modificar su catálogo; fuente desconocida,
   categoría sin medidor o descriptor incompatible producen causas saneadas. El descriptor
   no otorga permiso ni cambia configuración histórica del edificio.
4. Conservar lecturas y formar los candidatos descritos en el [modelo](../data-model.md).
   Registrar candidatos/evaluación pendientes antes de llamar 002, sin mantener locks 003
   durante la llamada. Los intervalos se entregan con sus dos extremos nativos cuando
   son deltas; referencia inicial/gap no se disfraza de medición con valor null.
5. Llamar una vez por evaluación lógica a `Reception.accept` de 002 con todos los
   candidatos y registros inválidos clasificables, nunca una vez por fragmento. Registros
   inválidos que ya puede representar su contrato se entregan sin limpiarlos para que
   001 produzca su rechazo; defectos no representables quedan en resultados 003 enlazados.
   No incorporar nada localmente como sustituto de 002.
6. Guardar referencias a resultados ya confirmados 002; reconstruir resumen tras caída.
   Con cero candidatos y solo referencia/archivos ilegibles hay evidencia 003 sin
   actualización de consumo ni evento `consumption.accepted` ficticio.

### Entrada coordinada con `Reception.accept` (002)

| Campo | Contrato |
| --- | --- |
| `building_id`, proceso autorizado | Del binding confiable; no del cuerpo remoto. |
| `publication_ref` | Estable para igual binding/revisión semántica/perfil/publicador/ciclo y conjunto exacto ordenado de nombres/tamaños/hashes. |
| `attempt_id` | UUID interno generado por003 y persistido en `PublicationEvaluation` antes de llamar002; el mismo al recuperar una llamada, nuevo al reenviar explícitamente. |
| `input_position` | Posición estable y única dentro del conjunto lógico, con archivo/serie/fila como evidencia. |
| origen, categoría, inicio/fin, valor/unidad | Correspondencias y deltas exactos; 001/002 revalida segmentos históricos, dominio y cadencia. |
| `source_evidence_ref` | Referencia durable a archivo(s), posición(es), lecturas y algoritmo de delta. |
| correlación | Interna generada por servidor; nunca confiada por un campo libre del archivo. |

El [contrato propietario002](../../002-registro-retencion-consumo/contracts/integrations.md)
define `Reception.accept(attempt_id, building_id, publication_ref, process, records,
correlation_ref)` y `Reception.read_attempt(attempt_id, building_id, process)` en
`backend/src/ecs_ec/consumption/ports.py`. Su implementación sigue siendo de002.
003 congela y persiste ID, correlación y entrada canónica ordenada de la evaluación antes
de llamar; la recuperación no reconstruye esa entrada con nuevas lecturas/candidatos.
Tras perder respuesta, consultar `read_attempt`: `not_found` confirmado permite repetir
`accept` con el mismo ID; `processing`/`partial_failure` permiten continuar con ese ID
y entrada, y `completed` conserva los resultados originales. La lectura no reanuda
trabajo. Fallo de DB/autorización es error, nunca `not_found`.
La exclusión del intento en002 evita dos recuperaciones simultáneas; lo ya confirmado
no se reclasifica como duplicado ni se vuelve a evaluar. Igual ID con entrada distinta
produce `attempt_payload_conflict`, sin mutar resultados ni reloj. Un `too_early`
confirmado requiere reenvío explícito con nuevo `attempt_id`, aun con publicación estable.
002 devuelve `accepted|duplicate|rejected`, causa y próxima admisible, con transacciones
por categoría. Archivo ilegible, inválida nativa y rechazo 001/002 se muestran separados.
No avanzar reloj 002 con datos simulados ni usar su rechazo como aceptación diferida.

## Evidencia y exportación técnica

`Acquisition.export_results` se invoca desde comando de mantenimiento local, con identidad
de proceso autorizada por el despliegue y alcance de edificio; no permiso derivado de
Programador ni sesión humana nueva. La selección explícita de categorías/período/zona/vista
no contiene el oráculo ni etiquetas de anomalía. El edificio se resuelve desde la publicación
y se valida el alcance autorizado antes de leer. Exporta JSON versionado con:
`schema_version`, `publication_ref`, manifiesto, fechas, estado de sellado,
archivos/parseo, posiciones nativas, lecturas/pares, adaptación, IDs de intento/resultado 002,
`accepted|duplicate|rejected`, causas y próxima admisible. Incluye el historial de
evaluaciones e intentos de esa publicación visible al corte, con sus IDs y estados,
sin escoger silenciosamente el último resultado tras un reenvío. Decimales como cadenas en la
exportación de evidencia; esto no modifica los tokens numéricos del archivo PAS600.
Los valores saneados bastan para contrastar, sin contraseñas/claves ni excepciones crudas.

### Snapshot de consumo para contraste

| Campo | Contrato |
| --- | --- |
| `snapshot_id`, `cutoff_at` | UUID interno y corte UTC009 de la captura coherente, no tiempo simulado ni corte arbitrario del cliente. |
| `selection` | `{building_id, category_ids, period:{start,end,timezone}, view}`; categorías únicas CAT-01..07 y view `detail\|hour\|day\|month\|year`. |
| `consumption_snapshot.status` | `available\|unavailable`; available significa lectura efectuada, incluso con resultado sin datos o cobertura incompleta. |
| `consumption_snapshot.reason_code` | Null si available; causa saneada obligatoria si unavailable. |
| `consumption_snapshot.detail_results` | Lista con un resultado001 por categoría para view detail; vacía para las otras vistas o si unavailable. |
| `consumption_snapshot.aggregate_results` | Lista con un resultado002 por categoría para view hour/day/month/year; vacía para detail o si unavailable. |

Reutilizar sin redefinir fórmulas/estados los contratos de
[detalle001](../../001-visualizar-consumo-categorias/contracts/http.md) y
[agregados002](../../002-registro-retencion-consumo/contracts/http.md), incluidos
selección, energía, duraciones/cobertura, procedencia, revisiones y diagnósticos.
El proveedor recibe la UoW de lectura REPEATABLE READ y el corte del exportador:
evidencia de recepción y resultados de todas las categorías comparten esa captura.
Un `cutoff_at` coincidente sin compartir captura no acredita coherencia. Liberar la UoW
antes de escribir el archivo. El snapshot es una proyección exportada, no otra tabla de
consumo ni una promesa de reconstrucción histórica desde una fecha.

Validar inicio<fin, offsets/zona del edificio y categorías/vista antes de consultar;
no ampliar ni redondear el período solicitado. Vista agrupada conserva bloques excluidos
y sus razones conforme a002; no afirmar evaluado un intervalo fuera de su alcance.
Una limitación del proveedor que permita conservar la captura produce unavailable con
causa, nunca cobertura cero inventada. Si la DB falla y se pierde la captura, el comando
falla explícitamente sin fabricar un corte coherente ni reemplazar una exportación válida.
En detail, la evidencia retirada o insuficiente se mantiene identificada: no se usa
su ausencia para afirmar una omisión de adquisición.

El evaluador enlaza archivo/hash/posición y pares del reporte local con esta exportación
y con el snapshot de consumo incluido; el contraste manual también puede consultar
las vistas001/002, identificando su corte si difiere. Una omisión no tiene fila recibida: se
comprueba por el intervalo esperado y su ausencia/cobertura. Si la fuente no entrega
resultados o la DB falla, estado desconocido, sin afirmar rechazo o aceptación.
No se carga el oráculo del simulador en el proceso receptor.

Auditoría 003 usa `FunctionalAudit` 009 junto a estados/resultados propios, sin añadir
tipos de `FunctionalEvent` no registrados. `reception.completed` y `consumption.accepted`
son producidos por 002. Señales de archivos/fallos/esperas/recuperación usan emisor 007
cuando exista, sin depender de sus visores ni de 008/SMTP.
