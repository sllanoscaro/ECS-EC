# Data Model: Notificaciones programables

Diseño lógico PostgreSQL 18, previo a migraciones. Todas las entidades pertenecen al
monolito. Las cuentas, categorías y datos de origen pertenecen a sus módulos originales.

## Convenciones

- Identidades UUID generadas por la aplicación; revisiones enteras positivas.
- Instantes UTC en `timestamptz`; conservar además zona IANA, intención local y versión
  de tzdata en resultados calendario. Intervalos `[inicio, fin)`, siempre inicio < fin.
- Energía y umbrales `NUMERIC`/Decimal finitos no negativos, transmitidos como cadenas
  decimales sin redondeo implícito. No aceptar NaN, infinito ni float binario para comparar.
- `created_at`, `recorded_by` (cuenta o proceso interno), `retain_until` en registros
  históricos. No usar borrado en cascada que destruya evidencia protegida.
- JSONB tiene esquema explícito de aplicación; no es un contenedor de archivos, excepciones
  o cuerpos SMTP. Las columnas críticas de identidad, estado, fecha e índices son relacionales.

## Relaciones

```text
Cuenta (spec-006) <- DestinatarioVersion -> VersionRegla <- Regla
                                            |
                                            +-> Activacion -> EstadoEvaluacion -> Episodio
                                            |       |
                                            |       +-> Ocurrencia
                                            +----------> Ocurrencia -> Notificacion
                                                                         |
Cuenta <------------------------------------------------------------- Entrega -> Intento
                                                                         |
                                                         DecisionReenvio --+
EventoFuncional -> Evaluacion -> Evidencia -> Episodio/Notificacion
Entrega original -> MiembroRecuperacion <- Entrega de recuperación
```

## Entidades

### Regla (`notification_rule`)

| Campo | Tipo/regla |
| --- | --- |
| `id`, `building_id` | UUID, edificio único del alcance |
| `name` | Texto recortado, 1..120 caracteres |
| `current_version_id` | FK a su versión vigente |
| `status` | `desactivada`, `activa`, `pausada` |
| `revision` | Entero para control optimista (`If-Match`) |
| `created_at`, `updated_at`, `created_by` | Procedencia administrativa |

No se elimina por API. Guardar una revisión incrementa `revision`, reemplaza la versión
vigente, pausa la regla y cancela pendientes de la versión anterior atómicamente.
Activación/pausa quedan además en auditoría funcional de spec-006.

### Versión (`notification_rule_version`)

| Campo | Tipo/regla |
| --- | --- |
| `id`, `rule_id`, `version_number` | UUID/FK; UNIQUE `(rule_id, version_number)` |
| `mode` | `periodica` o `urgente` |
| `content_types` | Conjunto no vacío del catálogo permitido |
| `schedule_id` / `condition_id` | Exactamente uno según modalidad |
| `timezone` | Zona IANA válida, copiada del edificio o explícita |
| `template_version`, `created_by`, `created_at` | Plantilla aprobada y procedencia |
| `retired_at`, `retain_until` | Historial y conservación |

Versión inmutable tras guardarse. `DestinatarioVersion` contiene FK `(version_id, account_id)`
única. Las direcciones no son destinatarios válidos por sí solas; se resuelven en spec-006.
Se exige una cuenta activa como mínimo y permiso sobre todo el contenido al activar.
Incluir `cambios_administrativos` exige administradores técnicos para todos los destinatarios.

### Programación (`notification_schedule`)

| Campo | Tipo/regla |
| --- | --- |
| `id`, `version_id` | Una programación por versión periódica |
| `kind` | `intervalo`, `diaria`, `semanal`, `mensual`, `anual` |
| `starts_at` | Instante RFC3339; límite inferior y ancla para intervalos |
| `interval_value`, `interval_unit` | Entero >0 y `minutos`/`horas`, solo intervalo |
| `local_time` | HH:MM, solo calendario |
| `weekday` | ISO 1..7, solo semanal |
| `day_of_month` | 1..31, mensual/anual; conservar el valor nominal |
| `month` | 1..12, solo anual |
| `timezone` | Zona IANA; nunca offset fijo en sustitución |

Las combinaciones no aplicables se rechazan. La política de huecos, repeticiones y último
día válido se define en [integrations.md](contracts/integrations.md#calendario).

### Condición (`notification_condition`)

| Variante | Datos |
| --- | --- |
| `consumo` | `category_id` CAT-01..07, `unit=kWh`, `window_kind` intervalo/hora/dia/mes/anio, `comparison` gt/gte/lt/lte, `threshold_kwh` Decimal; resolución de intervalo si aplica |
| `ausencia_datos` | Categoría, `silence_minutes` entero >=15 |
| `evento_sistema` | Tipo: `recepcion_rechazada`, `calculo_fallido` o `pdf_fallido` |

`interval` usa `measurement_interval_seconds` >0 y la resolución/configuración de la serie;
no se infiere de los 15 minutos mínimos entre recepciones. La configuración de fuentes
pertenece a specs-001/002. Una categoría sin fuente produce `no_evaluable`; CAT-01 calculada
requiere base no vacía y disponibilidad de totales válidos, no un medidor físico total.

### Activación y cursor (`notification_activation`, `notification_evaluation_state`)

Activación: `id`, `version_id`, `activated_at`, `ended_at`, `next_due_at`,
`last_materialized_slot`, `tzdata_version`, actor y revisión. Una activación vigente por
regla mediante índice único parcial. Pausa termina la activación; reactivar inicia otra
sin reproducir fechas anteriores. Cada ocurrencia sigue incluyendo su versión de regla.
Antes de habilitar planificación tras un inicio de versión, comparar `tzdata_version`
registrada e instalada; reconciliar las activaciones con futuros no materializados bajo
liderazgo y transacción por regla. Actualizar `next_due_at`/versión preservando ancla nominal
sin modificar slots existentes, evidencia, cortes o historial. Un reinicio intermedio retoma
la reconciliación idempotente; no habilitar planificación con reglas aún sin reconciliar.
Las previsualizaciones afectadas quedan inválidas; los vencidos mantienen recuperación.

Estado: UNIQUE `(activation_id, scope_key)`; guarda `last_valid_window_end`,
`last_evaluated_window_end`, `last_new_data_accepted_at`, `last_result`, `open_episode_id`
y cursor de evento. `scope_key` es la categoría conocida o tipo de evento, nunca un correo.
Solo una evaluación válida hace avanzar `last_valid_window_end`; los estados no evaluables
se registran sin cerrar episodio. Actualizar estado/episodio/entregas en una transacción.

### Evento funcional y evaluación

`FunctionalEvent` es una referencia externa a audit de plataforma009, cuyo
[modelo](../009-fundaciones-plataforma/data-model.md) y
[contrato](../009-fundaciones-plataforma/contracts/integrations.md) poseen campos,
unicidad, cobertura y conservación comunes. Este módulo no crea ni migra esa tabla.
La evaluación referencia la identidad estable de un evento confirmado por su productor.

`notification_evaluation`: `id`, `activation_id`, `source_event_id` opcional,
`window_start/end`, `cutoff_at`, `evaluated_at`, `result` (`cumple`, `no_cumple`,
`no_evaluable`, `omitida_historica`), `reason_code`, `evidence_id`, `episode_id` opcional.
Deduplicar por activación, revisión de evidencia y ventana o evento puntual. La evaluación
de un lote elige solo la ventana completa más reciente admisible y registra omisiones.

### Evidencia (`notification_evidence`)

`id`, `source_refs` con versiones, categoría, magnitud, unidad, límites de ventana,
`cutoff_at`, cobertura, estado de calidad, `value_kwh` nullable, `origin` (`medido`,
`calculado`, `sin_fuente`), base y alcance del total calculado, fórmula/versión del cálculo,
instantes de recepción/detección y motivo de limitación. Preservar la información necesaria
para reconstruir la decisión aunque el detalle de origen cumpla antes su plazo mínimo.

Valor ausente es NULL con razón explícita. Un total CAT-01 calculado identifica categorías
de base y sus fuentes; este módulo consume el total existente y no vuelve a sumarlas.
Solo una ventana completa y válida permite `cumple`/`no_cumple` en una condición de consumo.
Para resúmenes conservar conteos funcionales y sus referencias, sin archivos recibidos ni secretos.
Cada `summary_item` identifica tipo, `count` entero no negativo o NULL, `coverage`
(`completa`, `incompleta`, `desconocida`), períodos cubiertos, huecos conocidos y motivo
funcional de limitación. Cobertura completa exige conteo conocido e historia íntegra
para toda la ventana; en otro caso un conteo disponible es observado y no un total completo.
NULL significa conteo desconocido y nunca se serializa como cero. Se incluye un ítem
por cada contenido seleccionado aunque su fuente no pueda consultarse.

La evidencia de integridad del historial pertenece a auditoría: `functional_history_coverage`
con tipo de contenido/módulo, período registrado, alcance conservado, huecos conocidos,
revisión, origen y fechas. El resumen toma una captura al mismo corte de los conteos;
una fuente no consultable o sin evidencia suficiente queda desconocida. La conservación
vencida o una ventana anterior al registro íntegro son huecos conocidos. No inferir
cobertura funcional a partir de heartbeats/logs de observabilidad técnica.
El estado global es `sin_novedades` solo si todos los ítems están completos y en cero;
`disponible` si todos completos y alguno positivo; `informacion_insuficiente` si cualquiera
está incompleto/desconocido, conservando los resultados observados y su alcance.

### Episodio (`notification_episode`)

`id`, `activation_id`, `scope_key`, `opened_at`, `closed_at`, `opening_evidence_id`,
`closing_evidence_id`, `source_event_id` opcional y `status` (`abierto`, `cerrado`,
`finalizado_por_regla`). Índice único parcial de episodio abierto por activación/alcance.
Para eventos puntuales, unicidad por activación/evento. Reevaluar un episodio abierto no
crea otra urgencia. No evaluable mantiene el episodio; normalidad válida lo cierra y rearma.
Finalizar por pausa no afirma normalización del consumo.

### Ocurrencia (`notification_occurrence`)

`id`, `version_id`, `activation_id`, `kind` (`periodica`, `urgente`, `recuperacion`),
`logical_key`, `nominal_local_slot`, `scheduled_at`, `detected_at`, `window_start/end`,
`cutoff_at`, `episode_id` opcional, `tzdata_version`, `is_late`, `created_at`.

UNIQUE `(version_id, logical_key)`: clave periódica representa el slot nominal y ancla;
urgente representa episodio/evento; recuperación usa identidad estable de lote. El slot
local evita que una hora repetida cree dos ocurrencias. Guardar instante resuelto UTC.
Solo reintentar materialización de la misma clave no crea contenido ni entregas nuevos.

### Notificación (`notification_message`)

`id`, `occurrence_id`, `template_version`, `functional_content` tipado e inmutable,
`content_hash`, `required_permissions`, `created_at`, `retain_until`. UNIQUE ocurrencia.
Contenido: edificio, tipo/prioridad, regla/versión, estado, período, corte, evidencia y
rutas funcionales protegidas. Sin logs, trazas, métricas, secretos, cuerpos de archivos ni
excepciones. Enlaces se forman con URL del entorno y no contienen tokens de acceso público.

### Entrega (`notification_delivery`)

| Campo | Tipo/regla |
| --- | --- |
| `id`, `message_id`, `account_id` | Identidad individual |
| `generation` | 0 original; >0 reenvío manual |
| `state` | `pendiente`, `en_intento`, `aceptada`, `fallida`, `cancelada`, `indeterminada` |
| `next_attempt_at`, `attempt_count` | Fecha de elegibilidad y 0..3 para esta entrega |
| `smtp_message_id` | Estable dentro de entrega; distinto en reenvío manual |
| `transport_kind` | `local_prueba` o `smtp_produccion` |
| `parent_delivery_id` | Original del reenvío, si existe |
| `cancellation_reason`, `created_at`, `retain_until` | Razón funcional y conservación |

UNIQUE `(message_id, account_id, generation)`. Sin correo fijo en pendiente: resolver correo
vigente antes de cada intento. Los permisos del mensaje se comprueban íntegramente, sin
enviar una versión silenciosamente recortada a un destinatario ya no elegible.

### Intento (`notification_delivery_attempt`)

`id`, `delivery_id`, `attempt_number`, `effective_email` (solo historial funcional protegido),
`authorized_at`, `started_at`, `finished_at`, `transport_kind`, `process_ref`,
`outcome` (`aceptada`, `no_aceptada_transitoria`, `no_aceptada_definitiva`, `indeterminada`),
`functional_reason_code`, `acceptance_confirmed_at`, referencia del relay si existe.
UNIQUE `(delivery_id, attempt_number)`, número 1..3, un intento abierto máximo por entrega.

Registrar intento y pasar a `en_intento` atómicamente antes de SMTP. SMTP no usa una
transacción abierta de base. Error posterior a DATA aceptado no cambia a fallo. Si el
proceso termina sin evidencia durable, la reconciliación usa `indeterminada` de manera
conservadora, aunque el envío pudiera haber sido aceptado externamente.

### Recuperación y reenvío

`notification_recovery_member`: `original_delivery_id` UNIQUE, `recovery_delivery_id`,
slot/período original y fecha. Incorporar solo originales periódicos vencidos, vigentes
y `attempt_count=0`. Cancelarlos con razón `consolidada_en_recuperacion`, conservando vínculo.
Consolidación, miembros y nueva entrega en una transacción; conservar períodos separados
si existen huecos por entregas ya intentadas. Agrupar por versión y cuenta, no mezclar reglas.

`notification_resend_decision`: `id`, `parent_delivery_id`, `new_delivery_id`,
`administrator_id`, `decided_at`, `reason`, `acknowledge_possible_duplicate`,
`idempotency_key`, `request_hash`. Clave única por administrador/operación y clave idempotente.
Misma clave/cuerpo devuelve la decisión original; cuerpo diferente devuelve conflicto.
Reenvío solo con regla vigente, destinatario elegible y estado fallido/indeterminado.
Una entrega aceptada no se reenvía desde esta función.

### Idempotencia HTTP (`notification_api_idempotency`)

`actor_id`, `operation`, `idempotency_key`, `request_hash`, `resource_id`, `http_status`,
`created_at`, `retain_until`; UNIQUE `(actor_id, operation, idempotency_key)`. Guardar con
el cambio de negocio en la misma transacción para creación, revisión, activación, pausa
y reenvío. Autenticar y autorizar primero; después consultar esta clave antes de evaluar
`If-Match` de una acción ya confirmada. Así un reintento con la revisión original no
ejecuta de nuevo ni falla por la revisión que esa misma acción incrementó. Un cuerpo
distinto con la misma clave devuelve 409. Conservar al menos los 12 meses funcionales;
guardar referencias, no copias indiscriminadas de respuestas ni secretos de sesión.

## Transiciones

| Entidad/estado | Evento | Resultado |
| --- | --- | --- |
| Regla desactivada/pausada | Activación con vista previa válida | Activa, nueva activación y siguiente ocurrencia admisible |
| Regla activa | Pausa o revisión | Pausada; pendientes canceladas, sin retirar intentos iniciados |
| Episodio ausente/cerrado | Evaluación válida cumple | Nuevo abierto y una urgencia |
| Episodio abierto | Cumple de nuevo / no evaluable | Sigue abierto, sin otra urgencia |
| Episodio abierto | Normalidad válida | Cerrado y rearmado |
| Entrega pendiente | Cuenta/regla/permisos no elegibles | Cancelada solo para esa entrega |
| Entrega pendiente | Revalidación y plaza de transporte | En intento; incrementar contador y registrar intento |
| En intento | DATA aceptado confirmado | Aceptada, terminal |
| En intento | No aceptación transitoria confirmada, intento 1/2 | Pendiente a +1/+5 minutos desde final del intento |
| En intento | Rechazo definitivo/configuración o tercer transitorio | Fallida, terminal automático |
| En intento | Aceptación desconocida/reinicio sin prueba | Indeterminada, terminal automático |
| Fallida/indeterminada | Reenvío explícito autorizado | Nueva entrega pendiente vinculada; anterior inmutable |

## Concurrencia e índices

Orden de bloqueos compartido con mutaciones de identidad/regla: regla -> cuenta -> entrega.
Revalidar versión/activación, destinatario, estado activo, correo actual y permisos dentro
de la transacción de preparación. Pausa/revisión o revocación anteriores a ese punto
impiden iniciar; un intento ya iniciado puede completar sin invalidar su historia.
Una mutación de identidad que afecta varias reglas las bloquea por UUID ordenado antes
de la cuenta; revalida el conjunto tras bloquear y reintenta si cambió para evitar deadlocks.

Índices de cola `(next_attempt_at, id) WHERE state='pendiente'`, programación
`(next_due_at) WHERE ended_at IS NULL`, eventos por cursor y resultados de historial
por `(account_id, created_at, id)`, regla, estado y fecha. Paginación por cursor estable.
Las restricciones únicas, no el scheduler de un solo proceso, protegen deduplicación lógica.

## Conservación

`retain_until` se calcula sumando 12 meses calendario en la zona del edificio al registro
o revisión sustantiva y convirtiendo a UTC; último día válido si falta el aniversario.
Si la hora de aniversario no existe, usar el primer instante local válido posterior;
si se repite, usar la segunda ocurrencia (`fold=1`) para no adelantar el límite, conforme
a FR-017 de spec-002. Esta política difiere de `fold=0` del scheduler.
No retrasar el límite por consultas, duplicados ni reintentos de la misma operación.
Cada intento y decisión tiene su propio plazo. No eliminar padre/evidencia mientras una
versión, entrega, intento o decisión dependiente siga protegida; extender el padre hasta
el máximo de sus dependientes. Cumplir el mínimo no obliga a borrar automáticamente.

Cuentas desactivadas mantienen su identidad histórica. Direcciones efectivas de intentos
no se emiten en telemetría. La retención técnica es independiente y nunca purga este historial.
