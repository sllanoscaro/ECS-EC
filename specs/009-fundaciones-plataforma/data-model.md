# Data Model: Persistencia funcional común

Diseño lógico previo a migraciones. La [arquitectura](../../docs/architecture.md) define
convenciones de identidad/fecha/precisión. Esta spec posee tablas comunes; las specs de
negocio no vuelven a declararlas en sus migraciones.

## Evento funcional (`functional_event`)

Modelo `backend/src/ecs_ec/audit/models.py`; escritor `backend/src/ecs_ec/audit/events.py`.

`functional_event`: `id`, `event_type`, `source_module`, `source_entity_id`, `source_revision`,
`occurred_at`, `recorded_at`, `effective_window`, `accepted_new_data`, `safe_payload`,
`correlation_ref`; UNIQUE (`source_module`, `source_entity_id`, `source_revision`, `event_type`).
`source_module` identifica el módulo/emisor dentro del espacio de nombres del monolito;
esa clave compuesta es el mecanismo de deduplicación, mientras que `id` es el UUID estable
del evento persistido.
Se crea con el cambio funcional original. No modificar formatos nativos PAS600 para añadirlo.

## Auditoría funcional

Tabla `functional_audit`, propiedad de plataforma009:

| Campo | Tipo lógico y regla |
| --- | --- |
| `id` | UUID, clave primaria generada por la aplicación. |
| `actor_ref` | Referencia opaca no nula a cuenta o proceso; sin FK obligatoria a identidad. |
| `action` | Código estable de acción definido por el módulo productor. |
| `entity_type`, `entity_id` | Tipo y UUID de la entidad afectada; no crean FK a tablas de negocio. |
| `entity_revision` | Revisión positiva de la entidad cuando exista; nullable solo si el productor no versiona esa entidad. |
| `occurred_at`, `recorded_at` | Instantes UTC: momento de la acción y momento de persistencia. |
| `result` | Resultado tipado del intento, por ejemplo `succeeded` o `denied`; el vocabulario se amplía por acción. |
| `safe_payload` | JSONB con esquema por acción, limitado a datos aprobados y saneados. |
| `retain_until` | Instante UTC calculado según la regla común de conservación. |

Cada módulo define la semántica y el esquema permitido de sus acciones. La identidad
primaria UUID permite registrar acciones repetidas legítimas: no hay unicidad global por
actor, acción, entidad o revisión. Un productor que reintente la misma operación debe
proporcionar idempotencia en su propio contrato cuando la necesite. `safe_payload` no
incluye secretos, excepciones crudas, SQL, cuerpos de solicitud ni datos personales que
no sean necesarios para la evidencia. `recorded_by` en otras entidades históricas comparte
la semántica de referencia opaca de `actor_ref`.

La spec-006 posee la semántica de acciones administrativas, permisos de consulta y sus
denegaciones; cada módulo produce sus acciones en la misma transacción que el cambio
funcional correspondiente.

## Evidencia de cobertura

Tabla `functional_coverage`, propiedad de plataforma009:

| Campo | Tipo lógico y regla |
| --- | --- |
| `id` | UUID, clave primaria generada por la aplicación. |
| `content_type` | Tipo estable del contenido funcional cubierto. |
| `source_ref` | Referencia opaca a la fuente o productor consultado; no requiere FK externa. |
| `source_revision` | Revisión/cursor de origen que fundamenta la evidencia, nullable si no está disponible. |
| `cutoff_at` | Instante UTC al cual se evaluó la evidencia. |
| `window_start`, `window_end` | Instantes UTC de la ventana semiabierta `[window_start, window_end)`; `window_start < window_end`. |
| `integrity` | Uno de `completa`, `incompleta` o `desconocida`. |
| `observed_count` | Entero >=0 o NULL; nunca se infiere cero por ausencia de historia. |
| `covered_periods`, `known_gaps` | JSONB con intervalos tipados y acotados a la ventana, sin solapamientos internos. |
| `limitation_code` | Código estable nullable que explica una limitación conocida. |
| `created_at`, `recorded_by` | Instante UTC de creación y referencia opaca del proceso que registró la evidencia. |
| `retain_until` | Instante UTC calculado según la regla común de conservación. |

`completa` requiere conteo conocido, períodos cubiertos contiguos que abarquen toda la
ventana y ningún hueco. `incompleta` requiere al menos un hueco conocido; conserva el
conteo observado si puede establecerse, y usa NULL si no. `desconocida` indica que no
puede determinarse la integridad o consultarse la fuente; el conteo solo se conserva si
hay evidencia observada. Un intervalo anterior al inicio de registro no acredita cero
sucesos. Estado y límites se determinan al corte. La cobertura funcional sobrevive a la
conservación técnica y no se deriva de heartbeats.

No se impone unicidad por contenido/ventana: un mismo rango puede tener cortes o revisiones
distintos. Se indexa `(content_type, window_start, window_end, cutoff_at)` para consultas
por contenido/ventana y `(source_ref, cutoff_at)` para localizar evidencia de una fuente.
Las restricciones de ventana, conteo e integridad se aplican en base de datos cuando sean
representables y también se validan en el servicio.

## Conservación e integridad

`created_at`, `recorded_by` y `retain_until` en evidencia histórica de cobertura; auditoría
usa `recorded_at`, `actor_ref` y `retain_until`. Los eventos usan `recorded_at` y
`retain_until` además de su procedencia; no duplican `created_at`/`recorded_by`. Conservar
al menos 12 meses calendario desde registro/revisión sustantiva y extender evidencia
referenciada por dependientes protegidos. Sin cascadas destructivas. Una lectura no extiende el plazo;
su vencimiento no exige borrado automático. Migración base propia, sin tablas de negocio.
