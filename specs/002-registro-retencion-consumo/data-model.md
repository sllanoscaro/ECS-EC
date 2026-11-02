# Modelo de datos: Registro temporal y retención del consumo

[Spec](spec.md), [plan](plan.md), [decisiones](research.md),
[modelo 001](../001-visualizar-consumo-categorias/data-model.md).
Modelo normativo: entidades propias002 implementadas en `consumption`, migración
`47457bdabdfa`. [Estado y límites de validación](validation/acceptance.md).
UUID generados por aplicación, revisiones positivas, instantes UTC `timestamptz` con
microsegundos, zona IANA explícita, intervalos `[start,end)` y Decimal/NUMERIC exacto.
HTTP conserva decimales y duraciones grandes como cadenas.

## Propiedad, relaciones y migraciones

| Entidad / proyección | Propietario y relación |
| --- | --- |
| BuildingContext, ConsumptionCategory, InstallationRevision, CategorySource, MeasurementSource | 001; FK protegidas desde 002, sin recrearlas. |
| ReceptionAttempt, CategoryUpdate, ReceptionRecordResult | 002; intento lógico y resultados por categoría/posición. |
| CategoryReceptionState, BuildingReceptionState | 002; exclusión temporal e historia permanente para reconfiguración 001. |
| IncorporatedRecord | 002; identidad/evidencia durable compartida por medidas físicas y totales calculados. |
| AcceptedMeasurement, IncorporatedTotal | 002; payload conservado de un IncorporatedRecord. |
| TotalCalculationState | 002; candidato/diagnóstico/pendiente derivado mediante reglas puras 001. |
| TotalEvaluationRequest | 002; necesidad durable de evaluación CAT-01 registrada con las parciales, incluso antes de existir candidato. |
| ConsumptionAggregate, AggregateContribution | 002; registro conservado y aportes únicos. |
| CalculationContributionReference | 002; relación auxiliar que protege mediante FK los registros de las referencias JSON de candidatos/totales. |
| DetailQueryResult, SourceStatus y configuración | Fachada/dominio 001 sobre proveedores 002. |
| AggregateQueryResult, AdmissibleWindow | Proyecciones 002; sin tabla de resultados de consulta. |
| FunctionalEvent, FunctionalAudit, evidencia común | 009; 002 escribe mediante sus puertos, no redefine tablas. |

Una migración propia incorpora tablas/índices 002 y requiere `btree_gist` habilitada
con permisos adecuados. Enlazar al head real; coordinar Alembic y `models.py` con 001.
Todas las FK históricas usan protección explícita contra cascadas destructivas.

## ReceptionAttempt y resultados por categoría

`ReceptionAttempt`: `id` interno igual al `attempt_id` UUID persistido por el adaptador
confiable antes de la llamada, `building_id`, `publication_ref` opaca del adaptador,
`correlation_ref` interna confiable, `received_at`, `process_ref`, `status`
(`processing|completed|partial_failure`), `completed_at|null`, `retain_until`,
`input_schema_version` positiva, `input_manifest` canónico tipado e inmutable y
`input_digest` SHA-256. El manifiesto conserva la entrada completa del
[contrato de recepción](contracts/integrations.md), incluidos orden/posiciones,
edificio/publicación/correlación, valores/unidades/intervalos/fuentes y referencias
de evidencia; no contiene secretos ni tokens de autorización. El digest acelera la
comparación, sin sustituir la comprobación completa. La primera creación fija ese
manifiesto antes de confirmar resultados por categoría y lo protege durante su plazo.
La publicación agrupa fragmentos de un mismo envío; un intento no es una medición.
Un reenvío después de rechazo temporal obtiene otro intento, aun con igual publicación.
Recuperar el mismo intento interno tras crash permite completar solo sus partes pendientes.
Mismo ID con otra entrada produce `attempt_payload_conflict`; mismo ID completado devuelve
el resultado original, incluso un `too_early`, sin reevaluarlo ni extender conservación.
Un reenvío explícito usa nuevo ID; `read_attempt` no crea ni reanuda intentos y distingue
`not_found` de DB/autorización fallidas. Dos ejecutores coordinan el mismo intento,
recuperando el control tras caída sin procesar una categoría simultáneamente.

`CategoryUpdate`: `id`, `attempt_id|null` (null para trabajo calculado interno),
`building_id`, `category_id`, `kind: physical|calculated`, `evaluated_at`,
`new_data_at|null`, `previous_new_data_at|null`, `next_admissible_at|null`,
conteos de aceptados/duplicados/rechazados, `revision` y `retain_until`.
UNIQUE `(attempt_id,category_id)` para intentos físicos. Una transacción por categoría;
si no incorpora novedades, `new_data_at=null` y el estado temporal no cambia.

`ReceptionRecordResult`: `id`, `attempt_id`, `category_update_id|null`,
`input_position`, `category_id|null`, `record_id|null`, `status: accepted|duplicate|rejected`,
`reason_code|null`, `next_admissible_at|null`, `recorded_at`, `retain_until`.
UNIQUE `(attempt_id,input_position)`. Conflicto se expresa como rechazo con causa.
Categoría desconocida u otro registro no clasificable también conserva posición/motivo.
No almacenar cuerpos arbitrarios ni secretos como diagnóstico.

Transiciones del intento: `processing → completed` cuando todos los resultados son
durables, incluso si hay rechazos funcionales; `processing → partial_failure` si un error
de infraestructura deja categorías sin confirmar. Un fallo de DB no se etiqueta como
aceptación. Un resumen final del intento no condiciona la durabilidad de categorías
ya confirmadas; recuperación recompone el resumen desde sus resultados.
`partial_failure → processing` solo reanuda posiciones/categorías sin resultado durable;
las confirmadas conservan clasificación, fechas y referencias. El resumen puede
reconstruirse sin repetir incorporaciones, eventos ni plazos.

## Estado durable de recepción y reconfiguración

`BuildingReceptionState`: `building_id` PK, `has_accepted_history` inicialmente false,
`first_new_data_at|null`. Una vez true, nunca vuelve a false al retirar detalle.

`CategoryReceptionState`: PK `(building_id,category_id)`, `last_new_data_at|null`,
`next_admissible_at|null`, `latest_interval_end|null`, `revision`.
Preparar siete filas con el catálogo, sin crear aceptaciones. `latest_interval_end` es el
máximo histórico de todos los registros incorporados, incluidos calculados y retirados;
solo null cuando nunca hubo incorporación en esa categoría.

Solo una nueva incorporación confirmada actualiza estos estados, en la misma UoW.
`next_admissible_at = last_new_data_at + 900 segundos` UTC; primera actualización válida
no tiene límite previo. Las siete categorías son independientes. El estado CAT-01
incluye datos físicos y calculados conforme a la configuración histórica.

Orden compartido con 001: contexto/configuración del edificio → filas de categoría
afectadas por ID → candidatos/identidades/agregados por clave. Usar READ COMMITTED,
leer estado y reloj después del bloqueo, no valores previos ni timestamps de fuente.
El trabajo calculado y la retirada respetan el mismo orden.

## IncorporatedRecord: identidad y evidencia que sobreviven al detalle

| Campo | Contrato |
| --- | --- |
| `id`, `revision` | Identidad estable; la evidencia incorporada es inmutable. |
| `building_id`, `category_id`, `kind` | `measured|calculated`; calculado solo CAT-01. |
| `source_id|null`, `logical_source_key|null` | Fuente física 001 o identidad lógica de CAT-01; no medidor ficticio. |
| `start`, `end` | UTC con `start<end`; rango persistido/canónico `[)`. |
| `energy_kwh`, `energy_quanta` | NUMERIC exacto y coeficiente entero de `10^-15 kWh`; equivalentes. No float ni redondeo. |
| `configuration_revision`, `category_revision` | Global de inicio y categoría estable durante todo el intervalo, según 001. |
| `first_incorporated_at`, `update_id` | Instante/plazo de plataforma y actualización que lo confirmó. |
| `source_evidence_ref`, `correlation_ref` | Referencias opacas de procedencia, sin secretos. |
| `provenance_snapshot` | Esquema tipado: modo, fuente o base/referencias calculadas y revisiones históricas. |
| `detail_state`, `detail_withdrawn_at|null` | `retained|withdrawn`, sin convertir un reenvío en dato nuevo. |
| `retain_until`, `retention_timezone`, `tzdata_version` | Límite mínimo calculado al incorporar. |

Medida física: UNIQUE edificio/origen/categoría/start/end UTC. Misma identidad y energía
normalizada equivalente = duplicado; diferente energía = conflicto. Conservar el primer
original, incluso si el reenvío cambia unidad o representación.

Total calculado: UNIQUE edificio/CAT-01/revisión de categoría/start/end. Mismo conjunto
histórico de aportes y energía = duplicado. No recalcular con configuración actual.
La firma histórica y sus referencias se comparan exactamente, sin confiar solo en un hash.

EXCLUDE GiST `(building_id WITH =, category_id WITH =, tstzrange(start,end,'[)') WITH &&)`
para todo registro incorporado, medido o calculado. Así una fuente distinta tampoco
permite superponer intervalos de la categoría. Contigüidad válida; también se verifican
duplicados y superposiciones dentro del lote en orden de entrada estable.
Las comprobaciones previas producen causas funcionales; las restricciones son defensa
final ante carreras. Un savepoint por conflicto recuperable se abre después de los
bloqueos comunes; el resto de la categoría puede continuar. Fallo de infraestructura
revierte su UoW, sin evento/resultado de aceptación.

Este registro y sus identidades no se purgan en esta versión. No es el detalle original
web: la retirada elimina el payload permitido y lo excluye de `read_detail`, pero mantiene
el mínimo para agregación, idempotencia, exclusión y límites de reconfiguración.

## AcceptedMeasurement e IncorporatedTotal

`AcceptedMeasurement` tiene PK/FK `record_id`, `original_value` Decimal,
`original_unit: Wh|kWh|MWh`, representación original/evidencia aprobada,
`first_accepted_at` y `retain_until`. Los demás campos normalizados son del registro.
La validación/conversión pertenece a 001: energía individual `0<=E<10^30` y múltiplo de
`10^-15 kWh`. No cambiar precisión, fuente o referencias al reenviar.

`IncorporatedTotal` tiene PK/FK `record_id`, `first_incorporated_at`, `retain_until`,
`base_categories` no vacía, `basis_sources` y contribuciones inmutables tipadas:
`record_id`, revisión, categoría, fuente, revisión de categoría, energía e intervalo.
Una contribución exacta por cada parcial requerida; no sumar subintervalos para
simular alineación. Valor = suma exacta de la base, hasta `6*(10^30-10^-15)` inclusive,
sin aplicar techo individual. Solo se incorpora con fuente lógica calculada 001,
candidato completo y límite CAT-01 admisible.

Proteger configuración, fuentes y referencias necesarias para consultar ambos payloads
durante su mínimo. Los registros auxiliares de las contribuciones nunca desaparecen.
Si hace falta el original para una referencia protegida, extender su protección efectiva
hasta la del dependiente; una referencia no se rompe mediante DELETE CASCADE.

## TotalEvaluationRequest: evaluación recuperable antes del candidato

Campos: `id` UUID, `building_id`, `start/end` UTC con `start<end`,
`revision` positiva, `status: pending|processed`, `created_at`, `updated_at`,
`processed_at|null`, `trigger_update_id`, `correlation_ref` y `retain_until`.
UNIQUE `(building_id,start,end)`. Identifica un intervalo observado que puede afectar
CAT-01 calculada según la configuración histórica; no es una medición ni otro evento
común de auditoría. La migración/tablas pertenecen a 002.

La aceptación de parciales nuevas crea o reactiva la solicitud en su misma UoW,
con `status=pending` y `processed_at=null`. Una reactivación por novedades incrementa
revisión y actualiza referencia/fecha; duplicados/rechazos no crean ni reactivan
solicitudes. Su retención sigue el mínimo común desde registro/revisión sustantiva.

El trabajo toma contexto/configuración → categorías ordenadas → solicitudes/candidatos.
Lee todas las contribuciones confirmadas y guarda candidato, diagnóstico o total
incorporado mediante reglas 001, junto con `status=processed` y `processed_at` en
la misma UoW. Si el total completo aún no es elegible, persiste el candidato pendiente
antes de marcar procesada la solicitud. Si falla, ambas escrituras revierten y la
solicitud sigue pendiente. No borrar evidencia protegida al terminar.

Los productores usan la misma coordinación: una novedad concurrente queda incluida
en la evaluación o reactiva la solicitud después del commit del trabajo; nunca se
consume una solicitud sobre una captura anterior a esa novedad. Arranque y ejecución
periódica consultan solicitudes `pending`, aunque no exista candidato, además de
candidatos pendientes de incorporación. No se requiere reenvío ni una consulta GET.

## TotalCalculationState y recuperación

PK lógica: edificio, intervalo y firma/revisiones históricas; `id` UUID, `revision`,
`status: incomplete|no_basis|pending|incorporated`, `reason_code|null`,
`configuration_segments`, `base_categories`, `contribution_refs`, `missing_categories`,
`next_admissible_at|null`, `incorporated_record_id|null`, `updated_at` y `retain_until`.
Datos tipados, sin valores numéricos publicados mientras no se incorpore.
Reevaluaciones sin cambios de evidencia/estado conservan revisión y vencimiento;
duplicados y sondeos del trabajo no se consideran una revisión sustantiva.

- Parciales faltantes/desalineadas: `incomplete/missing_contributions`.
- Firma calculada cambia dentro del intervalo:
  `incomplete/calculation_configuration_changed`; sin base única, faltantes vacíos,
  segmentos históricos y fecha próxima null.
- Sin base: `no_basis`; no genera cero ni un intervalo inventado.
- Base completa antes del límite: `pending/pending_incorporation` con fecha próxima.
- Base completa y elegible: `incorporated`, enlazada al nuevo registro/actualización.

Al aceptar parciales nuevas, reevaluar intervalos observados afectados con reglas 001.
Los incompletos pueden completarse con aportes tardíos, incluidos aquellos cuya evidencia
se conserva después de retirar payload. Los pendientes protegen sus referencias necesarias.
El trabajo interno recupera solicitudes sin candidato y candidatos pendientes al iniciar,
selecciona sin invertir el orden de locks y luego
revalida todos los candidatos de CAT-01 bajo coordinación. Publica los completos elegibles
en una actualización, sin consumir quince minutos por cada intervalo del backlog.
Una ejecución repetida no crea otra contribución ni avanza el plazo con duplicados.
Ningún GET ni reinicio por sí mismo constituye una incorporación.

## ConsumptionAggregate y AggregateContribution

`ConsumptionAggregate`: `id`, `building_id`, `category_id`,
`granularity: hour|day|month|year`, `start/end` UTC, `timezone`, offsets de ambos límites,
`tzdata_version`, `energy_quanta` exacto, `covered_duration_us`,
`contribution_count`, `created_at`, `last_new_data_at`, `revision`,
`retain_until` y referencias de procedencia/base. UNIQUE edificio/categoría/granularidad/
zona/start/end. Solo se crea al incorporar la primera contribución, no por una consulta.

`AggregateContribution`: `aggregate_id`, `record_id`, revisión y snapshot de aporte
(energía, intervalo, modo/base/revisiones), `incorporated_at`.
UNIQUE `(aggregate_id,record_id)`. Aporte y contador cambian solo con registros nuevos.
Mantener índice de intervalos del registro auxiliar para reconstruir advertencias por
cruces y huecos aun después de retirada.

Para bloque B e incorporados incluidos I:

```text
I(B) = {r de la misma categoría | B.start <= r.start < r.end <= B.end}
energy_quanta(B) = sum(r.energy_quanta para r en I(B))
duration_us(B) = microsegundos(B.end_UTC - B.start_UTC)
covered_us(B) = duración de unión de [r.start,r.end) para r en I(B)
coverage_percent(B) = 100 * covered_us(B) / duration_us(B)
```

La exclusión de superposiciones permite sumar duraciones sin doble conteo. Un cero
válido aporta duración; sin contribuciones, energía null, duración cubierta cero.
Con contribuciones, energía puede ser exactamente cero. Nunca usar agregados de
otros niveles o categorías como contribuciones: una lectura cruzada de hora puede
ser válida para día, y CAT-01 no vuelve a sumar sus parciales.

Acumular coeficientes con enteros exactos; reconstruir Decimal desde dígitos/escala,
sin redondeo por contexto. NUMERIC sin escala coercitiva e índices usan los límites
verificados de PostgreSQL. Los bloques tienen duración positiva y los registros
resolución mínima técnica de un microsegundo, no quince minutos.

Cada incorporación modifica sincrónicamente los cuatro agregados donde esté totalmente
contenida. Si cruza un límite, se excluye solo de esa granularidad con aviso. Un bloque
sin aporte se proyecta al consultar, sin fila durable ni plazo ficticio.

## Proyecciones de consulta, calendario y estados

`AggregateQueryResult` se define en [HTTP](contracts/http.md). Enumera bloques completos
dentro del filtro, incluso sin datos, ordenados por inicio UTC; incluye filtro/corte,
procedencia histórica, avisos y motivos de exclusión de extremos. Las dos dimensiones:

| Dimensión | Regla |
| --- | --- |
| `temporal_state: not_started|ongoing|finished` | `not_started` si `cutoff_at < start`; `ongoing` si `start <= cutoff_at < end`; `finished` si `cutoff_at >= end`. |
| `coverage_state: complete|incomplete|no_data` | Comparar exactamente `covered_us` con duración: igualdad, entre cero y total, o cero. |

Clasificar antes de redondear porcentaje. Se transmite porcentaje con hasta seis
decimales, junto con duraciones exactas; un porcentaje mostrado como 100 no permite
etiquetar completo si falta un microsegundo.
Los bloques futuros totalmente contenidos se mantienen en el filtro y ambas vistas.
Un bloque futuro sin contribuciones tiene energía null y cobertura cero; su estado
temporal es `not_started`. No inferir cobertura de la clasificación temporal.

Horas: límites locales/offsets reales; hora repetida en dos bloques, inexistente omitida,
transiciones de otra duración explícitas. Día/mes/año por calendario local, resolviendo
límites inexistentes al primer instante válido. No bloques de 24 h/30 d/365 d fijos.
Persistir límites y zona; cambios de tzdata no reinterpretan silenciosamente agregados
ya creados. Una actualización de tzdata que altere historia requiere reconciliación
explícita antes de crear claves incompatibles, manteniendo valores y plazos.

GET no crea filas, acepta datos, evalúa CAT-01 ni extiende conservación.
La lectura compuesta comparte captura REPEATABLE READ y corte 009. El consumidor
conserva su snapshot si requiere reproducción posterior; una fecha sola no basta.

## Plazos y retirada permitida

| Registro | Inicio de mínimo | Límite |
| --- | --- | --- |
| Medición física | Primera aceptación de plataforma | Aniversario local +12 meses mediante 009. |
| Total calculado con base/referencias | Primera incorporación | Mismo helper; no recepción física ficticia. |
| Agregado | Primera contribución o última incorporación nueva, la posterior | Aniversario +12 meses; `retain_until` nunca disminuye. |
| Resultados/diagnósticos/evidencia | Registro o revisión sustantiva | Mínimo común 009 y extensión por dependientes protegidos. |

El aniversario usa último día válido si falta el día, primer instante válido posterior
si hay hueco y ocurrencia posterior si se repite. Guardar zona/límite evaluado; nueva
tzdata no lo adelanta. Lecturas/rechazos/duplicados no alteran fechas.

No hay purga automática obligatoria. `Retention.withdraw_detail` es operación interna:
bajo coordinación y UoW, comprueba `now>=retain_until` y todos los dependientes; si hay
protección, rechaza sin cambios; si puede retirar, elimina solo payload/evidencia
prescindible y registra fecha/motivo. Conserva registro auxiliar, aportes, base/procedencia,
exclusiones, estados de recepción y máximos históricos. El agregado protegido conserva
su valor/cobertura/revisión por la retirada; una incorporación tardía suma solo aportes
nuevos y extiende su plazo. El detalle retirado se identifica como tal, sin prometer
que aún existe ni degradar la cobertura histórica del agregado.
