# Modelo técnico de observabilidad

[Plan](plan.md), [catálogo](contracts/signals.md), [integración](contracts/integrations.md)
y [acceso/políticas](contracts/technical-access.md). Entidades de telemetría, no tablas
de negocio. Sin migración SQL ni copia de `FunctionalEvent`/`FunctionalAudit`.

## Identidad Programador

Registro externo por entorno: `technical_subject` opaco, verificador de contraseña,
`environment`, estado habilitado y revisión operativa del archivo autorizado. Relación
persona ↔ sujeto fuera de telemetría, con acceso de operación restringido. Habilitación
en varios entornos mediante provisiones independientes. Sin FK a cuentas006, sesión
web, perfil funcional o permiso de administración técnica.

Transiciones: ausente → habilitado → revocado; habilitar de nuevo requiere provisión
externa explícita. Sustitución atómica del archivo aplica la revocación en la siguiente
petición, incluida conexión HTTP reutilizada. Rol/cabeceras del cliente o cookies de
Grafana no sustituyen la autorización del gateway.

## Contexto de correlación

| Campo | Regla |
| --- | --- |
| `environment`, `service_version` | Configuración confiable; nunca entrada del cliente. |
| `operation_ref` | UUID opaco interno de operación lógica; null solo sin contexto confiable disponible. |
| `attempt_ref` | UUID de intento lógico; nuevo en reenvío explícito, el mismo en recuperación. |
| `execution_ref` | UUID nuevo por ejecución/reconciliación. |
| `publication_ref` | UUID técnico ligado a publicación003; no nombres, hashes de contenido o descriptores nativos. |
| `parent_operation_ref` | Relación explícita al iniciar otra operación, nunca coincidencia de texto. |
| `trace_id`, `span_id` | Hexadecimal OTel de 32/16 caracteres no nulos, generado por instrumentación confiable. |
| `context_status` | `available`, `unavailable` o `recovered`; sin padre inventado. |

Reutilizar referencias UUID opacas compatibles del propietario. Si `publication_ref` de
003 es clave semántica, mapearla mediante HMAC-SHA256 con clave por entorno a UUID opaco,
con versión de mapeo configurada. No registrar entrada del HMAC ni clave; la rotación
inicia nueva versión y declara límite de correlación. 003 conserva identidad/evidencia
exactas. El mapeo técnico no modifica archivos, credenciales ni documentos funcionales.

Continuaciones usan `contextvars`; trabajos durables conservan al menos referencia
interna del productor. Tras reinicio: nueva traza, misma `operation_ref`, nueva
`execution_ref`; link al span anterior solo con contexto confiable conservado. Consulta
por referencia enlaza ambas trazas sin inventar continuidad de un span interrumpido.

## Evento de log

Esquema normativo: [log-event.schema.json](contracts/log-event.schema.json).

| Campo | Tipo / invariantes |
| --- | --- |
| `schema_version` | `1` |
| `event_id`, `boot_id` | UUID del evento/arranque; evento serializado inmutable |
| `sequence` | Positivo creciente por arranque, asignado antes de admisión; descarte deja hueco |
| `timestamp` | RFC3339 UTC con `Z`, instante técnico original, no período medido |
| `environment`, `service_version`, `policy_revision` | Configuración validada y acotada |
| `event`, `operation`, `stage` | Catálogos cerrados; nunca texto libre de fuente |
| `source_module` | Módulo productor del catálogo; permite distinguir cambios administrativos sin revelar entidad/actor |
| `severity` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `outcome` | `success`, `expected_rejection`, `unexpected_error`, `in_progress`, `not_applicable` |
| `code` | Código seguro registrado; desconocido → `unclassified`, sin original |
| referencias | Contexto anterior, null explícito si no disponible |
| `duration_ms` | Número finito >=0 por reloj monotónico, o null si no observable |
| `counts` | Enteros tipados >=0 de archivos/registros; sin lecturas, importes ni IDs libres |
| `health` | Solo heartbeat/control: contadores acumulados, profundidades y último envío |

Máximo 16 KiB UTF-8 serializados. `additionalProperties: false`; sin `message`,
`exception`, `body`, `extra` o mapas libres. Código de catálogo aporta texto legible en
visor. Rechazar campo/tipo desconocido antes de encolar y contar `schema_rejected` sin
alterar operación funcional. Validación semántica adicional: terminal exige resultado
final; fallo exige código; heartbeat exige salud; referencias/conteos son confiables.

Estado: construido → validado/saneado → encolado → escrito → recolectado; un descarte
no se declara entregado. Recibir telemetría no es confirmación de negocio.

Un fallo de ejecución no implica que el intento lógico esté terminado:002 conserva
`processing|partial_failure` recuperables. Su fallo emite `execution.completed` con
`unexpected_error` y `counts=null`; el terminal `reception.completed` se reserva a la
transición durable a `completed`, con el resumen completo del intento. Las métricas de
registros excluyen etapas/ejecuciones y una lectura sin procesamiento no reemite terminales.

## Traza y span

`trace_id`, `span_id`, padre/link, operación/etapa, inicio/fin, duración, resultado,
código y referencias confiables. Allowlist equivalente al sobre; <=32 atributos con
cadenas <=128 caracteres, <=16 KiB por span exportable. Máximo 256 spans activos y 2048
pendientes; exceso descartado/contabilizado sin espera. OTel: éxito `OK`, rechazo esperado
`UNSET` con resultado explícito, fallo inesperado `ERROR` y código seguro. Sin captura
automática de excepción/stack. Spans hijos de validación no inflan operaciones.

## Métrica técnica y resultado de consulta

Definición versionada con nombre, unidad, hecho, eventos elegibles, dimensiones,
numerador/denominador y agregación. Resultado: `[start,end)`, corte, entorno, filtros,
valor nullable y cobertura. Dashboard muestra esos campos en paneles asociados, sin API
funcional nueva. Métricas derivadas de logs conservados, no registro contable durable.
Versión se usa como campo/filtro; IDs de operación/publicación/arranque nunca son dimensiones.

## Política de telemetría

Revisión, entorno, retención por señal, ratio de trazas, límites de cola/tamaño/spool,
heartbeat/umbral, timeouts y cuotas. Validar antes de habilitar emisión: configuración
técnica inválida deshabilita esa emisión con diagnóstico local saneado, sin impedir el
arranque funcional. El stack técnico puede fallar su propio chequeo de configuración.
Cambios emiten `policy.changed` y revisión en cada evento. Valores en [contrato técnico](contracts/technical-access.md).

## Estado de recolección y cobertura

Entorno, señal, arranque, último heartbeat UTC, última secuencia, descartes, último envío
exitoso del recolector, política y causa conocida. Sin almacenamiento en auditoría
funcional. Dashboard incluye configuración esperada aunque nunca haya llegado una señal.

El objeto `health` conserva dos evidencias de transporte independientes:

| Campo | Restricción |
| --- | --- |
| `log_collector_status` | `available`, `degraded` o `unknown`; solo recolección de logs |
| `last_log_collector_success` | RFC3339 UTC con `Z`, <=40 caracteres o null si no existe éxito observado |
| `trace_export_status` | `available`, `degraded` o `unknown`; solo exportación OTLP |
| `last_trace_export_success` | RFC3339 UTC con `Z`, <=40 caracteres o null si no existe éxito observado |
| `trace_export_failures_total` | Entero acumulado >=0 por arranque; un lote terminado sin éxito cuenta una vez |
| `trace_exported_spans_total` | Entero acumulado >=0 por arranque; spans de lotes confirmados sin multiplicar por reintento |

Los seis campos son obligatorios cuando `health` es objeto. Un estado `available`
requiere su fecha de último éxito no null. Sin evidencia, estado `unknown`; un fallo
observado informa `degraded`, conservando la última fecha de éxito si existe. El estado
indica el último resultado observado, acompañado por su antigüedad; estar sin nuevos
envíos no demuestra por sí solo una caída. Los contadores existentes de descartes y
profundidad de colas se conservan; `collector_dropped_total` corresponde solo a Alloy/logs.
Los campos genéricos `collector_status` y `last_collector_success` se sustituyen en este
diseño v1 todavía sin implementar; no se requiere migración de registros funcionales.

| Estado | Criterio y presentación |
| --- | --- |
| `complete` | Ventana dentro de retención/inicio conocido, secuencias conciliadas, heartbeats/recolectores continuos, sin pérdidas/replays ambiguos y política compatible. Cero significa cero observado. |
| `partial` | Pérdida/hueco conocido, muestreo de esa señal, arranque/cierre dentro de ventana o conservación vencida. Valores observados con causa, sin totalidad. |
| `unknown` | >45 s sin heartbeat, receptor inaccesible o continuidad/posiciones no verificables. Último dato si existe; total desconocido. |

Un heartbeat restablece continuidad actual; no rellena huecos históricos. Coberturas de
logs/métricas y trazas independientes: muestrear trazas no reduce conteos de logs.
Ausencia de una referencia no prueba que no hubo operación: puede ser muestreo, pérdida,
retención o contexto desconocido, y esa limitación debe verse en consulta.

Una confirmación OTLP acredita aceptación por transporte, no persistencia consultable.
La cobertura de trazas exige contrastar política, pérdidas y referencias esperadas con
señales consultables bajo autorización Programador; consulta fallida/truncada o evidencia
insuficiente → `unknown`. El éxito de Alloy no acredita trazas y una caída de Loki no
invalida por sí sola trazas disponibles. Recuperar transporte no rellena huecos anteriores.
