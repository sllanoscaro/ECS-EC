# Contratos internos de consumo

Propiedad según la [hoja de ruta](../../../docs/implementation-roadmap.md).
[Modelo](../data-model.md), [HTTP](http.md). Son llamadas dentro del monolito;
la disponibilidad real se registra en [la evidencia vigente](../validation/increment-2026-11-02.md).

## Dominio 001 y almacenamiento 002

| Puerto | Propietario / entrada | Resultado / garantía |
| --- | --- | --- |
| `MeasurementValidator.normalize` | 001, `validation.py`; registro y segmentos históricos de configuración de su categoría | Medición validada con revisión global de inicio y `category_revision` estable, o causa funcional; conversión exacta al dominio individual, sin escritura. |
| `TotalCalculator.evaluate` | 001, `totals.py`; intervalo, segmentos de configuración CAT-01, referencias de contribuciones | Candidato completo/incompleto/sin base; detectar firma calculada cambiante sin descartar parciales; suma exacta de hasta seis, sin reloj, commit ni importación de recepción. |
| `Reception.accept` | 002, `reception.py`; publicación lógica, proceso autorizado, reloj/UoW | Resultado por registro y actualización por categoría. Validación 001 + duplicado/conflicto/exclusión + 15 minutos, bajo bloqueo. |
| `MeasurementStore.read_detail` | 002; edificio/categoría/período/corte/UoW | Filas incorporadas, diagnósticos, revisiones y cruces; sin recalcular/publicar CAT-01 desde GET. |
| `MeasurementStore.read_extent` | 002; edificio/corte/UoW | Primer inicio/último fin de mediciones conservadas del edificio o ausencia explícita. |
| `MeasurementStore.read_update_state` | 002; categoría/corte/UoW | Última incorporación nueva y próxima admisible; incluye CAT-01 calculada. |
| `MeasurementStore.read_reconfiguration_bounds` | 002; edificio, categorías solicitadas y UoW de escritura ya coordinada | `has_accepted_history` y máximo fin aceptado por categoría, incluso después de retirar detalle; no usar el extent global conservado como sustituto. |
| `Consumption.query_detail` | 001, `queries.py`; selección y principal autorizado | Resultado del modelo/HTTP, mismos datos para gráfico y tabla. |
| `Consumption.source_status` | 001 compone configuración + estado 002; categoría/corte/UoW | Presencia física/lógica, base y revisión; sin inferir medidor por ausencia de lecturas. |

Los contratos/objetos de `consumption/ports.py` no importan implementaciones de 002.
Estado de ejecución 2026-11-02: reglas/configuración 001 disponibles; proveedores 002 aún
ausentes. `Reception` declara la firma de intento y `read_attempt` acordadas en el
[contrato 002](../../002-registro-retencion-consumo/contracts/integrations.md), sin implementarlas.
Para recepción/configuración usar `catalog_storage.lock_configuration` en READ COMMITTED;
para resolver fuentes históricas usar `read_revisions` y `configuration_segments`.
Los segmentos internos calculados incluyen `basis_category_revisions` en orden de base,
para verificar revisiones de las contribuciones; ese campo se excluye de JSON HTTP. Al
reconstruir segmentos desde esa proyección hay que rehidratar esas revisiones desde la
configuración histórica antes de evaluar; el cálculo falla si faltan. No se altera el
contrato público BasisSource. La integración funcional real se verifica en T018 de 001.

002 depende de las reglas puras 001; la composición de plataforma inyecta su almacenamiento
en consultas 001. No existe dependencia de aceptación completa ni llamadas recursivas
entre ambos módulos. Coordinar `models.py`, `ports.py`, registro de rutas y migraciones
secuencialmente. El borrador de 002 deberá actualizar sus rutas al concretar su propio plan.

`read_reconfiguration_bounds(building_id, category_ids, unit_of_work)` devuelve
`{has_accepted_history: bool, latest_interval_end_by_category: {category_id: instant|null}}`.
Debe incluir exactamente una clave por categoría solicitada; null solo significa que
nunca se incorporaron registros en ella. `has_accepted_history` abarca todo el edificio,
es verdadero desde su primera incorporación física o calculada y no se pierde al retirar
detalle. 002 conserva los máximos y ese indicador junto a cada incorporación confirmada;
duplicados/rechazos no los avanzan. El mecanismo/tabla de esos límites es propiedad de 002.

Para cambiar una revisión existente, bloquear contexto/configuración y categorías ordenadas
y llamar al puerto dentro de la misma UoW de escritura. Usar estado actual después de
adquirir bloqueos: esta operación usa READ COMMITTED, no una captura histórica
REPEATABLE READ ni un corte del cliente. Recepción adquiere la misma coordinación antes
de consultar/actualizar los límites; no se permite una escritura sin ese orden común.
Rechazar el cambio si su instante es anterior al máximo de una categoría cuya firma cambia;
incluir CAT-01 si cambia su firma derivada. Impedir cambio de zona con historia aceptada.
Ausencia del proveedor, error o respuesta incompleta impide la modificación, sin interpretar
historia vacía ni guardar revisión/evento parcial. Probar las dos órdenes de la carrera
recepción/cambio y lectura posterior a retirada de detalle. La primera configuración sin
revisiones previas puede crearse antes de 002; después se exige proveedor real para cambios.
Un no-op autorizado y con revisión esperada vigente conserva el estado sin nueva revisión.

### Orden de recepción

1. 003 entrega una publicación completa, con identidades nativas conservadas y correlación
   interna confiable. Agrupar sus fragmentos por actualización lógica, no por archivo.
2. 002 coordina configuración/categorías en orden estable, obtiene reloj de plataforma,
   resuelve todos los segmentos de la categoría durante el intervalo y usa validación 001.
   Una revisión global ajena conserva `category_revision` y no invalida la lectura. Cambiar
   su propia fuente/presencia dentro de `[start,end)` causa `source_configuration_changed`.
   Validar después de conversión el dominio `0 <= E < 10^30`, quantum `10^-15 kWh`;
   fuera de él, `energy_out_of_supported_range`, sin redondear. Registros inválidos no invalidan
   los independientes válidos. Dentro de un lote, procesar en orden de entrada estable;
   el primer registro válido de una identidad se conserva, sus reenvíos se clasifican.
3. Comparar duplicados/conflictos antes de tratarlos como datos nuevos. Solo novedades
   válidas y no superpuestas se someten al límite por categoría; rechazar anticipadas con
   próxima admisible. No reiniciar plazo con duplicados/rechazos ni fechas de medición.
4. Incorporar novedades admitidas y guardar resultados/eventos en la misma UoW válida;
   los fallos de base no se presentan como aceptación durable. Independencia entre categorías.
5. Evaluar candidatos afectados usando `TotalCalculator`; si la firma CAT-01 cambia dentro
   del intervalo, conservar diagnóstico `calculation_configuration_changed` con segmentos
   y sin valor, dejando consultables las parciales válidas. Una revisión global que no
   cambie esa firma no bloquea el total. El dominio calculado admite hasta
   `6*(10^30-10^-15) kWh`, inclusive; nunca aplicar el techo de una medición individual.
   Incorporar CAT-01 solo si cumple
   su propio límite de 002. Persistir pendientes y reevaluarlos al vencimiento/reinicio
   con su trabajo interno. Esta obligación pertenece al diseño/implementación de 002.

No basta bloquear en Python: exclusión/unicidad y bloqueo transaccional de categorías
deben probarse en PostgreSQL. Contigüidad es válida. La incorporación calculada no cuenta
como recepción física ni altera el último instante de sus categorías contribuyentes.

## Frontera PAS600/SFTP (003)

El [perfil de 003](../../003-simulador-pas600-sftp/spec.md) fija firmware/documentación,
CSV/JSON nativos, medidores iEM3150 y publicación SFTP. 001 no redefine esos archivos.
El adaptador resuelve origen/magnitud, conserva referencias nativas y convierte contadores
acumulados a consumos por intervalo solo con evidencia válida de lecturas consecutivas.
Un archivo ilegible es distinto de una transferencia fallida y de un rechazo por registro.

Las pruebas de 001 llaman al mismo `Reception.accept` desde fixtures locales controlados,
con reloj inyectado; no hay POST público de mediciones ni sesión humana para cada envío
automático. SFTP usa su identidad de integración de 003, no perfiles humanos de 006.
El simulador no es requisito de funcionamiento continuo de la plataforma.

## Lecturas coherentes y consumidores

Una lectura compuesta abre/recibe UoW REPEATABLE READ de plataforma; configuración,
recepción y revisiones deben ser visibles en esa captura y no posteriores a `cutoff_at`.
No prometer reproducción histórica arbitraria solo mediante una fecha: el consumidor
que necesite reproducirla conserva su snapshot y referencias. Liberar la transacción
antes de renderizar UI/PDF o efectuar comunicaciones externas.

| Puerto existente | Responsabilidad coordinada | Límite |
| --- | --- | --- |
| `Consumption.latest_admissible_window` | 002 selecciona intervalo/agregado completo, con evidencia/revisión/cobertura; 001 aporta fuente/base. | Compatible con [008](../../008-notificaciones-programables/contracts/integrations.md); sin otra suma CAT-01, parcial = no evaluable. |
| `Consumption.read_general_snapshot` | Lectura 001/002 para [004](../../004-costos-tarifa-bt43/contracts/integrations.md). | Solo CAT-01 física asociada al suministro; calculada devuelve limitación, no sustitución. |
| `Consumption.read_demand_history` | 002 expone detalle físico/ventanas con resolución demostrable; 004 aplica su cálculo de demanda. | No inventar bloques de 15 minutos desde agregados horarios; esta spec no garantiza que existan esos datos. |
| `Consumption.read_report_snapshot` | 001 compone catálogo/procedencia y lecturas/agregados conservados de 002 para [005](../../005-generar-reportes-pdf/contracts/integrations.md). | Siete categorías, base/alcance, calidad/cobertura/revisiones al corte; sin crear agregados ni recalcular costos. |

Estos adaptadores se conectan al incorporar la capacidad propietaria. No obligan a
implementar costos, PDF, agregados o notificaciones en las tareas de 001. La aceptación
de consumidores exige implementaciones reales, no dobles presentados como integración.

## Identidad, eventos y operación

006 proporciona `Identity.authorize(principal, action, building_id)`, sesión/CSRF actuales.
Consulta permitida a Operador/Administrador; configuración solo Administrador, incluidas
lecturas directas. Bootstrap controlado identifica un proceso; no añade cuentas ni un
permiso humano de inyección de mediciones. La configuración y recepción comparten un
orden de bloqueo: contexto/configuración del edificio → categorías por identificador.

La escritura usa el [contrato común 009](../../009-fundaciones-plataforma/contracts/integrations.md):

| Productor | Evento/resultado | Atomicidad |
| --- | --- | --- |
| 001 configuración/fuentes | `source.changed`, `administration.changed` y auditoría de actor/revisión/cambio saneado | Con la revisión de configuración; no cuerpos nativos, secretos ni datos de sesión. |
| 002 incorporación | `consumption.accepted` con `accepted_new_data=true` | Con actualización/medición o total incorporado; distingue calculado y conserva ventana. |
| 002 resultado de recepción | `reception.completed` y clasificación por registro | Con resultado durable; duplicados/rechazos no avanzan última aceptación. |

Deduplicación por módulo/entidad/revisión/tipo; UUID/correlación internos, fechas de registro
distintas del intervalo medido. Sin importar `notifications`, SMTP ni sus modelos.
`FunctionalSummary.read` reutiliza evidencia funcional común, no logs como prueba de cobertura.
007 recibe señales saneadas de validación/consulta/incorporación al existir su emisor;
fallos de visores/correo no revierten commits ni impiden leer consumo. Los procedimientos
local/VPS y evidencia se concretan en [quickstart](../quickstart.md).

## Implementación comprobada de detalle 001 (2026-11-02)

`backend/src/ecs_ec/consumption/queries.py` compone `MeasurementStore` real de 002 y
expone `source_status`, `catalog` y `detail`. Cada captura abre REPEATABLE READ READ ONLY,
con configuración, corte y almacenamiento coherentes. `main.py` instala esa instancia
con el edificio configurado de identidad 006; no hay selección pública de otro edificio.
Las rutas de configuración revalidan cuenta/sesión bajo locks antes de escribir y
confirman revisión/evidencia/actividad de sesión en una UoW. La composición registra
`consumption.configuration.changed` en el catálogo de historia administrativa existente.

`read_general_snapshot`, `read_demand_history`, lecturas agrupadas y `FunctionalSummary.read`
siguen pendientes de 002; encontrar esta fachada no acredita esos proveedores.
`MeasurementStore.read_detail` devuelve IDs de registros cruzados, pero filtra diagnósticos
cruzados sin exponerlos.002 debe ampliar su evidencia de lectura para que 001 pueda
contarlos una sola vez;001 no crea otra consulta sobre tablas internas como sustituto.
