# Contrato común de auditoría, eventos y cobertura

Propietario: plataforma009. [Modelo](../data-model.md), [arquitectura](../../../docs/architecture.md).

## EventWriter y FunctionalAudit

`EventWriter.append` y `FunctionalAudit.append` reciben la unidad de trabajo del productor,
actor/proceso, procedencia, fechas y carga tipada/saneada. Escriben junto con su resultado;
no hacen commit por separado ni usan HTTP, SMTP o un broker. Tras un error que revierte
cálculo/generación, resultado de fallo y evento se confirman juntos en una UoW nueva.
Si la base está inaccesible, no se afirma durabilidad. Repetir la misma identidad de
procedencia no crea otro evento; la clave es módulo + entidad + revisión + tipo.

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

Los nombres de sobre `event_id`/`type` se mapean explícitamente a las columnas `id`/`event_type`;
no son otras tablas o identidades. Los productores amplían cargas tipadas por capacidad,
sin importar consumidores. Los formatos nativos PAS600 permanecen intactos.

## FunctionalSummary.read

Entrada: tipos de contenido, ventana `[inicio,fin)`, corte y permisos actuales. Resultado:
ítems con conteo, cobertura, períodos/huecos/motivo y referencias, sin cuerpos ni secretos.
Los permisos los entrega identidad; la plataforma conserva la evidencia y los módulos
implementan la consulta de sus propios datos. El adaptador de 008 compone el resultado.


La lectura devuelve un ítem por contenido seleccionado, incluido aquel cuya
fuente no se pueda consultar. No usa logs o heartbeats técnicos como prueba de integridad.

| Estado | Criterio | Conteo y alcance |
| --- | --- | --- |
| `completa` | Historial funcional íntegro de toda `[inicio,fin)` al corte. | `count` entero >=0; períodos cubiertos abarcan la ventana y no hay huecos conocidos. |
| `incompleta` | Existen intervalos faltantes conocidos, incluidos historia anterior al inicio de registro o conservación vencida. | Conteo observado si se conoce, NULL en caso contrario; períodos cubiertos y huecos identificados. |
| `desconocida` | No puede determinarse la integridad o consultarse la fuente. | Conteo observado solo si existe evidencia disponible; NULL si no se conoce, nunca cero inventado. |

Cada ítem incluye `covered_periods`, `known_gaps`, `limitation_code` y referencias de origen.
Los períodos están acotados a la ventana del resumen y se evalúan al mismo corte. Fuera de
cobertura completa, la UI/correo identifica todo conteo disponible como observado/parcial.
Historia íntegra con cero sucesos es distinta de falta de historia o fuente no consultable.

La presentación del estado global del correo pertenece a spec-008, no al mecanismo común.
