# Contratos internos: recepción, historial y conservación

[Modelo](../data-model.md), [HTTP](http.md), [plan](../plan.md),
[propiedad](../../../docs/implementation-roadmap.md).
Todos los puertos son llamadas dentro del monolito. Son diseño, no proveedores ya instalados.
Los objetos comunes viven en `backend/src/ecs_ec/consumption/ports.py`; los puertos
no importan implementaciones concretas ni notificaciones.

## Dependencias de 002

| Proveedor | Contrato consumido / garantía |
| --- | --- |
| 009 `core` | UoW asíncrona, reloj UTC/monotónico inyectable y helper de aniversario; plataforma compone rutas/lifespan. |
| 001 configuración | Catálogo fijo, contexto con zona IANA, revisiones/segmentos y fuentes; coordinación común con recepción. |
| 001 `MeasurementValidator.normalize` | Validación pura por registro/segmentos, conversión exacta y revisión de categoría; sin escritura. |
| 001 `TotalCalculator.evaluate` | Candidato histórico alineado de CAT-01, completo/incompleto/sin base; sin publicar ni alterar reloj. |
| 006 identidad | Permisos actuales del principal para lecturas web/consumidores; no se crea identidad propia. |
| 003 adaptador | Publicación lógica completa, identidades nativas/origen, intervalos inequívocos y correlación confiable. |
| 009 `audit` | Resultado, auditoría y eventos en la misma UoW del productor. |
| 007 emisor | Señales saneadas cuando exista su capacidad; sin condicionar operación a visores. |

## Reception.accept — productor interno

Implementación prevista: `backend/src/ecs_ec/consumption/reception.py`.
Entrada: `attempt_id`, `building_id`, `publication_ref`, proceso de integración autorizado,
registros con posición estable y referencias nativas, `correlation_ref` generada internamente.
El adaptador entrega consumos por intervalo, no un contador acumulado sin transformar.
003 conserva sus formatos PAS600/CSV/JSON y credenciales; no los redefine 002.
No hay POST público de mediciones ni endpoint de reloj/fixtures.

Salida `ReceptionOutcome`: intento/correlación, fechas de evaluación, resultado por
posición y actualización por categoría, aceptación durable y próxima admisible donde
corresponda. Estados por registro `accepted|duplicate|rejected`; causas saneadas, incluidas
`too_early`, `conflicting_duplicate`, `overlapping_interval`,
`source_configuration_changed` y `energy_out_of_supported_range`.
Se conserva el vocabulario de validación 001 para las restantes causas.

### Identidad y recuperación del intento

```text
Reception.accept(
  attempt_id, building_id, publication_ref,
  process, records, correlation_ref
) -> ReceptionOutcome

Reception.read_attempt(
  attempt_id, building_id, process
) -> AttemptLookup
```

Son puertos internos de `backend/src/ecs_ec/consumption/ports.py`, implementados por002;
003 y los fixtures internos son adaptadores confiables, no clientes HTTP públicos.
El adaptador genera y persiste `attempt_id` UUID y la entrada ordenada antes de llamar002.
La primera llamada crea el intento y fija su entrada; `ReceptionOutcome.attempt_id`
conserva ese mismo UUID. Si ya existe, comparar la entrada canónica completa, no solo
su digest: edificio, publicación, correlación y registros ordenados con posiciones,
valores/unidades, intervalos, fuentes y referencias de evidencia. Tokens de autorización
y fechas de invocación no forman parte de esa entrada inmutable.

- Igual ID e igual entrada: recuperar resultados confirmados y continuar únicamente
  categorías o posiciones sin resultado durable. No convertir un `accepted` original
  en `duplicate`, repetir eventos/aportes ni reevaluar un rechazo ya confirmado.
- Intento `completed`: devolver su resultado original sin nuevas incorporaciones ni
  extender plazos. Esto incluye rechazos `too_early`, aunque ahora haya transcurrido900s.
- Igual ID con entrada distinta: error `attempt_payload_conflict`, sin cambiar entrada,
  resultados ni reloj de incorporación. El mismo UUID tampoco puede reutilizarse para
  otro edificio, publicación o contexto autorizado.
- Un reenvío explícito crea otro `attempt_id` aun con igual `publication_ref`; permite
  evaluar nuevamente novedades antes rechazadas. Recuperar un intento inconcluso no
  equivale a ese reenvío.
- Coordinar exclusivamente cada intento ante dos ejecutores: uno procesa y el otro
  espera o consulta sus resultados; una caída permite recuperar la coordinación.
  No esperar al coordinador de intento manteniendo locks de contexto/categorías.
  Las UoW de escritura conservan después el orden común y la atomicidad por categoría.

`AttemptLookup` contiene `attempt_id`, `building_id`, `state`:
`not_found|processing|completed|partial_failure`, y `outcome: ReceptionOutcome|null`.
`not_found` lleva outcome null y solo resulta de una lectura autorizada satisfactoria
sin ese intento. Los demás estados incluyen únicamente resultados durables observados
en una captura coherente; `processing`/`partial_failure` identifican además las posiciones
aún sin resultado y no afirman que el intento esté completo. `read_attempt` es lectura:
no crea intentos, incorpora datos, reanuda trabajo ni modifica plazos. Fallo de DB o
autorización es error explícito, nunca `not_found` ni una respuesta vacía de éxito.

Después de perder una respuesta, el adaptador consulta `read_attempt` y, si necesita
crear o continuar trabajo, repite `accept` con el mismo ID y entrada congelada.
El control de concurrencia también protege la carrera entre esa consulta y la llamada.

### Procesamiento de la entrada fijada

1. Reunir fragmentos de una publicación lógica antes de aceptar. Separar referencia de
   publicación de identidad interna del intento: el reenvío de una publicación rechazada
   a 14m59s debe poder incorporarse desde 15m.
2. Procesar categorías con UoW independientes READ COMMITTED. Bloquear contexto/
   configuración → categorías afectadas ordenadas → candidatos/registros/agregados.
   La breve serialización de contexto no impone un intervalo global al edificio.
3. Tras bloquear, leer configuración histórica/estado y reloj actual. No usar instante
   de inicio de una transacción que esperó, reloj de fuente ni hora local sin offset.
4. Normalizar cada registro con 001. Resolver todo `[start,end)`, permitiendo revisión
   global ajena si `category_revision` sigue estable. No descartar válidos independientes.
5. Comparar con registro auxiliar durable y registros anteriores del lote en orden estable:
   duplicado equivalente, conflicto o superposición. El primero válido conserva original.
   Solo novedades válidas/no superpuestas pasan al límite de categoría.
6. Si la categoría no es elegible, rechazar sus novedades `too_early` e informar instante
   UTC/fecha local de próxima aceptación. Duplicados conservan clasificación; ninguna
   de estas respuestas reinicia el reloj. No guardar novedades físicas anticipadas para
   incorporación automática posterior: la fuente debe reenviarlas.
7. Si es elegible, incorporar todas las novedades válidas de esa categoría como una
   actualización; confirmar payload, registro auxiliar, estado, máximos históricos,
   aportes/agregados, resultados, eventos y solicitudes `TotalEvaluationRequest` de
   intervalos parciales nuevos que puedan afectar CAT-01 calculada juntos. Crear o
   reactivar solicitudes `pending` es parte de este commit, aun sin candidato; duplicados
   y rechazos no las generan. La siguiente consulta iniciada
   después de su commit ve esos agregados, sin esperar trabajo eventual.
8. Evaluar candidatos CAT-01 afectados usando evidencias ya confirmadas y reglas 001;
   completar/incorporar en UoW coordinada CAT-01 o guardar diagnóstico/pendiente.
   Marcar procesada la solicitud en esa misma UoW, nunca antes de persistir su resultado.
   Los parciales no se revierten si CAT-01 aún no es elegible. La respuesta no afirma
   total calculado incorporado mientras solo sea candidato.
9. Completar resumen del intento desde resultados durables. Fallos parciales permiten
   reintentar sin duplicar categorías ya confirmadas; caída DB nunca acredita commit.

Una violación funcional recuperable usa savepoint creado después de bloqueos; un fallo
de infraestructura revierte toda la categoría. No se devuelve aceptación antes del commit.
Errores funcionales de una categoría no cancelan las demás; una caída general de DB
se comunica como indisponibilidad y conserva únicamente los resultados ya confirmados.

## PendingTotals.run_due — trabajo propio 002

`pending_totals.py` registra trabajo cancelable en el `lifespan` común 009.
Consulta solicitudes `pending` incluso sin candidato y candidatos pendientes de
incorporación, al arrancar y periódicamente, sin invertir bloqueos. Adquiere contexto →
categorías ordenadas → solicitudes/candidatos y revalida configuración histórica,
referencias, completitud y elegibilidad CAT-01 con las contribuciones confirmadas.
Agrupa los candidatos completos admisibles en una actualización; primera incorporación
inicia protección y avanza solo el estado CAT-01. Recupera pendientes al iniciar y tras
fallo/reintento. Estado y unicidad PostgreSQL protegen aun con dos ejecuciones concurrentes.
Guardar candidato/diagnóstico/total y marcar solicitud `processed` es atómico; un fallo
revierte ambos y conserva trabajo pendiente. Si el límite impide incorporar, primero
guardar el candidato pendiente. La coordinación compartida con recepción impide perder
novedades durante el procesamiento: quedan incluidas o reactivan la solicitud después.
Una caída entre commit de parciales y creación de candidato se recupera sin reenvío;
duplicados/reintentos no duplican aportes, totales ni eventos. GET no procesa solicitudes.

Un candidato calculado pendiente parte de contribuciones aceptadas; difiere de un envío
físico anticipado rechazado. GET no ejecuta este trabajo ni publica valores.
Sin medidor total y base vacía no hay total; con medidor total no se generan sustituciones.
Los diagnósticos de falta, cambio de firma y espera conservan sus reglas/campos 001.

## Proveedores de almacenamiento para 001

Todos reciben edificio/categoría/período/corte y UoW del llamador donde corresponda.
La [integración 001](../../001-visualizar-consumo-categorias/contracts/integrations.md)
es el contrato de dominio que se implementa aquí:

| Puerto / `store.py` | Salida / límite |
| --- | --- |
| `MeasurementStore.read_detail` | Payloads incorporados y aún conservados, completamente contenidos; diagnósticos, revisiones, cruces y retiradas identificadas; sin crear CAT-01 ni reconstruir detalle retirado. |
| `MeasurementStore.read_extent` | Mínimo inicio/máximo fin de payloads conservados del edificio; ausencia explícita. No sustituir por extensión de una sola categoría. |
| `MeasurementStore.read_update_state` | Última incorporación nueva/próxima admisible independiente por categoría; incluye CAT-01 calculada. |
| `MeasurementStore.read_reconfiguration_bounds` | Historia permanente y máximo fin incorporado por cada categoría solicitada, aun tras retirada. |

`read_reconfiguration_bounds(building_id,category_ids,unit_of_work)` devuelve
`{has_accepted_history: bool, latest_interval_end_by_category: {category_id: instant|null}}`
con exactamente una clave por categoría solicitada. Null significa nunca incorporada;
ausencia/fallo/clave faltante impide modificar configuración, sin interpretar historia vacía.
Se lee con READ COMMITTED, tras bloqueos comunes, dentro de la misma UoW de escritura 001.
Probar recepción/cambio en ambos órdenes, zona inmutable tras primera incorporación,
historia calculada y estado después de retirar payload.

001 compone `Consumption.source_status` y `Consumption.query_detail` usando estos
proveedores. 002 no cambia nombres/categorías, cálculo puro, permisos ni configuración.

## Lecturas agrupadas y consumidores

`Consumption.query_aggregates` (002) recibe selección validada, principal autorizado y
UoW opcional; produce [AggregateQueryResult](http.md). Usa captura REPEATABLE READ y
corte 009 coherentes con configuración/recepciones/revisiones. Copiar resultado y
liberar transacción antes de renderizar, generar PDF o hacer comunicaciones externas.
No usar cache de otra revisión tras una incorporación confirmada.

| Puerto | Entrada y salida |
| --- | --- |
| `Consumption.latest_admissible_window` | Categoría, resolución, zona de regla, activación, cursor, corte/UoW. Última ventana completa y terminada disponible, o motivo no evaluable; evidencia y revisión estable. |
| `Consumption.read_general_snapshot` | Edificio, ciclo, corte/UoW: detalle CAT-01 física asociada al suministro, energía exacta, procedencia/revisión/cobertura; calculada = limitación explícita. |
| `Consumption.read_demand_history` | Suministro, meses/ventanas punta, corte/UoW: intervalos físicos exactos y resolución demostrable o potencia integrada válida si la fuente real la provee; nunca inventar desde hora/día. |
| `Consumption.read_report_snapshot` | 001 compone catálogo/procedencia con detalle/agregados 002 conservados, selección/corte/UoW: siete categorías, límites/offsets, origen/base/alcance, valores/cobertura/referencias/revisiones. |

### Última ventana admisible para 008

Resolución `intervalo` selecciona un intervalo incorporado de la serie con resolución
demostrada, nunca presupone quince minutos por la frecuencia de recepción. Hora/día/mes/
año requieren límites reales de la zona solicitada. Con zona del edificio usa agregados
canónicos; con otra zona genera proyección no persistida directamente desde la evidencia
de registros incorporados, aplicando contención/cobertura idénticas. No sumar buckets
del edificio para aparentar una ventana de otra zona. No cambia conservación al leer.

Ventanas ordenadas por fin/inicio UTC e identidad; seleccionar la última admisible que
no preceda a activación según la ventana de evaluación de 008. Cursor opaco versionado
identifica categoría/resolución/zona, ventana y revisión de evidencia. Misma ventana sin
nuevos aportes conserva revisión; datos tardíos cambian revisión y permiten reevaluación.
Un cursor de otra selección es inválido, no se ignora. La proyección de otra zona
identifica revisión mediante conjunto ordenado de IDs/revisiones contribuyentes y
configuración histórica, además de límites/tzdata.

`AdmissibleWindow`: `status: available|not_evaluable`, selección/corte, límites, kWh nullable,
cobertura/duraciones, origen/base/segmentos, referencias/revisión/cursor y `reason_code|null`.
`available` exige ventana terminada, fuente válida, al menos una contribución y cobertura
exactamente completa. No escalar incompletos ni sustituir CAT-01 medida por suma.
Motivos: `no_source`, `no_complete_window`, `insufficient_resolution`,
`insufficient_evidence`. Fallo de DB es error, no consumo cero ni cobertura conocida.

Los puertos satisfacen a [004](../../004-costos-tarifa-bt43/contracts/integrations.md),
[005](../../005-generar-reportes-pdf/contracts/integrations.md) y
[008](../../008-notificaciones-programables/contracts/integrations.md) sin implementar
sus negocios. Costos no recibe una CAT-01 calculada como medidor general. Reportes y
notificaciones no vuelven a sumar parciales al total.

El corte limita lo visible en una captura, pero no promete reproducción histórica
arbitraria por fecha. Quien necesite reproducir conserva snapshot y referencias.

## Retention.withdraw_detail

Entrada interna: registros, proceso autorizado de mantenimiento, reloj/UoW y motivo.
Previsualización permite revisar elegibilidad; ejecución revalida tras bloqueos comunes.
No endpoint humano nuevo ni servicio de purga externo.
Rechaza retiro protegido o con dependiente que requiera original; registra resultado
saneado. Al retirar payload vencido preserva ledger/aportes/máximos/configuración
necesarios y no revisa ni reduce el agregado por esa sola retirada.
Un reenvío posterior sigue siendo duplicado o conflicto y no reactiva el detalle ni el
plazo automáticamente. Un dato tardío distinto y no superpuesto puede incorporarse
desde la elegibilidad, sumar solo una vez y extender el agregado.

## Eventos y auditoría 009

Usar [EventWriter/FunctionalAudit](../../009-fundaciones-plataforma/contracts/integrations.md)
en UoW del productor; IDs y correlación internos, sobre y cargas tipadas, sin cuerpos/secretos.

| Productor | Tipo / entidad / semántica |
| --- | --- |
| Incorporación física o calculada | `consumption.accepted` por `CategoryUpdate`/revisión; `accepted_new_data=true`, categoría, clase de origen, referencias y ventanas afectadas. |
| Resultado de actualización física evaluada | `reception.completed` por resultado de categoría/intento y revisión; acepta también duplicados/rechazos, con conteos y causas; `accepted_new_data` refleja solo novedades confirmadas. |
| Retirada/mantenimiento | Auditoría de proceso, referencias/resultado; sin inventar otro tipo común de evento no registrado. |

Si una actualización contiene intervalos disjuntos, el sobre `measurement_window` expresa
la envolvente y la carga conserva sus ventanas/referencias exactas; no afirma que los
huecos estén cubiertos. El instante del evento no sustituye al intervalo medido.
Deduplicar módulo/entidad/revisión/tipo. El resumen del intento no duplica eventos ya
confirmados por categoría; `FunctionalSummary` cuenta publicaciones/actualizaciones
según tipo explícito, sin mezclar ambos como si fueran recepciones distintas.

002 aporta evidencia funcional de recepción/calidad al mecanismo común: inicio de registro,
períodos íntegros/huecos, conteo observado o null y limitaciones. No deriva integridad de
logs/heartbeat. Instrumentación 007 mide operaciones/errores/esperas/reintentos de forma
saneada; caída de visores/SMTP no revierte cambios ni impide consultas.
