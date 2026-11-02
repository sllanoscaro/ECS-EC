---
description: "Tareas integrales de registro temporal y retención de consumo"
---

# Tasks: Registro temporal y retención del consumo

## Contexto compartido del proyecto (ECS-EC)

Aplican [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y constitución v1.0.0 en
`.specify/memory/constitution.md`. Plataforma/auditoría pertenece a 009, identidad a 006,
catálogo/fuentes/validación/cálculo puro a 001, recepción/historial/conservación a 002,
adquisición a 003 y observabilidad común a 007.

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [HTTP](contracts/http.md),
[integraciones](contracts/integrations.md), [UI](contracts/ui.md) y
[quickstart.md](quickstart.md).
**Fecha**: 2026-11-01; continuación local 2026-11-02. **Estado**: 68/71 tareas completas;
US1–US4 y validación automatizada local realizadas usando fachada/UI001 reales.
T064 (adaptador003), T065 (emisor007) y T068 (personas) permanecen pendientes.
No equivale a aceptación integral: [evidencia vigente](validation/acceptance.md).
Reemplaza el borrador de cinco tareas y conserva su alcance en la matriz de traslado.
Generar esta lista no acredita implementación, pruebas ejecutadas ni aceptación.

**Tests**: se incluyen por el flujo de desarrollo, punto 3, de la constitución, los
escenarios/Independent Test de la spec y las pruebas trasladadas. Escribir pruebas
antes del comportamiento nuevo; comprobar fallo por la capacidad faltante y conservar
como regresiones las que ya pasen. Dobles solo acreditan aislamiento; concurrencia,
transacciones, retirada y aceptación requieren PostgreSQL real.

**Documentación en cada tarea de código**: documentar propósito/responsabilidad del
archivo y contrato de cada función/método/clase/componente, público o privado:
entradas, salidas, errores y efectos; fórmulas/supuestos junto al código. Incluir
pruebas, fixtures, migraciones y scripts propios en el mismo cambio.

## Formato y rutas

`- [ ] TNNN [P?] [USn?] Descripción con ruta exacta`. IDs locales a esta spec.
`[P]` significa archivos distintos y prerrequisitos ya satisfechos; no permite editar
simultáneamente archivos compartidos. Las tareas de historia llevan `[US1]` a `[US4]`;
setup, fundaciones y cierre no llevan etiqueta de historia.

Rutas de código relativas a la raíz; enlaces relativos al archivo. La base y los proveedores 002 ya existen; las rutas previstas restantes no acreditan
implementación. Se amplía el módulo/página 001 y su router único
`backend/src/ecs_ec/consumption/router.py`, coordinando esquemas/puertos/consultas.
No se modifica software distribuido por Spec Kit ni se recrea el scaffold 009.

## Prerrequisitos externos por capacidad

| Capacidad y documento propietario | Gate / integración 002 |
| --- | --- |
| Plataforma: [009 plan](../009-fundaciones-plataforma/plan.md), [contrato](../009-fundaciones-plataforma/contracts/integrations.md) | Antes de migraciones/pruebas integradas: herramientas/locks, PostgreSQL 18, UoW, reloj, aniversario y auditoría reales en `backend/src/ecs_ec/core/` y `backend/src/ecs_ec/audit/`; registro existente en `backend/src/ecs_ec/main.py`. |
| Dominio/configuración: [001 modelo](../001-visualizar-consumo-categorias/data-model.md), [puertos](../001-visualizar-consumo-categorias/contracts/integrations.md) | Catálogo/contexto/revisiones y funciones puras en `backend/src/ecs_ec/consumption/catalog_storage.py`, `backend/src/ecs_ec/consumption/validation.py` y `backend/src/ecs_ec/consumption/totals.py`. Acordar interfaces primero, sin esperar aceptación completa de 001 ni crear un ciclo entre listas de tareas. |
| Identidad: [006 spec](../006-acceso-usuarios-rbac/spec.md) | Antes de endpoint/UI reales: sesión, permisos actuales y layout en `backend/src/ecs_ec/identity/` y frontend; 002 no crea cuentas, sesiones, CSRF ni autorización propia. |
| Adquisición: [003 spec](../003-simulador-pas600-sftp/spec.md) | Recepción nativa exige adaptador real de publicaciones completas/reenvíos. Fixtures internos pueden invocar el mismo puerto antes, sin acreditar PAS600/SFTP ni implementar su transporte. La ruta definitiva de adaptador pertenece a su plan. |
| Instrumentación: [007 spec](../007-observabilidad-externa/spec.md) | Instrumentación propia usa emisor real en `backend/src/ecs_ec/observability/` cuando exista. Recolectores/visores no bloquean commits o consultas. |
| Consumidores: [004](../004-costos-tarifa-bt43/contracts/integrations.md), [005](../005-generar-reportes-pdf/contracts/integrations.md), [008](../008-notificaciones-programables/contracts/integrations.md) | 002 implementa proveedores de series/ventanas/evidencia. No implementa costos, PDF, reglas, scheduler SMTP ni correo; aceptación conjunta espera consumidores reales. |

Registrar faltantes con capacidad, documento y ruta; no ejecutar automáticamente otras
specs. Documentar un gate faltante no habilita las tareas dependientes de esa capacidad.

## Phase 1: Setup de la funcionalidad

**Objetivo**: verificar propietarios y preparar integración/fixtures dentro del monolito.

- [X] T001 Verificar gates externos y registrar capacidades reales, propietarios/documentos/rutas, versiones y bloqueos en `specs/002-registro-retencion-consumo/validation/prerequisites.md`; comprobar PostgreSQL 18, DB de prueba separada, `btree_gist`/permisos y head Alembic real. No presentar archivos planificados como implementación ni crear capacidades ajenas.
- [X] T002 Conciliar interfaces/archivos compartidos con 001/009 en `specs/002-registro-retencion-consumo/contracts/integrations.md` y `specs/002-registro-retencion-consumo/validation/prerequisites.md`: orden de locks, UoW, proveedor de límites históricos, publicación frente a intento y composición existente; registrar `backend/src/ecs_ec/consumption/router.py` como router único y los nombres reales de integración. Mantener el contrato definido Reception.accept/read_attempt con attempt_id y entrada fija del adaptador, recuperación exclusiva y conflicto de payload; verificar correspondencia con el consumidor003 sin transferir propiedad de esos puertos.
- [X] T003 [P] Tras T001/T002, preparar fixtures documentados en `backend/tests/fixtures/consumption/history_scenarios.json` y `backend/tests/integration/consumption/conftest.py`: siete categorías, fuentes/revisiones sintéticas, >=12 meses, 14m59s/15m, DST/bisiesto, ceros/huecos/cruces, CAT-01 medida/calculada y extremos numéricos. Usar reloj/tzdata controlados, servicios 001 y `Reception.accept`; no INSERT de mediciones ni endpoint de inyección.
- [X] T004 [P] Tras T001/T002 y plataforma disponible, comprobar dependencias específicas en `pyproject.toml`, `uv.lock`, `frontend/package.json` y `frontend/package-lock.json`: tzdata reproducible y `decimal.js` reutilizada de 001; añadir/fijar solo faltantes, conservando CPython 3.14, pila/locks compartidos y build estático sin datos privados. No rehacer herramientas 009.

## Phase 2: Fundaciones compartidas y bloqueantes

**Objetivo**: preparar contratos, esquema y primitivas necesarias en toda incorporación.
La escritura inicial de agregados y vencimientos pertenece a esta base porque US1 no
debe confirmar datos sin ellos. US2 incorpora consulta/UI; US3 añade dependientes y
retirada. No hay callbacks vacíos en aceptación.
**Gate**: Phase 1 y capacidades reales de plataforma/dominio.

- [X] T005 [P] Escribir `backend/tests/contract/consumption/test_history_ports.py` para contratos de recepción/almacenamiento/lectura: resultados por posición, corte/UoW, GET sin efectos, campos nullable/versiones y proveedor completo de límites históricos; diferenciar error de proveedor frente a null real antes de ampliar DTO.
- [X] T006 [P] Escribir `backend/tests/integration/consumption/test_history_schema.py` para claves/FK protegidas, unicidad física/calculada, exclusión `[inicio,fin)` entre fuentes/tipos, contigüidad, estados y aporte único; comprobar rechazo/rollback y ausencia de cascadas destructivas en PostgreSQL real. Verificar también unicidad (building_id,start,end), estados y reactivación de TotalEvaluationRequest.
- [X] T007 [P] Escribir `backend/tests/unit/consumption/test_history_primitives.py` para límites hora/día/mes/año, duraciones UTC/DST/bisiesto, q=`10^-15 kWh`, sumas que superen precisión 50 y creación/vencimiento inicial mediante helper 009; obtener esperados independientes de los servicios nuevos.
- [X] T008 Ampliar DTO/puertos en `backend/src/ecs_ec/consumption/ports.py` sin importar implementaciones 002: `ReceptionOutcome`, `MeasurementStore` y entrada/salida agrupada/consumidores conforme a contratos; conservar «UUID generados por aplicación, revisiones positivas», «microsegundos», «zona IANA explícita», «intervalos `[start,end)`» y «HTTP conserva decimales y duraciones grandes como cadenas». Compartir UoW sin commits ocultos.
- [X] T009 Definir todos los campos de intentos/resultados/estado en `backend/src/ecs_ec/consumption/models.py`: `ReceptionAttempt` «`processing|completed|partial_failure`», «`completed_at|null`»; `CategoryUpdate` «`attempt_id|null`», «`kind: physical|calculated`», «`new_data_at|null`», «`previous_new_data_at|null`», «`next_admissible_at|null`», «UNIQUE `(attempt_id,category_id)`»; `ReceptionRecordResult` «`category_update_id|null`», «`category_id|null`», «`record_id|null`», «`status: accepted|duplicate|rejected`», «`reason_code|null`», «`next_admissible_at|null`», «UNIQUE `(attempt_id,input_position)`». Preparar siete `CategoryReceptionState` con «PK `(building_id,category_id)`», «`last_new_data_at|null`», «`next_admissible_at|null`», «`latest_interval_end|null`» y `BuildingReceptionState` con «`has_accepted_history` inicialmente false», «`first_new_data_at|null`», sin fabricar aceptaciones. En ReceptionAttempt incorporar input_schema_version positiva, input_manifest completo/canónico/tipado/inmutable e input_digest SHA-256; id igual al attempt_id persistido por adaptador confiable. Fijar manifiesto antes de resultados por categoría y comparar entrada completa además del hash; sin secretos/tokens en el manifiesto.
- [X] T010 Ampliar secuencialmente `backend/src/ecs_ec/consumption/models.py` con todos los campos de registro/payloads/candidatos del modelo: `IncorporatedRecord` «`measured|calculated`; calculado solo CAT-01», «`source_id|null`», «`logical_source_key|null`», «`start<end`», «`retained|withdrawn`», «`detail_withdrawn_at|null`», «NUMERIC exacto y coeficiente entero de `10^-15 kWh`; equivalentes. No float ni redondeo.» y evidencia inmutable; `AcceptedMeasurement` «PK/FK `record_id`», «`original_unit: Wh|kWh|MWh`», «`0<=E<10^30`» y «`10^-15 kWh`»; `IncorporatedTotal` «`base_categories` no vacía», contribuciones exactas y máximo «`6*(10^30-10^-15)` inclusive». `TotalCalculationState` conserva «`status: incomplete|no_basis|pending|incorporated`», «`reason_code|null`», «`next_admissible_at|null`», «`incorporated_record_id|null`» y todos sus segmentos/referencias, sin valor publicado antes de incorporar. Añadir TotalEvaluationRequest con todos los campos del modelo: «status: pending|processed», «processed_at|null», «start<end», revisión positiva y «UNIQUE (building_id,start,end)»; es almacenamiento propio 002, sin nueva API pública.
- [X] T011 Completar `backend/src/ecs_ec/consumption/models.py` con `ConsumptionAggregate` «`granularity: hour|day|month|year`», límites/offsets/zona/tzdata, coeficientes/duración/conteos/fechas/revisión/plazo y «UNIQUE edificio/categoría/granularidad/zona/start/end»; `AggregateContribution` con snapshot tipado y «UNIQUE `(aggregate_id,record_id)`». Generar `backend/migrations/versions/consumption_002_initial.py` enlazada al head real, o registrar nombre real equivalente en `specs/002-registro-retencion-consumo/validation/prerequisites.md`; incluir unicidades del registro y «EXCLUDE GiST `(building_id WITH =, category_id WITH =, tstzrange(start,end,'[)') WITH &&)`», índices y FK sin cascada, sin recrear tablas 001/009. Ejecutar T006 sobre el esquema real. Incluir tabla/índices/FK protegidas de TotalEvaluationRequest y su UNIQUE (building_id,start,end) en esa misma migración.
- [X] T012 Implementar calendario en `backend/src/ecs_ec/consumption/calendar.py` con zona IANA/tzdata y límites UTC: horas repetidas separadas por offset, inexistentes omitidas, transición no entera explícita, días/meses/años locales y primer instante válido en límite inexistente; duración positiva en UTC. Persistir límites/versión y detectar cambio de tzdata que requiera reconciliación antes de generar claves incompatibles; no reinterpretar historia ni reimplementar aniversario 009.
- [X] T013 Implementar primitivas/escritor transaccional en `backend/src/ecs_ec/consumption/aggregates.py`: sumar enteros exactos de q sin contexto fijo, registros totalmente contenidos de la misma categoría, cobertura por unión/duración real y creación desde primer aporte; actualizar cuatro niveles sin rollups y preservar aporte único. Calcular plazos iniciales/no decrecientes de registro/total/agregado con helper 009 y UoW del llamador; sin commit propio ni aceptación provisional sin agregados. Ejecutar T007 antes de habilitar US1.

**Checkpoint**: contratos/esquema/calendario/escritura común verificados; todavía no
hay recepción funcional ni aceptación web acreditadas.

## Phase 3: User Story 1 — Respetar la separación mínima (P1, MVP técnico)

**Objetivo**: incorporar novedades físicas/calculadas con 900 segundos por categoría,
primera fecha/origen conservados, resultados durables e independencia entre categorías.
**Independent Test**: puerto real y reloj controlado con siete categorías: rechazar
a 14m59s, aceptar desde 15m, no avanzar por duplicados/rechazos y verificar concurrencia/
reinicio CAT-01 en PostgreSQL.
**Gate**: Phase 2 y dominio/configuración 001 real; no acredita web ni SFTP.

### Pruebas antes del comportamiento nuevo

- [X] T014 [P] [US1] Escribir `backend/tests/contract/consumption/test_reception_contract.py` para `Reception.accept`, publicación lógica/posición/proceso/correlación, estados/causas, envío mixto y reenvío de misma publicación tras rechazo temporal; exigir primera incorporación y próxima admisible, sin caché terminal por publicación ni endpoint público. Añadir contrato Reception.read_attempt: not_found|processing|completed|partial_failure y outcome nullable solo en not_found; lectura autorizada sin crear/reanudar ni extender plazos. Accept con igual ID/entrada recupera original; igual ID/entrada distinta da attempt_payload_conflict y reenvío explícito usa ID nuevo, incluso con igual publicación.
- [X] T015 [P] [US1] Conservar/ampliar `backend/tests/integration/consumption/test_reception_limits.py` trasladada: primera aceptación, 14m59s/15m exactos, siete categorías simultáneas, lotes históricos, categoría anticipada frente a otra válida, fechas de fuente/DST/retroceso detectado del reloj y duplicados/solo inválidos que no reinician plazo; comprobar detalle/agregados intactos tras rechazo.
- [X] T016 [P] [US1] Escribir `backend/tests/integration/consumption/test_reception_concurrency.py` para dos novedades concurrentes, equivalencia Wh/kWh/MWh, conflicto, superposición/contigüidad y orden estable dentro del lote; correr recepción/reconfiguración 001 en ambos órdenes, revisión ajena/propia, máximos calculados y proveedor ausente/fallido/incompleto, sin configuración parcial.
- [X] T017 [P] [US1] Escribir `backend/tests/integration/consumption/test_pending_totals.py` para faltantes/desalineación/base vacía, cambio de firma frente a revisión global ajena, pendiente antes del límite CAT-01, múltiples candidatos vencidos, ejecuciones concurrentes y reinicio; GET no publica ni el backlog consume quince minutos por intervalo. Probar solicitud pending sin candidato al reiniciar, procesamiento fallido/reintentado y recepción concurrente que queda incluida o reactiva solicitud; completar sin reenvío de la fuente ni duplicación.
- [X] T018 [P] [US1] Escribir `backend/tests/integration/consumption/test_reception_durability.py` para commit/rollback conjunto de registro/estado/agregados/eventos 009, caída entre categorías y tras commit antes de respuesta, reconstrucción de resumen e idempotencia de eventos/intentos; DB fallida no acredita durabilidad. Inyectar caída exactamente después del commit de parciales y antes de crear candidato; al reiniciar recuperar desde solicitud durable sin reenvío. Fallar también entre escritura del resultado calculado y marcado processed: ambos deben revertirse. Probar dos recuperaciones simultáneas del mismo attempt_id, creación/continuación desde entrada inmutable, rechazo de payload cambiado sin mutar reloj/resultados, completed original sin reclasificar accepted como duplicate ni reevaluar too_early, y not_found distinto de DB/autorización fallidas.

### Implementación e integración

- [X] T019 [US1] Implementar escritura/coordinación en `backend/src/ecs_ec/consumption/store.py`: READ COMMITTED, contexto/configuración → categorías ordenadas → candidatos/registros/agregados; releer tras locks, clasificar contra ledger durable y dentro del lote, conservar primer original y contigüidad. Aplicar unicidad/exclusión PostgreSQL y savepoint recuperable después de locks; fallo de infraestructura revierte la categoría. Coordinar también filas de solicitudes bajo contexto → categorías ordenadas → solicitudes/candidatos para evitar perder novedades mientras se procesa.
- [X] T020 [US1] Definir firmas/DTOs de Reception.accept/read_attempt en `backend/src/ecs_ec/consumption/ports.py` e implementar `Reception.accept` con attempt_id/entrada fija del contrato en `backend/src/ecs_ec/consumption/reception.py` con validación 001 y T019/T013: validar segmentos/dominio antes de distinguir novedades, clasificar duplicados/conflictos antes del límite y exigir «`next_admissible_at = last_new_data_at + 900 segundos`» UTC obtenido del reloj actual 009 tras bloquear, sin usar `CURRENT_TIMESTAMP` fijado antes de la espera. Solo novedades confirmadas avanzan estado/máximos/historia; rechazo anticipado informa motivo/próxima fecha local y UTC, sin encolado automático. Crear/reactivar TotalEvaluationRequest pending por intervalo parcial nuevo que pueda afectar CAT-01 calculada en la misma UoW de aceptación, incluso sin candidato; duplicados/rechazos no crean ni reactivan solicitudes.
- [X] T021 [US1] Completar intentos/resultados en `backend/src/ecs_ec/consumption/reception.py`: UoW por categoría, resultado por posición, válidos independientes y publicación distinta de intento; reanudar partes no confirmadas y recomponer resumen. Aplicar «`processing → completed`» con todos los resultados durables y «`processing → partial_failure`» ante categorías sin confirmar, sin revertir otras ni responder aceptación antes del commit. Implementar read_attempt autorizado sin efectos con captura coherente y posiciones aún sin resultado; coordinador exclusivo por intento recuperable tras caída, sin esperar manteniendo locks de contexto/categorías. Crear entrada canónica al primer accept y validar equivalencia completa antes de continuar; completed devuelve resultado original, partial_failure→processing solo completa lo no confirmado. Igual ID con otra entrada da attempt_payload_conflict; una lecturaDB fallida no es not_found. Nuevo intento solo por reenvío explícito del adaptador, manteniendo publication_ref.
- [X] T022 [US1] Implementar evaluación/persistencia de candidatos en `backend/src/ecs_ec/consumption/pending_totals.py` mediante `TotalCalculator` 001, evidencia histórica y límite CAT-01: faltantes, no base, cambio de firma con segmentos sin fecha/faltantes ficticios, pendiente con próxima fecha e incorporado con referencias. Mantener «Reevaluaciones sin cambios de evidencia/estado conservan revisión y vencimiento»; parciales permanecen confirmadas y total físico no recibe sustitución. Consumir la solicitud bajo locks comunes y marcarla processed en la misma UoW que persiste candidato/diagnóstico/total; si aún no puede incorporar, guardar candidato pending antes de marcar procesada. Un error conserva la solicitud pending mediante rollback.
- [X] T023 [US1] Implementar `PendingTotals.run_due` en `backend/src/ecs_ec/consumption/pending_totals.py`: seleccionar sin invertir locks, revalidar elegibilidad/referencias y agrupar candidatos completos admisibles en una actualización CAT-01 mediante escritor común; recuperar al iniciar/reintentar. Esperas monotónicas acotadas y revalidación UTC durable; no persistir reloj monotónico entre reinicios. Consultar al arrancar y periódicamente tanto solicitudes pending sin candidato como candidatos pendientes de incorporación; no depender del reenvío de la fuente. Revalidar aportes confirmados y coordinar reactivación concurrente con recepción.
- [X] T024 [US1] Implementar `read_detail`, `read_extent`, `read_update_state` y `read_reconfiguration_bounds` en `backend/src/ecs_ec/consumption/store.py` e inyectar proveedor en fachadas 001 de `backend/src/ecs_ec/consumption/queries.py`; el último devuelve «`{has_accepted_history: bool, latest_interval_end_by_category: {category_id: instant|null}}`», exactamente las claves solicitadas, null solo si nunca incorporó y máximos físicos/calculados permanentes. Distinguir extensión del payload conservado de historia permanente.
- [X] T025 [US1] Integrar escritores 009 desde `backend/src/ecs_ec/consumption/reception.py` y `backend/src/ecs_ec/consumption/pending_totals.py`: `consumption.accepted` por actualización/revisión con `accepted_new_data=true` y `reception.completed` por resultado de categoría, conteos/causas y ventanas exactas además de envolvente; commit conjunto y deduplicación módulo/entidad/revisión/tipo, sin duplicar eventos por resumen. Implementar el proveedor propio de `FunctionalSummary.read` en `backend/src/ecs_ec/consumption/queries.py`: conteo observado o null, períodos íntegros/huecos y limitaciones al corte, sin derivar cobertura de logs/heartbeat ni importar 008.
- [X] T026 [US1] Registrar proveedor y trabajo CAT-01 cancelable en el ciclo de vida existente de `backend/src/ecs_ec/main.py`, con cierre/reinicio y dependencias inyectadas; ampliar solo el registro después de existir plataforma, sin worker separado ni cálculo/incorporación desde GET. Recuperar al arrancar y durante la ejecución solicitudes de evaluación aunque aún no tengan candidato, además de incorporaciones calculadas pendientes.
- [X] T027 [US1] Ejecutar T014..T018/T005 con PostgreSQL, auditoría y dominio 001 reales; registrar FR-001..006/SC-001, carreras y recuperación en `specs/002-registro-retencion-consumo/validation/reception.md`. Demostrar persistencia de originales/estado/agregados/eventos; separar fixtures internos de recepción física no validada. Registrar explícitamente recuperación sin reenvío tras caída entre aceptación de parciales y creación de candidato, y ausencia de pérdida por concurrencia con el trabajo.

**Checkpoint**: MVP técnico US1 verificable por puerto real; no acredita consulta
agrupada web, retirada, SFTP ni aceptación completa de la funcionalidad.

## Phase 4: User Story 2 — Consultar hora, día, mes y año (P1)

**Objetivo**: exponer las cuatro agrupaciones con valores exactos, calendario/procedencia
y los mismos bloques en gráfico/tabla, conservando categoría/período.
**Independent Test**: siete categorías con sumas conocidas: cuatro intervalos de 1 kWh
dan 4 kWh; día/mes/año coinciden con suma directa, incluidos DST/bisiesto y CAT-01.
Cambiar agrupación mantiene filtro y ambas vistas representan la respuesta real.
**Gate**: US1, identidad006 y fachada/página 001 reales para aceptación web.

### Pruebas antes de consulta e interfaz nuevas

- [X] T028 [P] [US2] Conservar/ampliar `backend/tests/integration/consumption/test_aggregates.py` trasladada: sumas conocidas de siete categorías/cuatro niveles, contención `[inicio,fin)`, contigüidad, DST/bisiesto/meses de distinta duración, cruces utilizables en nivel mayor y CAT-01 medida 100 frente a parciales 60 o calculada 20+30=50; incluir máximos/quantum/sumas superiores a precisión 50 y cobertura de cero frente a ausencia.
- [X] T029 [P] [US2] Escribir `backend/tests/contract/consumption/test_aggregate_http.py` contra tablas/ejemplo de `specs/002-registro-retencion-consumo/contracts/http.md`: campos obligatorios/nullables, estados, decimales/duraciones como cadenas, selección exacta, bloques de extremos excluidos, zona/offset/microsegundos, 200/401/403/404/422/503 y `no-store` también en error; sesión real 006 para aceptación.
- [X] T030 [P] [US2] Escribir `backend/tests/contract/consumption/test_history_consumers.py` para última ventana terminada/completa, resolución demostrada, cursor inválido/revisión tardía, zona 008 distinta y proyección sin escritura; verificar captura/UoW compartida, CAT-01 física limitada para 004 y siete categorías/procedencia para 005 sin implementar consumidores.
- [X] T031 [P] [US2] Escribir `frontend/tests/unit/consumption-history.test.tsx` para selector Detalle/Hora/Día/Mes/Año, filtro/categoría conservados, bloques idénticos en tabla/tooltip, offsets repetidos, un bloque/ceros/positivo minúsculo y máximo agregado exacto; comparar contra respuesta conocida, no recalcular sumas en el test con el componente.
- [X] T032 [P] [US2] Ampliar `frontend/tests/e2e/consumption.spec.ts` con recorrido autenticado de agrupaciones/siete categorías, límites/valores/cobertura/procedencia contra API, filtro con extremos parciales y navegador en otra zona; escribir escenarios antes de montar el incremento y preservar pruebas 001.

### Implementación e integración

- [X] T033 [US2] Implementar proyección de `AggregateBlock` en `backend/src/ecs_ec/consumption/aggregates.py` sobre aportes persistidos: «`temporal_state: not_started|ongoing|finished`», «`coverage_state: complete|incomplete|no_data`», energía null sin contribuciones y cero explícito con cobertura. Exponer «Cadenas de enteros >=0; duración total estrictamente positiva», porcentaje «hasta seis decimales» clasificado antes de redondeo y «`contribution_count`» no negativo; no derivar completitud del porcentaje mostrado. Aplicar not_started si cutoff_at < start, ongoing si start <= cutoff_at < end y finished si cutoff_at >= end; conservar bloques futuros y clasificar cobertura independientemente.
- [X] T034 [US2] Implementar `Consumption.query_aggregates` en `backend/src/ecs_ec/consumption/queries.py`: captura REPEATABLE READ/corte común, bloques totalmente contenidos ordenados UTC, vacíos proyectados sin filas/plazos y extremos excluidos con razón, configuración/procedencia histórica y diagnósticos; copiar resultado antes de liberar UoW, sin aceptar/recalcular CAT-01 ni usar caché anterior al commit.
- [X] T035 [US2] Ampliar `backend/src/ecs_ec/consumption/schemas.py` y `backend/src/ecs_ec/consumption/router.py` para GET `/api/v1/consumption/categories/{category_id}/aggregates`: `start`/`end`/`timezone`/`granularity` obligatorios, «`hour|day|month|year`», «`CAT-01`..`CAT-07`», zona del edificio/offset válido y microsegundos. Mantener campos presentes, null explícito en IDs/revisión/fechas del bloque vacío, energía decimal sin exponente, `Problem`/estados HTTP del contrato y autorización actual 006; no recortar resultados ni añadir paginación silenciosa.
- [X] T036 [US2] Conectar router/fachada agrupada al registro existente en `backend/src/ecs_ec/main.py`, usando dependencias 001/002/006 reales y `Cache-Control: no-store` en toda respuesta protegida; preservar rutas/configuración/detalle 001, sin nuevo servidor Node, endpoint de recepción o datos privados en export estático.
- [X] T037 [US2] Ampliar tipos/cliente de `frontend/src/lib/api/consumption.ts` con selección agrupada y `AggregateQueryResult` del contrato, energía/porcentajes/duraciones como cadenas y fechas textuales con microsegundos; reutilizar sesión/error/cancelación 001/006, documentar regeneración si genera código y no calcular consumos en navegador.
- [X] T038 [US2] Crear `frontend/src/components/consumption/GranularitySelector.tsx` e integrarlo en `frontend/src/components/consumption/ConsumptionView.tsx` y `frontend/src/app/consumption/page.tsx`: Detalle inicial y Hora/Día/Mes/Año, período inicial global 001 y filtro/categoría/zona conservados al alternar. La misma respuesta alimenta gráfico/tabla; clave de petición incluye granularidad.
- [X] T039 [P] [US2] Tras T037/T038, ampliar `frontend/src/components/consumption/EnergyChart.tsx` para bloques agrupados sin volver a agregarlos: límites/offsets, energía exacta por foco/tooltip, duración/cobertura/estado temporal accesibles y marcadores 001 para un solo bloque/cero/positivo inferior al píxel; huecos sin interpolación ni barras de cero ficticias.
- [X] T040 [P] [US2] Tras T037/T038, ampliar `frontend/src/components/consumption/EnergyTable.tsx` con límites/kWh/cobertura/estado temporal/procedencia de los mismos bloques, tabla semántica y formateador Decimal común 001; representar hora repetida por offset, fuentes/bases por segmento y alcance parcial de CAT-01 sin sumar parciales de nuevo.
- [X] T041 [US2] Implementar `Consumption.latest_admissible_window` en `backend/src/ecs_ec/consumption/queries.py`: «`status: available|not_evaluable`», energía nullable y «`reason_code|null`»; disponible exige ventana terminada/fuente válida/aporte/cobertura completa. Validar resolución/activación/cursor versionado, devolver revisión de evidencia estable o nueva ante datos tardíos; otra zona usa aportes originales en proyección transitoria, sin sumar buckets del edificio, crear persistencia ni inventar resolución de quince minutos.
- [X] T042 [US2] Implementar proveedores `read_general_snapshot` y `read_demand_history` en `backend/src/ecs_ec/consumption/queries.py` sobre `store.py` existente: CAT-01 física/suministro con intervalos/revisión/cobertura, calculada como limitación y resolución exacta demostrada para demanda; no reconstruir quince minutos desde hora ni aplicar tarifas/cálculos propios de 004.
- [X] T043 [US2] Conectar lecturas 002 con `Consumption.read_report_snapshot` de la fachada 001 en `backend/src/ecs_ec/consumption/queries.py`: siete categorías, detalle/agregados conservados, origen/base/alcance/segmentos y evidencia/revisiones al mismo corte/UoW del llamador. Liberar antes de renderizar y documentar que una fecha sola no reproduce snapshots históricos; no generar PDF ni recalcular costos.
- [X] T044 [US2] Ejecutar T028..T032 con identidad/DB/dominio reales y build estático; registrar FR-007..013/SC-002, correspondencia API/gráfico/tabla y contratos productores en `specs/002-registro-retencion-consumo/validation/aggregates.md`. Separar contrato del proveedor de aceptación conjunta pendiente con consumidores externos.

**Checkpoint**: US2 consultable en web autenticada con las cuatro granularidades;
no se acredita SC-005 ni integración nativa por estas pruebas.

## Phase 5: User Story 3 — Conservar y consultar doce meses (P1)

**Objetivo**: proteger mediciones/totales/agregados, base y referencias según aniversario
local; permitir retirada interna elegible sin degradar agregados ni idempotencia.
**Independent Test**: >=12 meses sintéticos en siete categorías y reloj avanzado:
consulta antes/en límite, dato tardío desde aceptación, 29 de febrero/hora inexistente/
repetida, y agregado protegido tras retirar payload vencido y reenviar aportes.
**Gate**: US1/US2 y helper 009 real; sin esperar doce meses reales.

### Pruebas antes de políticas y retirada nuevas

- [X] T045 [P] [US3] Conservar/ampliar `backend/tests/integration/consumption/test_retention.py` para mínimo desde primera aceptación/incorporación, agregado desde primera/última novedad, datos tardíos, consultas/duplicados/rechazos que no extienden plazo, disponibilidad antes/en aniversario y conservación posterior opcional; incluir 2028-02-29→2029-02-28, hueco/repetición local, tzdata que no adelanta plazo e historia anual parcial.
- [X] T046 [P] [US3] Escribir `backend/tests/integration/consumption/test_detail_withdrawal.py`: retirada protegida rechazada, retirada vencida permitida mediante operación real, agregado aún protegido intacto y posterior lote con duplicado/conflicto/superposición/novedad; solo la novedad suma/cubre/extiende, sin reactivar payload por reenvío ni perder máximos de reconfiguración.
- [X] T047 [P] [US3] Escribir `backend/tests/integration/consumption/test_retention_references.py` para dependencias protegidas de total calculado/pendiente, fuentes/revisiones/diagnósticos y aportes con payload vencido; impedir referencias rotas/cascadas, permitir completar candidato desde evidencia conservada y comprobar consulta/puerto de límites históricos después de retirada. Incluir solicitudes pending que aún no tienen candidato y comprobar que su evidencia necesaria permanece disponible para recuperarlas.

### Implementación e integración

- [X] T048 [US3] Implementar políticas de `backend/src/ecs_ec/consumption/retention.py` sobre helper 009: primera aceptación física, primera incorporación calculada y primera/última novedad del agregado, doce meses calendario en zona del edificio y «`retain_until` nunca disminuye». Reutilizar desde escritor común/recepción/pendientes, conservar zona/límite calculado y no considerar lectura/duplicado/rechazo/sondeo como revisión sustantiva.
- [X] T049 [US3] Implementar protección efectiva de dependencias en `backend/src/ecs_ec/consumption/retention.py` y su uso desde `backend/src/ecs_ec/consumption/pending_totals.py`: extender payload/origen/revisión/evidencia necesarios hasta el dependiente protegido, preservar base/contribuciones y bloquear retirada si falta evidencia de elegibilidad; no fijar TTL desde fecha medida ni acoplar a SMTP. Incluir solicitudes TotalEvaluationRequest pending en la comprobación de dependencias antes de retirar evidencia necesaria para su evaluación.
- [X] T050 [US3] Implementar previsualización/ejecución de `Retention.withdraw_detail` en `backend/src/ecs_ec/consumption/retention.py` y persistencia en `backend/src/ecs_ec/consumption/store.py`: proceso interno autorizado, motivo y UoW/locks comunes, comprobar «`now>=retain_until`» y dependientes; eliminar solo payload permitido y auditar. Conservar ledger/aportes/configuración/máximos, sin purga automática obligatoria, cascada destructiva ni cambio de valor/cobertura/revisión del agregado por retirada.
- [X] T051 [US3] Ajustar `backend/src/ecs_ec/consumption/store.py` y `backend/src/ecs_ec/consumption/queries.py` para detalle conservado frente a retirado, agregado histórico protegido y referencias aún consultables; mantener deduplicación/exclusión permanente y sumar solo nuevos aportes tardíos. GET no reconstruye el payload retirado, acepta registros ni cambia plazos.
- [X] T052 [US3] Ampliar primero `frontend/tests/e2e/consumption.spec.ts` con avisos de retirada/inicio de operación y después integrarlos en `frontend/src/components/consumption/QueryState.tsx` y `frontend/src/components/consumption/ConsumptionView.tsx` según respuesta; explicar `detail_withdrawn` y disponibilidad de agregado/detalle sin afirmar un año completo ni degradar cobertura preservada. Verificar el recorrido contra API real.
- [X] T053 [US3] Ejecutar T045..T047 y consulta autenticada de historia >=12 meses para siete categorías, incluyendo reinicio y retirada real permitida; registrar los nueve escenarios US3/FR-015..019/SC-004 en `specs/002-registro-retencion-consumo/validation/retention.md`, con reloj/tzdata/fechas de límite y disponibilidad observada.

**Checkpoint**: mínimo de conservación y retirada comprobados con dependencias
reales; no se infiere historia anterior al inicio de operación.

## Phase 6: User Story 4 — Interpretar incompletos y datos tardíos (P2)

**Objetivo**: completar mensajes/recorridos y validación transversal de huecos, ceros,
períodos en curso, cruces y nuevas incorporaciones visibles tras commit.
**Independent Test**: hora con tres cuartos a 1 kWh = 3 kWh/75 %; vacío = null/0 %;
ceros cubiertos = 0; cuarto tardío permitido = 4 kWh/100 % en siguiente consulta;
reenvío no modifica resultado. Bloques futuros, en curso y terminados se distinguen
en ambas vistas; antes de start / en start / en end se conserva el filtro.
**Gate**: US1/US2; casos con retirada requieren US3. La semántica base incompleta ya
se prueba desde fundaciones/US2; esta historia no habilita que antes se inventen ceros.

### Pruebas antes de completar recorridos nuevos

- [X] T054 [P] [US4] Escribir `backend/tests/integration/consumption/test_history_late_data.py` para 3→4 kWh/75→100 %, actualizaciones anticipadas/invalidas fuera del historial, ceros físicos/calculados, huecos/en curso, cruce de nivel fino válido en amplio y reenvío posterior a retirada; la primera consulta iniciada después del commit ve nuevos aportes/revisión, sin esperar agregación eventual.
- [X] T055 [P] [US4] Escribir `backend/tests/contract/consumption/test_aggregate_states.py` para clasificación temporal/cobertura independiente, ausencia de energía null frente a cero, falta de un microsegundo aunque porcentaje redondee a 100, `blocks=[]` y diagnósticos CAT-01 con null/base/segmentos/faltantes/fecha adecuados; error de DB no equivale a falta de datos. Añadir bloque futuro sin lecturas (not_started/null/0 %), corte exactamente en start (ongoing) y exactamente en end (finished), con filtro conservado y cobertura independiente.
- [X] T056 [P] [US4] Escribir `frontend/tests/unit/consumption-history-states.test.tsx` para carga/sin medidor/sin datos/incompleto/en curso/error, `<100 %` por redondeo, avisos de cruce/base parcial/retirada y faltantes/cambio/pendiente CAT-01; incluir A→B con respuesta antigua, error/reintento, selección inválida y limpieza al vencer sesión. Probar Aún no iniciado antes del inicio, En curso desde start y Terminado desde end, idénticos en gráfico y tabla y sin cambiar el filtro.
- [X] T057 [P] [US4] Escribir `frontend/tests/e2e/consumption-history-states.spec.ts` con identidad/API reales: publicar tardío mediante preparación interna del harness, actualizar consulta y comparar ambas vistas; probar cero frente a hueco, período en curso, cruce excluido, sesión vencida, otra categoría y respuesta demorada, sin endpoint de pruebas público. Incluir bloques futuros sin datos y cortes controlados antes de start, exactamente en start y en end; verificar etiquetas, energía null/cobertura cero cuando falten lecturas y selección conservada en ambas vistas.

### Implementación e integración

- [X] T058 [US4] Completar proyecciones/avisos en `backend/src/ecs_ec/consumption/aggregates.py`, `backend/src/ecs_ec/consumption/queries.py` y `backend/src/ecs_ec/consumption/schemas.py`: prioridad global del contrato «`available|incomplete|no_data|no_meter`», origen «`measured|calculated|mixed|unavailable`», estados por bloque, huecos/cruces/extremos/base/retirada y períodos sin configuración/historia. No modificar filtros, prorratear energía ni diagnosticar contribuciones faltantes cuando solo están pendientes de incorporación.
- [X] T059 [US4] Completar recorrido tardío en `backend/src/ecs_ec/consumption/reception.py`, `backend/src/ecs_ec/consumption/pending_totals.py` y `backend/src/ecs_ec/consumption/aggregates.py`: actualización conjunta de los niveles afectados, cobertura/revisión/plazos, aporte ya contabilizado inmutable y caché invalidada por revisión; ninguna novedad anticipada/inválida aparece incorporada. Preservar valor/cobertura previos tras retirada y comprobar T054.
- [X] T060 [US4] Completar presentación compartida en `frontend/src/components/consumption/QueryState.tsx`, `frontend/src/components/consumption/EnergyChart.tsx` y `frontend/src/components/consumption/EnergyTable.tsx`: Sin datos/— frente a cero, En curso, porcentaje/duración real y `<100 %` cuando redondea; avisos legibles y por teclado, huecos sin valores ficticios y errores distintos de ausencia. Mostrar Aún no iniciado para not_started, En curso para ongoing y Terminado para finished, según corte común; mantener bloques futuros contenidos y cobertura independiente del estado temporal.
- [X] T061 [US4] Completar ciclo de peticiones en `frontend/src/components/consumption/ConsumptionView.tsx` y `frontend/src/lib/api/consumption.ts` con clave categoría/inicio/fin/zona/granularidad y generación/abort; descartar respuestas viejas después de cambio/error/reintento, conservar último rango válido y limpiar datos al vencer/cerrar sesión, sin localStorage privado.
- [X] T062 [US4] Integrar mensajes/procedencia histórica CAT-01 en `frontend/src/components/consumption/QueryState.tsx` y `frontend/src/components/consumption/ConsumptionView.tsx`: medido frente a calculado, base/fuentes por segmento, alcance parcial, contribución faltante, cambio de configuración y pendiente temporal diferenciados; Actualizar consulta lo confirmado sin publicar pendientes ni sumar parciales.
- [X] T063 [US4] Ejecutar T054..T057 y regresiones US1..US3; registrar FR-010..014/019 y SC-003 en `specs/002-registro-retencion-consumo/validation/incomplete-history.md`, con respuestas antes/después de commit y pruebas de correspondencia/selección/reintento/accesibilidad. Registrar también fronteras futuras/inicio/fin y conservación del filtro en ambas vistas.

**Checkpoint**: las cuatro historias cumplen escenarios automatizados con evidencia
real; SC-005 y verificaciones externas permanecen pendientes hasta ejecutarse.

## Phase 7: Cierre y aspectos transversales

- [ ] T064 Con adaptador real 003 disponible, escribir/ejecutar `backend/tests/integration/consumption/test_source_reception.py` para publicación completa, identidades/referencias temporales, fragmentos que forman una actualización y reenvío desde próxima admisible sin perder lecturas pendientes; documentar compatibilidad/faltantes en `specs/002-registro-retencion-consumo/validation/source-integration.md`. No implementar formatos/transporte ni acreditar PAS600/SFTP con fixtures; si falta capacidad externa, conservar esta validación pendiente. Verificar que003 persiste attempt_id/entrada antes de llamar002, recupera con read_attempt/accept el mismo intento tras caída y usa ID nuevo al reenviar tras too_early; no reabrir rechazos confirmados al recuperar.
- [ ] T065 Con emisor 007 disponible, escribir primero `backend/tests/integration/consumption/test_history_telemetry.py` y después ampliar instrumentación propia 002 en `backend/src/ecs_ec/consumption/telemetry.py`, conectada desde recepción/agregados/retención/pendientes/router; ejecutar para verificar correlación/códigos/esperas/reintentos saneados, sin cuerpos/secretos ni eventos funcionales duplicados. No crear emisor, recolectores, visores ni infraestructura técnica.
- [X] T066 Escribir/ejecutar `backend/tests/integration/consumption/test_history_availability.py` con DB/identidad/auditoría reales: reinicio de app/DB, consumidores 008/SMTP/visores indisponibles, error DB explícito, ausencia de commits/eventos parciales y GET sin efectos. Comprobar permisos/no-store y que ninguna dependencia técnica externa condicione recepción/consulta.
- [X] T067 Ejecutar comandos aplicables de `specs/002-registro-retencion-consumo/quickstart.md`: pruebas backend/frontend/E2E, build estático y recorridos con >=12 meses/siete categorías; registrar comandos/versiones/tiempos/resultado y pendientes en `specs/002-registro-retencion-consumo/validation/acceptance.md`. Medir sin inventar SLO y distinguir bloqueos externos de fallos propios.
- [ ] T068 Ejecutar evaluación humana SC-005 y registrar diez tareas representativas de categoría/agrupación/período en `specs/002-registro-retencion-consumo/validation/usability.md`: consumo/período/cobertura reconocidos en ambas vistas sin ayuda y tiempo por tarea; exigir >=9 correctas en <=60 s cada una. Sin participantes/resultados reales, dejar el criterio y la tarea pendientes.
- [X] T069 Revisar documentación de cada archivo/función/método/clase/componente propio, incluidos privados, tests/fixtures/migraciones y scripts, y registrar cobertura/faltantes en `specs/002-registro-retencion-consumo/validation/documentation.md`; corregir en sus archivos contratos/fórmulas/supuestos/origen de código generado antes de considerar completo el cambio.
- [X] T070 Actualizar `specs/002-registro-retencion-consumo/quickstart.md` y los procedimientos propios referenciados desde `deploy/README.md` con comandos/rutas reales, zona/tzdata, sincronización de reloj, próxima admisible/reenvío, pendientes/reinicio, respaldo/restauración 009 y retirada interna; mantener secretos externos y enlaces relativos, sin asumir validación VPS desde ejecución local.
- [X] T071 Consolidar trazabilidad FR-001..019/SC-001..005, evidencias de cada historia, dependencias reales y pendientes en `specs/002-registro-retencion-consumo/validation/acceptance.md`; revisar consistencia de `specs/002-registro-retencion-consumo/plan.md`, `specs/002-registro-retencion-consumo/tasks.md` y `docs/implementation-roadmap.md`. No marcar checklists/requisitos, pruebas humanas, fuentes o implementación que carezcan de resultado comprobado.

## Dependencies & Execution Order

### Orden entre fases e historias

```text
Gates plataforma009 + dominio001
              |
      Phase 1 -> Phase 2
                   |
             US1 (T014..T027)  <- MVP técnico de recepción
                   |
             US2 (T028..T044)  <- requiere identidad006/UI001 reales
                   |
             US3 (T045..T053)
                   |
             US4 (T054..T063)
                   |
       Cierre (T064..T071)     <- gates 003/007 y personas donde corresponda
```

La dependencia US1→US2 corresponde a datos reales; US3 necesita registros/agregados
reales; US4 usa ambos y sus casos de retirada dependen de US3. Cada checkpoint se
valida con sus propios escenarios sin necesitar implementar una historia posterior.
No se promete independencia de las capacidades de datos que una historia consume.

Dentro de cada fase: pruebas antes de comportamiento nuevo → modelos/servicios →
adaptadores → integración → ejecución de criterios. Las fundaciones T009..T011 son
secuenciales sobre el mismo modelo/migraciones; T013 requiere T012. T019..T026 siguen
el orden indicado; T027 comprueba el incremento completo. Tras US1, T028..T032 pueden
prepararse juntos; T033..T038 preceden a la integración visual T039/T040. T041..T043
secuenciales sobre consultas; T044 espera todos. US3/US4 conservan el orden de
implementación después de sus grupos de pruebas.

### Archivos compartidos y oportunidades paralelas

Los grupos siguientes son oportunidades de trabajo independiente cuando se cumplan
sus gates, no una instrucción para ejecutar agentes ni para saltarse dependencias:

| Grupo | Prerrequisito | Tareas y archivos independientes |
| --- | --- | --- |
| Setup | T001/T002 y capacidad de entorno para cada tarea | T003 fixtures/conftest y T004 manifiestos/locks. |
| Fundaciones | Phase 1 | T005 contrato, T006 esquema PostgreSQL y T007 primitivas, sin modificar helpers comunes. |
| US1 | Phase 2 | T014..T018: contrato, límite, concurrencia, pendientes y durabilidad en archivos distintos. |
| US2 pruebas | US1 y entorno web donde corresponda | T028..T032: agregados, HTTP, consumidores, componentes y E2E. |
| US2 vistas | T037/T038 | T039 gráfico y T040 tabla, con DTO/formateador compartidos ya estables. |
| US3 | US2 | T045..T047: conservación, retirada y referencias. |
| US4 | US3 | T054..T057: tardíos, contrato de estados, componentes y E2E de estados. |

Coordinar secuencialmente con 001/009 cualquier edición de modelos, puertos, esquema
HTTP, consultas, router, composición, manifiestos, conftest, componentes y E2E compartidos.
Los grupos `[P]` son internos a 002 y no habilitan ediciones simultáneas con otros
propietarios. T039/T040 editan componentes distintos después de estabilizar sus contratos.

### Ejemplos por historia

| Historia | Ejemplo paralelo concreto |
| --- | --- |
| US1 | Tras Phase 2, escribir T015 `backend/tests/integration/consumption/test_reception_limits.py` junto con T017 `backend/tests/integration/consumption/test_pending_totals.py`; ejecutar después de implementar sus proveedores. |
| US2 | Tras T037/T038, ampliar T039 `frontend/src/components/consumption/EnergyChart.tsx` junto con T040 `frontend/src/components/consumption/EnergyTable.tsx`, usando el mismo DTO/formateador sin editarlo. |
| US3 | Tras US2, escribir T045 `backend/tests/integration/consumption/test_retention.py` junto con T046 `backend/tests/integration/consumption/test_detail_withdrawal.py` contra fixtures ya preparados. |
| US4 | Tras US3, escribir T055 `backend/tests/contract/consumption/test_aggregate_states.py` junto con T056 `frontend/tests/unit/consumption-history-states.test.tsx` con respuestas del contrato común. |

## Implementation Strategy

### MVP primero

Completar gates, setup y fundaciones; implementar US1 y ejecutar T027. El incremento
demuestra recepción durable/límite/pendientes CAT-01 por puerto interno, con agregados
y plazos escritos atómicamente. No representa aceptación completa de spec-002 ni
validación SFTP/web. No desplegar funcionalidades incompletas como si cumplieran toda
la spec; los pasos de despliegue siguen los procedimientos y autorizaciones del proyecto.

### Entrega incremental

Añadir US2 y validar API/gráfico/tabla; añadir US3 y comprobar aniversarios/retirada;
completar US4 y comprobar estados/tardíos/carreras de consulta. Ejecutar regresiones al
incorporar cada incremento. El cierre valida dependencias reales, documentación y
SC-005; ausencia de un propietario o de personas deja la evidencia correspondiente
pendiente. No sustituir aceptación funcional por existencia de documentos.

## Trazabilidad de requisitos, contratos y traslado

| Requisito / criterio | Implementación y verificación en esta spec |
| --- | --- |
| FR-001 | T003/T008, T015/T020/T024/T027; catálogo fijo 001 consumido, sin siete medidores obligatorios. |
| FR-002, FR-003, FR-004, FR-005 | T014..T027; límite por categoría, reloj de plataforma, rechazo/reenvío, duplicados, concurrencia y recuperación durable antes del candidato. |
| FR-006 | T009/T010/T019..T025; originales, primera fecha, base y referencias, medido frente a calculado. |
| FR-007, FR-008, FR-009 | T007/T011..T013/T028/T033..T044; cuatro niveles/calendario, suma exacta por categoría y CAT-01 propia. |
| FR-010, FR-011, FR-012, FR-013 | T028..T040/T054..T063; contención, duración/cobertura/estados y correspondencia de vistas. |
| FR-014 | T013/T017/T018/T020/T022/T023/T034/T041/T054/T059/T063; evaluación CAT-01 durable antes del candidato y siguiente consulta posterior al commit sin duplicación. |
| FR-015, FR-016, FR-017, FR-018 | T010..T013/T045..T053; aniversario, protección/referencias, retirada y deduplicación durable. |
| FR-019 | T034/T045/T051/T052/T053/T058/T063; historia insuficiente sin estimar ni afirmar cobertura anterior. |
| SC-001 | T015..T018/T027; siete categorías, primeros envíos, 14m59s/15m y concurrencia. |
| SC-002 | T007/T028..T044; sumas conocidas y API/gráfico/tabla, meses/bisiesto/DST. |
| SC-003 | T028/T033/T054..T063; faltantes, ceros, futuros/en curso/terminados, cruces/tardíos y estado exacto. |
| SC-004 | T003/T045..T053/T067; >=12 meses/siete categorías, reloj controlado y consulta protegida. |
| SC-005 | T031/T032/T056/T057 preparan interfaz; solo T068 acredita resultado con personas. |
| Contrato recepción/pendientes/almacenamiento | T005/T014..T027; pruebas de puerto antes de proveedor real. |
| Contrato HTTP agrupado | T029 antes de T034..T036; estados extendidos T055/T058. |
| Contrato UI | T031/T032 antes de T037..T040; T056/T057 antes de T060..T062. |
| Contrato consumidores 004/005/008 | T030 antes de T041..T043; sin implementar sus negocios ni afirmar integración real mediante dobles. |
| Borrador 002 T001, procedente de pruebas 008 T010 | T015/T016/T027 conservan íntegro límite/concurrencia/duplicados/categorías. |
| Borrador 002 T002, procedente de persistencia 008 T020 | T009..T013/T019..T026 conservan almacenamiento, primera fecha, validación 001 y límite físico/calculado. |
| Borrador 002 T003, procedente de pruebas 008 T010/T021 | T007/T028/T033/T044/T054 conservan sumas, DST, CAT-01, cruce y cobertura cero/ausencia. |
| Borrador 002 T004, procedente de agregados 008 T021 | T012/T013/T033/T034/T041..T044 conservan agregados, última ventana admisible, corte/revisión y consumo sin estimaciones. |
| Borrador 002 T005 | T045..T053 conservan retención de mediciones/totales/agregados, helper 009 y protección/deduplicación tras retirada. |

Los IDs del borrador/008 son procedencia histórica, no dependencias de ejecución.
Todas las tareas nuevas y trasladadas permanecen pendientes hasta resultado real.
