# Modelo de datos: Consumo eléctrico por categorías

Diseño de [spec-001](spec.md), alineado con la [arquitectura](../../docs/architecture.md).
UUID de aplicación, revisiones enteras positivas, instantes UTC `timestamptz`, precisión
temporal hasta microsegundos y valores de energía Decimal/NUMERIC sin redondeo impuesto.
Las interfaces HTTP transmiten energía como cadena decimal y fechas con offset.

## Propiedad y persistencia

| Entidad | Propietario | Persistencia / relaciones |
| --- | --- | --- |
| BuildingContext, ConsumptionCategory | 001 | Edificio único y catálogo fijo; no módulo multiedificio. |
| InstallationRevision, CategorySource, MeasurementSource | 001 | Revisiones inmutables, siete estados por revisión y orígenes estables. |
| ValidatedMeasurement, TotalCandidate | Semántica 001 | Objetos de dominio; no aceptación ni escritura por sí mismos. |
| AcceptedMeasurement, IncorporatedTotal, ReceptionResult | 002, reutiliza dominio 001 | Tablas únicas de mediciones/totales y recepción; conservar fechas, deduplicación y referencias. |
| DetailQueryResult, SourceStatus | Fachada 001 sobre lecturas 002 | Proyecciones de lectura, sin tablas duplicadas. |
| Aggregate, retención, cobertura histórica | 002 | Fuera de las migraciones de 001; contrato en [spec-002](../002-registro-retencion-consumo/spec.md). |

Las migraciones de 001 solo crean catálogo/contexto/fuentes/configuración y se enlazan al
head real. No reservar una revisión global ni crear las tablas de recepción de 002.
Referencias históricas se protegen contra eliminación en cascada.

## BuildingContext y ConsumptionCategory

`BuildingContext`: `id: UUID`, `name: str`, `timezone: IANA`, `created_at: instant`.
Se inicializa mediante configuración local/producción documentada antes de recibir datos;
la zona es obligatoria. `America/Santiago` es un fixture, no la zona confirmada del edificio.

`ConsumptionCategory`: `id: CAT-01..CAT-07`, `name`, `scope`, `display_order: 1..7`.
Siete registros fijos con los nombres y alcances de [FR-001](spec.md#functional-requirements).
No se eliminan ni renombran mediante configuración. HVAC/ACS es una serie; sanitario mide
energía eléctrica. Todas las categorías permanecen seleccionables.

## MeasurementSource, InstallationRevision y CategorySource

`MeasurementSource`: `id: UUID`, `building_id`, `label`, `created_at`. Identifica un origen
consolidado; no equivale al publicador PAS600. Su correspondencia nativa y credenciales
pertenecen a 003 y no aparecen en el contrato web. Una identidad de origen no se reutiliza
para otro medidor; se conserva aunque deje de estar activa.

`InstallationRevision`: `id: UUID`, `building_id`, `revision: int`, `effective_from`,
`recorded_at`, `created_by` (actor de 006 o proceso confiable de preparación), `timezone`.
`effective_until` se obtiene de la siguiente revisión, sin mutar la revisión anterior.

`CategorySource`: `installation_revision_id`, `category_id`, `has_meter: bool`,
`source_id: UUID|null`, `category_revision: int`. Siete entradas únicas por revisión. Con medidor, origen obligatorio
y único dentro de la revisión; sin medidor, `source_id=null`. La etiqueta del origen se
registra/valida junto a su identidad al configurar. No se aceptan medidas físicas para
una categoría no instalada durante todo el intervalo.

`category_revision` es positiva, monotónica e inmutable por edificio/categoría. La primera
configuración asigna 1 a cada categoría. Una parcial incrementa su revisión solo si cambia
`has_meter` o `source_id`; una etiqueta descriptiva o un cambio ajeno conserva su revisión.
Volver a una fuente anterior crea otra revisión, sin reutilizar la antigua. Su vigencia
termina en la siguiente revisión **de esa categoría**, no en la siguiente revisión global.

La base de CAT-01 es el conjunto ordenado de CAT-02..07 con `has_meter=true` de esa revisión:

- CAT-01 con medidor: modo `measured`, su propia fuente; no suma ni sustitución de huecos.
- CAT-01 sin medidor, base no vacía: modo `calculated`, fuente lógica, contribuciones de toda la base.
- CAT-01 sin medidor, base vacía: modo `unavailable`; no valor cero ni medidor ficticio.
- Categoría parcial sin medidor: modo `unavailable`, etiqueta "Sin medidor".

La firma de revisión CAT-01 es modo/fuente propia si es medida; modo y pares ordenados
`(category_id, source_id)` de la base si es calculada; modo sin base si no está disponible.
Un cambio de parcial no modifica la revisión CAT-01 física. Un cambio de base o fuente
contribuyente sí modifica la revisión CAT-01 calculada. Los cambios se determinan en
servidor; el cliente nunca asigna `category_revision`.

La primera configuración puede declarar vigencia anterior a la importación inicial.
Cada revisión posterior exige `expected_revision` vigente y entra en vigor al aplicar
el cambio con reloj de plataforma, sin retroactividad ni programación. Ese instante debe
ser igual o posterior al fin más reciente de registros aceptados de las categorías cuya
firma cambia, incluyendo CAT-01 cuando cambie su firma derivada. El registro tardío se
valida contra toda la vigencia de su categoría durante `[start,end)`, no contra la
configuración actual al recibirlo. Puede atravesar revisiones globales si conserva una
única `category_revision`; cruzar un cambio de su propia presencia/fuente se rechaza con
`source_configuration_changed`, sin dividirlo ni afectar datos aceptados. Un cambio que
coincide con `end` no está dentro del intervalo; en `start` aplica la nueva revisión.

Para revisar configuración, usar `MeasurementStore.read_reconfiguration_bounds` de 002
en la misma UoW de escritura, después de bloquear contexto/configuración y categorías
en orden estable, con READ COMMITTED para leer el estado vigente después de esos bloqueos.
Su respuesta contiene `has_accepted_history: bool` y
`latest_interval_end_by_category: {category_id: instant|null}` para todas las categorías
solicitadas. Incluye mediciones físicas y totales incorporados, conserva límites después
de retirar detalle y mantiene `has_accepted_history=true` tras la primera incorporación.
Un null significa que nunca hubo incorporación en esa categoría; proveedor ausente,
fallo o respuesta sin una clave solicitada es error, nunca historia vacía. No cambiar zona
si existe historia aceptada. Primera configuración sin revisiones previas puede prepararse
antes de 002 porque no puede existir una medición aceptada sin configuración; una revisión
posterior con cambios requiere su proveedor real. Un no-op conserva revisión/vigencia.

Las consultas que abarcan revisiones devuelven segmentos de configuración y procedencia
por fila. No recalculan historia con la base actual. Permitir todo sin medidor es válido.

Implementación interna 001: `ConfigurationSegment.basis_category_revisions` conserva las
revisiones de las parciales en orden de base, necesarias para validar contribuciones.
Se resuelve desde InstallationRevision, se excluye del JSON HTTP y no amplía BasisSource
público. Evaluar un segmento web reconstruido exige rehidratar esa evidencia desde historia.

## ValidatedMeasurement y AcceptedMeasurement

| Campo | Tipo / significado |
| --- | --- |
| `building_id`, `category_id`, `source_id` | Contexto y fuente conocida de la revisión aplicable. |
| `start`, `end` | Instantes inequívocos; `start < end`; intervalo `[start,end)`. |
| `original_value`, `original_unit` | Decimal original y unidad exacta `Wh|kWh|MWh`; conservar representación de origen en evidencia. |
| `energy_kwh` | Decimal finito; `0 <= E < 10^30 kWh`, múltiplo exacto de `10^-15 kWh`. Wh × 0.001, kWh × 1, MWh × 1000. |
| `configuration_revision` | Revisión global vigente en `start`; referencia histórica inmutable, no límite de validez por sí misma. |
| `category_revision` | Revisión positiva de fuente de la categoría, única durante todo `[start,end)`; inmutable. |
| `source_evidence_ref`, `correlation_ref` | Referencias opacas a origen/recepción; sin cuerpos ni secretos web. |
| `id`, `revision`, `first_accepted_at` | Asignados por 002 al incorporar; no provienen de fechas declaradas por la fuente. |

Rechazar booleanos, tipos no numéricos, negativos, NaN/infinito, unidad incompatible,
origen/categoría desconocidos, fechas incompletas/sin offset, precisión temporal superior
a microsegundos sin equivalencia exacta e intervalos nulos/invertidos. El dominio técnico
individual se valida **después de convertir a kWh**, con independencia de la unidad original:
`E` debe estar en `[0,10^30)` y ser múltiplo de `q=10^-15`. Fuera de ese dominio se rechaza
con `energy_out_of_supported_range`; no es un umbral físico del edificio. El máximo válido
es `M=10^30-10^-15`; el mínimo positivo es `q`. Ceros finales o notación exponencial no
alteran la admisibilidad; normalizar exactamente su representación sin redondear y
conservar la representación original en evidencia. Wh `10^-12`, kWh `10^-15` y MWh `10^-18`
son equivalentes y válidos. `10^-16 kWh`, valores no múltiplos de q y `10^30 kWh` se rechazan.

Construir Decimal desde texto y usar contexto de precisión 50 con detección de `Inexact`,
`Rounded`, operaciones inválidas y mezcla con float para conversiones y suma CAT-01.
Canonicalizar ceros insignificantes antes de operar, sin pasar valores de negocio por float.
NUMERIC sin escala coercitiva conserva originales y resultados exactos. Una medición
normalizada necesita como máximo 30 dígitos enteros y 15 fraccionarios; el total de seis
máximos necesita hasta 31 y 15 respectivamente. Esa precisión no establece el contexto
de agregaciones horarias/diarias/mensuales/anuales de 002, que deben dimensionar su suma.

Identidad de reenvío: edificio + origen + categoría + inicio + fin UTC. Con energía kWh
equivalente es duplicado, incluso `1000 Wh` frente a `1 kWh`; conservar el primer original.
Misma identidad con energía distinta es conflicto. Un intervalo distinto que se superpone
en la misma categoría es rechazo incluso tras cambiar de fuente; contigüidad es válida.
Aplicar estas reglas también entre registros del mismo envío. 002 protege unicidad y
exclusión en transacción, no solo mediante consultas previas.

## TotalCandidate e IncorporatedTotal

`TotalCandidate`: `building_id`, `category_id=CAT-01`, `start/end`,
`configuration_revision`, `category_revision: int|null`, `base_categories`, `contributions`,
`energy_kwh|null`, `status: complete|incomplete|no_basis`, `missing_categories`,
`reason_code|null`, `configuration_segments`.

Cada contribución contiene `measurement_id`, `measurement_revision`, `category_id`,
`source_id`, `category_revision`, `energy_kwh`, `start/end`. Una por cada categoría de la base y ninguna CAT-01.
Para base no vacía P e intervalo I:

`T(I) = sum(E(c,I) en kWh, c en P)` únicamente si la firma CAT-01 permanece estable en I
y toda c tiene una lectura válida que cubre **exactamente** I. No sumar dos subintervalos para simular esa contribución, ni
prorratear/interpolar intervalos desalineados. La unión de intervalos observados en las
categorías de la base identifica candidatos; faltantes/alineación insuficiente producen
diagnósticos sin valor numérico. Sin ninguna lectura no se inventa un intervalo candidato.

Si cambia la firma calculada dentro de I, el candidato queda `incomplete`, con
`reason_code=calculation_configuration_changed`, `category_revision=null`, sin valor ni
base única fingida (`base_categories=[]`, `contributions=[]`, `missing_categories=[]`).
Sus `configuration_segments` conservan modo/base/fuentes y revisiones de cada segmento.
Las parciales aceptadas siguen disponibles. Un cambio global con la misma firma CAT-01
no invalida el cálculo. Los otros motivos son `missing_contributions` y, tras orquestación
002, `pending_incorporation`; no se confunden cambio de configuración, faltantes y espera.

`IncorporatedTotal` añade `id`, `revision`, `first_incorporated_at`, referencias y snapshot
de base/contribuciones, persistidos por 002. Solo un candidato completo incorporado puede
ser fila numérica de detalle; cero exige base no vacía y todas las lecturas cero.
Su dominio derivado es `0 <= T <= 6*M`, múltiplo de q; el máximo `6*(10^30-10^-15)` es
inclusivo. No aplicar a un total calculado el máximo individual `E < 10^30`. La suma de
las contribuciones exactas, no la mera pertenencia al dominio, determina su valor.

Transiciones coordinadas por 002:

1. Candidato sin toda la base → incompleto, sin fila numérica.
2. Base completa y elegible → incorporado; misma actualización conserva resultado/evento.
3. Base completa antes de elegibilidad CAT-01 → pendiente hasta `next_admissible_at`;
   diagnóstico `pending_incorporation`, sin publicar un valor anticipado.
4. Trabajo interno de 002 revalida/reintenta al vencimiento y tras reinicio; no requiere GET
   ni worker externo. Reenvíos/consultas no reinician plazos ni crean otra contribución.

Los diagnósticos pendientes se distinguen de `missing_contributions` y de
`calculation_configuration_changed`; la UI puede mostrar
"Datos incompletos: total pendiente de incorporación" sin afirmar lecturas faltantes.
Con medidor total no se generan candidatos de sustitución.

## ReceptionResult y SourceStatus

Recepción (002): por posición/identidad de entrada, `accepted|duplicate|rejected`,
`reason_code|null`, `measurement_id|null`, `category_id|null`, `next_admissible_at|null`,
`correlation_ref`. Conflicto es rechazo; aceptación mixta conserva registros independientes
válidos. Solo una incorporación nueva avanza la última actualización; duplicados/rechazos
no la avanzan. Persistir resultados y eventos mediante plataforma 009.
Las causas `source_configuration_changed` y `energy_out_of_supported_range` son rechazos
por registro; no se usan como causa de faltantes ficticios ni revierten otros registros válidos.

`SourceStatus`: categoría, corte, revisión global y `category_revision`, presencia física, modo/fuente lógica, base,
última aceptación/incorporación nueva y siguiente admisible. Ausencia configurada no es
silencio temporal y la separación mínima no es una promesa de llegada máxima.

## DetailQueryResult

Una respuesta inmutable: `request_ref`, edificio, categoría, período/zona, `cutoff_at`,
`state`, `source_mode`, `configuration_segments`, `rows`, `diagnostics`, `warnings`.
Cada fila identifica registro/revisión, intervalo con offset del edificio, energía kWh
exacta, `configuration_revision` global de inicio, `category_revision` válida en todo el
intervalo, primera incorporación y procedencia medida o calculada con originales o base.
En HTTP `first_incorporated_at` unifica primera aceptación física o incorporación calculada.

`rows` contiene únicamente registros numéricos incorporados completamente contenidos,
ordenados por inicio/fin UTC e identidad. `diagnostics` identifica candidatos incompletos
o pendientes, incluidos cambios de configuración calculada; no es una lista de filas de energía ficticias. `warnings` incluye cruces
excluidos, huecos observados, base vacía y alcance parcial del total calculado.

Prioridad de estado: `incomplete` si hay diagnósticos del total calculado; en otro caso
`available` si existen filas, `no_meter` si una parcial estuvo sin fuente en todo el período,
o `no_data`. CAT-01 sin base usa `no_data` y aviso `no_calculation_basis`. Puede haber filas
válidas junto con diagnósticos incompletos de otros intervalos. Modo global `mixed` si
coexisten modos distintos entre segmentos; cambios de base/fuente dentro del modo
calculado se identifican por segmentos y revisión, manteniendo `source_mode=calculated`.
El modo de cada fila siempre es inequívoco.

Cada `configuration_segment` identifica `start/end`, revisión global, `category_revision`,
modo, `source_id|null`, `base_categories` y `basis_sources:[{category_id,source_id}]`.
En modo medido tiene fuente propia y base vacía; calculado tiene fuente propia null y
pares de base completos; no disponible tiene fuente/base vacías. Una revisión global
puede dividir segmentos sin cambiar su `category_revision`. Antes de la primera
configuración no se inventan revisiones: catálogo expone `category_revision=null` y
el detalle solo enumera segmentos configurados, indicando el tramo sin configuración.
En diagnóstico de cambio calculado, `configuration_segments` cubre el intervalo y tiene
al menos dos revisiones CAT-01 distintas; `missing_categories=[]`, `next_admissible_at=null`.
Los diagnósticos de faltantes/espera mantienen una revisión de categoría positiva y
sus segmentos: faltantes tiene categorías ausentes y fecha null; espera tiene faltantes
vacíos y próxima admisible explícita.

Período inicial global: mínimo inicio y máximo fin de mediciones aceptadas conservadas del
edificio, no de la categoría seleccionada; si no hay ninguna, día calendario actual de la
zona del edificio entre sus primeros instantes válidos. Cambiar categoría no lo recalcula.
Una consulta no extiende conservación ni produce aceptaciones/eventos de consumo.
