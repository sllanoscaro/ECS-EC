---
description: "Tareas integrales de spec-001: consumo eléctrico por categorías"
---

# Tasks: Consumo eléctrico por categorías

**Fecha**: 2026-11-01. **Continuación**: 2026-11-03,57/61 tareas completas.
**Estado**: ampliaciones locales de recepción/configuración, períodos/estados y telemetría
propia verificadas sobre002/006/007 reales. [Aceptación vigente](validation/acceptance.md).
Pendientes: T056 por proveedores003/008 ausentes; T059/personas, T060/VPS y T061/cierre
integral. Las verificaciones humanas/VPS se difieren por instrucción del usuario.
Los proveedores de diagnósticos cruzados y retirada002 ya están disponibles y probados.
**Aclaraciones integradas**: I1/U1/A1 aprobadas; se conservan IDs, historias y marcas pendientes.
**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/) y [quickstart.md](quickstart.md).
**Prerequisites**: diseño completo y capacidades externas según los gates de este archivo;
revisar consistencia antes de implementar. La existencia de documentos no satisface un gate.
**Tests**: se incluyen las pruebas de aceptación explícitas de las cuatro historias y las
pruebas automatizadas exigidas por la constitución, flujo de desarrollo §3. Se conserva
el orden del traslado: escribir las pruebas antes de implementar y comprobar el fallo
por comportamiento ausente; un error de entorno no acredita esa comprobación.

**Resumen**: 61 tareas: Setup 4, Foundation 8, US2 8, US1 16, US3 8, US4 9 y cierre 8.
Hay 23 tareas `[P]`, sujetas a los grupos/prerrequisitos descritos abajo. MVP visible:
base y recepción confiable US2 → consulta gráfico/tabla US1 con dependencias reales.

## Contexto compartido del proyecto (ECS-EC)

Leer [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y
[constitución](../../.specify/memory/constitution.md). 009 posee scaffold, DB/UoW/reloj,
auditoría/eventos y operación; 006, identidad/permisos; 002, incorporación, almacenamiento,
15 minutos, agregados y retención; 003, PAS600/SFTP; 007, emisor/visores técnicos;
008, notificaciones/correo. Aquí se implementa únicamente consumo de 001 y sus integraciones.

**Documentación obligatoria en cada tarea**: propósito de cada archivo y contratos de todas
las funciones, métodos, clases, componentes y pruebas propios, públicos y privados, con
entradas, salidas, errores y efectos. Documentar fórmulas/supuestos junto al código y
actualizar contratos/guía en el mismo cambio. No diferirlo al cierre.

## Format: `[ID] [P?] [Story] Description`

IDs T001..T061 locales a **spec-001**; referencias entre specs siempre por capacidad,
documento y ruta. `[P]` permite trabajo en archivos distintos solo tras sus prerrequisitos,
según los grupos indicados al final. Rutas de código relativas a la raíz; rutas futuras
no acreditan implementación. Las fases sin historia no usan `[USn]`.

## Path Conventions

Código propio en `backend/src/ecs_ec/consumption/` y
`frontend/src/components/consumption/`; rutas web bajo `frontend/src/app/`.
Pruebas en `backend/tests/{unit,integration,contract}/consumption/` y
`frontend/tests/{unit,e2e}/`; evidencia en
`specs/001-visualizar-consumo-categorias/validation/`. Las migraciones usan el framework
existente de 009 y un nombre generado sobre el head real, sin reservar IDs globales.

## Gates externos por capacidad

| Gate | Propietario y contrato | Cuándo se necesita / rutas previstas |
| --- | --- | --- |
| Plataforma | [009 plan](../009-fundaciones-plataforma/plan.md), [eventos](../009-fundaciones-plataforma/contracts/integrations.md) | Antes de persistencia/integración: `core/`, `audit/`, `main.py`, herramientas, Alembic y PostgreSQL real. No crearlos en setup de 001. |
| Identidad | [006 spec](../006-acceso-usuarios-rbac/spec.md) | Antes de HTTP/E2E: `identity/`, sesión, CSRF, permisos y layout administrativo existentes. Dobles solo para pruebas aisladas. |
| Almacenamiento | [002 spec](../002-registro-retencion-consumo/spec.md), [integración acordada](contracts/integrations.md) | Antes de ejecutar las pruebas de T015 y completar T018..T020/aceptación US1: `consumption/reception.py`, proveedor de `MeasurementStore` incluido `read_reconfiguration_bounds`, incorporación calculada y pendientes reales; primera configuración sin revisiones previas puede preceder al proveedor. Recepción/almacenamiento y pendientes reales están disponibles; consultas agrupadas, proveedores consumidores y retirada protegida también están disponibles. No ejecutar tareas de 002 desde aquí. Escribir las pruebas contra puertos no requiere esperar ese proveedor. |
| Recepción física | [003 spec](../003-simulador-pas600-sftp/spec.md) | Antes de la prueba SFTP T056: adaptador nativo y receptor local provistos por 003. El fixture del puerto no acredita SFTP. |
| Emisión técnica | [007 spec](../007-observabilidad-externa/spec.md) | Antes de T054 y pruebas técnicas T056: `observability/` y perfiles locales propios; visores caídos no bloquean consultas. |
| Correo de prueba | [008 plan](../008-notificaciones-programables/plan.md) | Solo integración transversal T056: SMTP/Mailpit locales de 008; no es prerrequisito del MVP de consumo. |
| VPS | [009 operación](../009-fundaciones-plataforma/quickstart.md), [006 HTTPS](../006-acceso-usuarios-rbac/spec.md) | Solo T060: entorno real, dominio/HTTPS y cuentas; no contratar/provisionar infraestructura desde tareas 001. |

Si falta una capacidad, conservar pendientes las tareas que la consumen y continuar con
trabajo independiente. No sustituirla por una implementación dentro de 001 ni declarar
integración con dobles. Las pruebas puras de dominio pueden avanzar sin identidad/SFTP.

## Phase 1: Setup de la funcionalidad

**Purpose**: preparar el módulo sobre la plataforma existente, sin recrear infraestructura.

- [X] T001 Comprobar los gates externos, registrar capacidad real, documento, ruta, revisión y faltantes en `specs/001-visualizar-consumo-categorias/validation/prerequisites.md`; verificar plataforma antes de escribir código dependiente y distinguir pruebas puras, integración local, aceptación humana y VPS sin marcar capacidades por encontrar archivos.
- [X] T002 Crear únicamente los paquetes propios de consumo en `backend/src/ecs_ec/consumption/__init__.py`, `backend/tests/unit/consumption/__init__.py`, `backend/tests/integration/consumption/__init__.py` y `backend/tests/contract/consumption/__init__.py`, usando Python `>=3.14,<3.15` y las herramientas existentes de 009; preparar carpetas frontend previstas en el plan sin crear otro servidor.
- [X] T003 Añadir y fijar `decimal.js` en `frontend/package.json` y `frontend/package-lock.json` usando npm, registrar versión/licencia y regeneración en `specs/001-visualizar-consumo-categorias/quickstart.md`; reutilizar React 19/Next 16 y las herramientas de pruebas existentes, sin biblioteca de gráficos ni dependencias nuevas de infraestructura.
- [X] T004 [P] Preparar entradas y resultados esperados independientes en `backend/tests/fixtures/consumption/scenarios.json` y cargador documentado `backend/tests/unit/consumption/conftest.py`: siete categorías y subconjuntos, tres intervalos por categoría, unidades mixtas, 100 frente a parciales 60, 12+8=20, cero, positivo minúsculo, huecos y revisiones; usar zona/IDs sintéticos explícitos, sin escribir directamente tablas de mediciones. Añadir fixtures independientes de revisión ajena/propia, firma CAT-01 cambiante, límites históricos conservados y fronteras numéricas q=10^-15, M=10^30-q, seis M, valores exteriores y equivalentes en las tres unidades.

**Checkpoint**: paquete propio preparado y faltantes externos documentados; T003 y T004
pueden avanzar sobre T002, con manifiestos compartidos editados secuencialmente.

## Phase 2: Foundational — catálogo, configuración y puertos compartidos

**Purpose**: entregar el modelo y configuración que necesitan ambas historias P1 y que
002 puede consumir antes de completar la UI de 001. Plataforma real requerida para DB.

### Pruebas primero

- [X] T005 [P] Escribir `backend/tests/unit/consumption/test_catalog.py` para catálogo fijo CAT-01..07, nombres/alcances de FR-001, HVAC/ACS conjunto, sanitario eléctrico, orden, subconjuntos y base CAT-01; comprobar que ausencia de fuente nunca implica cero ni que CAT-01 contribuya a su suma. Verificar revisión de categoría estable ante etiqueta/cambio ajeno, incremento ante cambio propio/restauración, y firma CAT-01 física independiente de parciales frente a firma calculada sensible a su base/fuentes.
- [X] T006 [P] Escribir `backend/tests/integration/consumption/test_configuration.py` con PostgreSQL real para primera vigencia histórica, siete entradas únicas, fuente conocida/no reutilizada, revisiones concurrentes, cambio sin efecto, vigencia al aplicar, zona inmutable con datos, intervalo cruzado y rollback de configuración/auditoría/eventos; aislar explícitamente el estado de mediciones tras su puerto para esta prueba de configuración propia, sin implementar tablas de 002. La carrera conjunta con recepción real se verifica después en T018. Diferenciar cruce global ajeno válido y cambio propio incompatible; comprobar null por ausencia real frente a error de proveedor/claves incompletas, máximos por categoría incluida CAT-01 calculada y zona protegida después de retirar detalle. Aislar el proveedor 002 en la prueba propia y ejecutar su integración real en T018.
- [X] T007 [P] Escribir `backend/tests/contract/consumption/test_internal_ports.py` para los objetos y garantías de `MeasurementValidator`, `TotalCalculator`, `Reception` y `MeasurementStore`: aceptar/duplicar/rechazar por registro, referencias/revisiones conservadas, lectura sin efectos y UoW/corte compartidos; separar prueba aislada de contrato de su futura ejecución con proveedor real 002. Añadir contrato de read_reconfiguration_bounds: claves completas, null solo si nunca incorporó, indicador global persistente, máximos físicos/calculados conservados y error ante ausencia/fallo; comprobar category_revision y diagnósticos de cambio con sus segmentos.

### Implementación compartida

- [X] T008 Definir el dominio compartido en `backend/src/ecs_ec/consumption/models.py` y catálogo en `backend/src/ecs_ec/consumption/catalog.py`, copiando nombres/alcances de la spec y restricciones del modelo: "UUID de aplicación", "revisiones enteras positivas", "instantes UTC `timestamptz`", "precisión temporal hasta microsegundos", `BuildingContext` con "`id: UUID`, `name: str`, `timezone: IANA`, `created_at: instant`", categoría con "`id: CAT-01..CAT-07`" y "`display_order: 1..7`"; zona obligatoria, catálogo no editable y ningún esquema de múltiples edificios. Añadir category_revision positiva, monotónica por edificio/categoría e inicial 1; configuración global de auditoría separada de vigencias por categoría y de la firma modo/base/fuentes CAT-01, incluyendo cambios de vuelta sin reutilizar revisiones antiguas.
- [X] T009 Definir interfaces/DTO en `backend/src/ecs_ec/consumption/ports.py` sin importar implementaciones 002: `normalize`, `evaluate`, `accept`, `read_detail`, `read_extent`, `read_update_state` y `read_reconfiguration_bounds(building_id, category_ids, unit_of_work)`; este último devuelve `has_accepted_history: bool` y `latest_interval_end_by_category: {category_id: instant|null}`, con todas las claves solicitadas, límites conservados tras retirada de detalle y error ante proveedor ausente/fallido o respuesta incompleta. ValidatedMeasurement conserva originales, "`start < end`; intervalo `[start,end)`", revisión global vigente en start y `category_revision` positiva estable; energía "`0 <= E < 10^30 kWh`, múltiplo exacto de `10^-15 kWh`". ReceptionResult conserva `accepted|duplicate|rejected`, referencias y campos nullable del modelo. Las lecturas compuestas admiten UoW REPEATABLE READ/corte; la comprobación de reconfiguración usa READ COMMITTED y estado actual bajo bloqueos en UoW de escritura. Proveedores, IDs y primera incorporación pertenecen a 002.
- [X] T010 Implementar solo tablas de contexto/catálogo/fuentes/revisiones en `backend/src/ecs_ec/consumption/catalog_storage.py` y generar su migración en `backend/migrations/versions/`, enlazada al head real y con nombre real registrado en `specs/001-visualizar-consumo-categorias/validation/prerequisites.md`; conservar identidad/etiqueta de `MeasurementSource`, actor/proceso y fechas de `InstallationRevision`, "`effective_until` se obtiene de la siguiente revisión, sin mutar la revisión anterior", y "Referencias históricas se protegen contra eliminación en cascada". No crear tablas de mediciones, totales, recepción o retención de 002. Persistir category_revision en los snapshots propios y derivar su fin de la siguiente revisión de esa categoría; un cambio global ajeno conserva su revisión. Los máximos históricos y has_accepted_history del nuevo puerto siguen siendo almacenamiento de 002.
- [X] T011 Implementar configuración transaccional en `backend/src/ecs_ec/consumption/configuration.py` y `backend/src/ecs_ec/consumption/catalog_storage.py`: "Siete entradas únicas por revisión", "Con medidor, origen obligatorio y único dentro de la revisión; sin medidor, `source_id=null`", base ordenada CAT-02..07 y base vacía válida. Conservar revisión global de auditoría y `category_revision` positiva por categoría: solo presencia/fuente propia cambia una parcial; CAT-01 física depende de su fuente y calculada de modo/base/pares categoría-fuente; etiquetas o cambios ajenos no incrementan su revisión. Vigencia al aplicar, sin retroactividad/programación. Tras bloquear contexto/configuración → categorías ordenadas, consultar `read_reconfiguration_bounds` de 002 en la misma UoW de escritura, incluyendo CAT-01 si cambia su firma; impedir cambio anterior a máximos aceptados y cambio de zona con historia aceptada incluso retirada. Proveedor ausente/fallido o claves incompletas impide modificar; primera configuración sin revisiones puede preceder a 002. Auditoría/eventos comunes atómicos; no-op no crea revisión ni evento; no invalidar lecturas por un cruce global ajeno.
- [X] T012 Proveer inicialización controlada de `BuildingContext` y configuración inicial en `backend/src/ecs_ec/consumption/bootstrap.py` usando los servicios de T011 y ajustes propios en `backend/src/ecs_ec/consumption/configuration.py`; documentar provisión de zona, identidad del proceso y fuentes por entorno en `specs/001-visualizar-consumo-categorias/quickstart.md`. No crear cuentas, rutas públicas de seed ni flags de reloj; pasar T005..T007 con el alcance aislado/integrado identificado. Distinguir bootstrap sin revisiones previas de modificaciones posteriores: solo el primero precede al proveedor 002; un no-op no crea revisiones. No completar los contratos funcionales de validación/cálculo aún no implementados: su ejecución real corresponde a T018, manteniendo aquí solo el alcance aislado de DTO/puertos.

**Checkpoint**: reglas/puertos/configuración de 001 disponibles para 002. El gate de
almacenamiento puede completarse en su propia spec sin esperar la aceptación de US1.
Las historias comienzan con esta base; no requieren correo ni visores.

## Phase 3: User Story 2 — Recibir mediciones separadas y confiables (P1)

**Goal**: suministrar reglas puras y conectar la recepción real de 002, conservando
origen/unidad/intervalo y resultados por registro. Se adelanta US2 entre las dos P1 por
la dependencia de datos de US1; no cambia las prioridades de la especificación.
**Independent Test**: sin gráficos, enviar por `Reception.accept` lotes válidos/mixtos y
reenvíos; verificar resultados y conjunto persistido contra valores conocidos, incluidas
concurrencia y contigüidad. La incorporación temporal de CAT-01 la realiza 002.

### Pruebas primero

- [X] T013 [P] [US2] Escribir `backend/tests/unit/consumption/test_validation.py` para Wh/kWh/MWh, equivalencia decimal exacta, cero y positivo `0.000001 Wh`, no finitos/negativos/booleanos, categorías/orígenes desconocidos, fechas sin offset o precisión no representable, unidades incompatibles y rango invertido; conservar originales y rechazar desbordes explícitamente sin imponer límites físicos inventados (FR-002/003/010). Añadir q=10^-15 kWh, M=10^30-q, cero, 10^-16 kWh, 10^30 kWh y valor no múltiplo de q; probar mismos resultados en Wh/kWh/MWh, ceros finales/exponentes equivalentes y mínimo 10^-12 Wh = 10^-15 kWh = 10^-18 MWh. Validar revisión ajena estable y cambio propio dentro del intervalo, incluido cambio justo en start/end.
- [X] T014 [P] [US2] Escribir `backend/tests/unit/consumption/test_totals.py` con base vacía/no vacía, 12+8=20, ceros, falta/invalidez de una contribución, intervalos desalineados, cambio de revisión y CAT-01 física 100 frente a parciales 60; no sustituir su lectura ausente, no aceptar CAT-01 como contribución ni repartir/sumar subintervalos para fabricar una contribución exacta (FR-006). Añadir seis contribuciones M y resultado exacto 6*M sin techo individual, firma calculada estable a través de revisiones globales ajenas y cambio modo/base/fuente contribuyente con diagnóstico calculation_configuration_changed, sin valor y con segmentos conservados.
- [X] T015 [P] [US2] Escribir `backend/tests/integration/consumption/test_measurement_semantics.py` contra los puertos acordados para recepción/DB reales de 002: subconjuntos, registros fuera de orden, `1000 Wh` frente a `1 kWh` duplicado, conflicto 2 kWh sin sobrescritura, solapamiento por categoría incluso al cambiar fuente, contigüidad, duplicados dentro del lote, rechazo mixto y carreras concurrentes; comprobar primera aceptación/originales/eventos y que duplicados/rechazos no reinicien el límite (FR-002..006/010, SC-003). Redactarlas antes de T016/T017; su ejecución integrada espera gate Almacenamiento, sin bloquear esas reglas puras ni usar ausencia de proveedor como fallo de comportamiento. Verificar físicamente una lectura que cruza revisión global ajena y conserva category_revision, cambio propio source_configuration_changed, cambio de firma CAT-01 sin pérdida de parciales y fronteras equivalentes energy_out_of_supported_range.

### Implementación e integración

- [X] T016 [P] [US2] Implementar `MeasurementValidator.normalize` en `backend/src/ecs_ec/consumption/validation.py` tras escribir T013..T015: resolver todos los segmentos de la categoría en "`start < end`; intervalo `[start,end)`", conservar revisión global de inicio y `category_revision` positiva estable; cruce global ajeno válido y cambio propio `source_configuration_changed`. Convertir exactamente Wh × 0.001, kWh × 1, MWh × 1000 desde texto y validar "`0 <= E < 10^30 kWh`, múltiplo exacto de `10^-15 kWh`"; fuera de dominio `energy_out_of_supported_range` sin redondeo. Canonicalizar ceros insignificantes antes de operar, preservar original/evidencia y usar contexto Decimal 50 con detección de Inexact/Rounded/operación inválida/mezcla float. Mantener rechazos de T013 y microsegundos; no escribir, aceptar ni sobrescribir aquí.
- [X] T017 [P] [US2] Implementar `TotalCalculator.evaluate` en `backend/src/ecs_ec/consumption/totals.py` tras escribir T013..T015: `TotalCandidate` con `category_id=CAT-01`, `energy_kwh|null`, `status: complete|incomplete|no_basis`, `category_revision: int|null`, motivo y segmentos. Base no vacía estable y todas las contribuciones exactamente alineadas suman una sola vez, con ID/revisión/origen/revisión de categoría; ninguna CAT-01 contribuye. Si la firma calculada cambia en el intervalo, devolver incomplete y `calculation_configuration_changed`, `category_revision=null`, sin valor/base única/contribuciones/faltantes fingidos, conservando segmentos. Cruce global ajeno permite cálculo. Usar precisión 50 y admitir hasta `6*(10^30-10^-15) kWh` inclusive, sin aplicar el máximo individual; cero exige base válida, fuente física excluye sustitución. No usar reloj, commit, scheduler ni incorporación desde GET.
- [X] T018 [US2] Con gate Almacenamiento satisfecho, conectar reglas 001 al proveedor real de recepción/incorporación de 002 mediante la composición existente en `backend/src/ecs_ec/main.py` y exportaciones de `backend/src/ecs_ec/consumption/ports.py`; ejecutar T015, contrato real T007 y carrera configuración/recepción de T006 verificando identidad de reenvío edificio/origen/categoría/inicio/fin UTC, exclusión transaccional y resultados parciales. Verificar 14m59 s/15m, candidatos CAT-01 pendientes y reevaluación/reinicio provistos por 002; cualquier faltante queda en su spec, sin implementar `reception.py`, almacenamiento ni trabajos de 002 desde 001. Integrar también read_reconfiguration_bounds real: comprobar ambas órdenes de la carrera recepción/reconfiguración, máximos por categoría física/calculada tras retiro de detalle permitido y fallo/ausencia/clave incompleta sin modificación parcial. Comprobar revisión ajena aceptada, cambio propio rechazado, cambio calculado diagnosticado y suma máxima 6*M.
- [X] T019 [US2] Implementar `Consumption.source_status` en `backend/src/ecs_ec/consumption/queries.py` sobre configuración 001 y `read_update_state` real 002, con categoría/corte/revisión, presencia física o fuente lógica, base, última aceptación/incorporación nueva y próxima admisible; conservar ausencia de fecha como null y comprobar que duplicados/rechazos no simulen novedades ni que 15 minutos se interpreten como SLA de llegada. Incluir category_revision positiva o null sin configurar; cambios globales ajenos/etiquetas no simulan una nueva fuente ni una aceptación.
- [X] T020 [US2] Ejecutar pruebas puras y de integración US2, reiniciar app/DB y verificar originales/resultados conservados, equivalencia sin duplicación y ninguna aceptación/evento durable ante fallo de commit; registrar comandos, versiones, datos y resultados observados de FR-002..006/010 y SC-003 en `specs/001-visualizar-consumo-categorias/validation/us2.md`. No dar por completa US2 con dobles del proveedor 002.

**Checkpoint**: US2 verificable sin frontend; reglas puras no esperan otras historias,
aceptación durable exige 002. Ningún formato nativo PAS600 se modifica.

## Phase 4: User Story 1 — Consultar cada categoría mediante gráficos y tablas (P1, MVP visible)

**Goal**: entregar siete opciones, gráfico/tabla exactos y configuración de instalación,
con total medido o calculado identificado. Requiere datos confiables US2 y gates de
Almacenamiento/Identidad, sin exigir SFTP/SMTP para la prueba por puerto local.
**Independent Test**: cargar tres intervalos conocidos por categoría mediante recepción
real y consultar instalaciones completas/parciales; comparar ambas vistas con origen,
unidades y período. CAT-01 física =100 y calculada =20 en escenarios separados.

### Pruebas primero

- [X] T021 [P] [US1] Escribir `backend/tests/contract/consumption/test_http.py` para las cuatro operaciones de `specs/001-visualizar-consumo-categorias/contracts/openapi.json`: catálogo/detalle y GET/PUT de configuración, ejemplos válidos y campos inválidos, sesión/roles actuales, renovación pendiente, origen/CSRF, `Cache-Control: no-store` incluso en errores y respuestas Problem saneadas; Operador no lee configuración y Programador no obtiene permisos funcionales. Comprobar esquemas diferenciados de energía individual/calculada/original, category_revision derivada de servidor en salidas y rechazada en PUT, y diagnóstico calculation_configuration_changed con campos consistentes; fallo del proveedor de límites al modificar devuelve 503.
- [X] T022 [P] [US1] Escribir `backend/tests/integration/consumption/test_detail_queries.py` para catálogo de siete, período inicial global, origen/base por fila/segmento, detalle cronológico y captura coherente REPEATABLE READ/corte con actualización concurrente; GET nunca incorpora/recalcula CAT-01, modifica retención o produce eventos de aceptación (FR-001/006..010, SC-001/002). Añadir fila que atraviesa dos revisiones globales con la misma category_revision y configuration_revision global de inicio; comprobar snapshot/base por segmento sin reescritura de historia.
- [X] T023 [P] [US1] Escribir pruebas de precisión/presentación en `frontend/tests/unit/consumption/format.test.ts`, `frontend/tests/unit/consumption/EnergyChart.test.tsx` y `frontend/tests/unit/consumption/EnergyTable.test.tsx`: mismos intervalos/cadenas de respuesta en tabla/tooltip/etiqueta accesible, una sola lectura, todos ceros, positivo minúsculo, base y contribuciones; datos esperados independientes de los componentes.
- [X] T024 [P] [US1] Escribir escenario inicial de `frontend/tests/e2e/consumption.spec.ts` y preparación controlada en `frontend/tests/e2e/consumption.setup.ts` sobre DB separada, usuarios reales 006 y semillas por servicios/puerto reales: tres intervalos por categoría, subconjunto instalado, CAT-01 100 frente a 60 y 12+8=20; build estático sin datos privados y acceso por ambos perfiles (SC-001/002, US1 escenarios 1..6).

### Implementación e integración

- [X] T025 [US1] Implementar esquemas HTTP en `backend/src/ecs_ec/consumption/schemas.py` conforme al OpenAPI/modelo: siete categorías únicas, revisión global positiva salvo expected_revision=0 inicial, category_revision calculada por servidor (nullable en catálogo sin configurar), y "Con medidor, UUID/etiqueta no vacíos; sin medidor ambos null". Separar cadenas de originales, dominio individual `0 <= E < 10^30`/quantum `10^-15 kWh` y dominio calculado inclusivo `6*(10^30-10^-15)`; nunca imponer techo individual al total. Añadir revisión de categoría a filas/contribuciones/segmentos y motivos diagnósticos con restricciones null/segmentos/faltantes/fecha del modelo. GET configuración añade category_revision; PUT la rechaza como campo adicional y admite effective_from nullable con vigencia T011. Conservar campos obligatorios, offsets/microsegundos, origen discriminado y Problem saneado.
- [X] T026 [US1] Completar catálogo y consulta de detalle en `backend/src/ecs_ec/consumption/queries.py` con `read_extent`/`read_detail` reales, UoW compartida y corte: devolver `request_ref`, edificio/categoría/período/zona, `configuration_segments`, `rows`, `diagnostics` y `warnings`; conservar valores incorporados, originales o base/contribuciones y "En HTTP `first_incorporated_at` unifica primera aceptación física o incorporación calculada". Período inicial min inicio/max fin global o día actual del edificio; orden UTC, sin truncamiento/downsampling ni tablas espejo.
- [X] T027 [US1] Implementar las cuatro rutas en `backend/src/ecs_ec/consumption/router.py` delegando consulta/configuración a servicios existentes y autorización/CSRF a 006; exigir selección explícita de zona/período y estado de cuenta vigente, GET configuración inexistente 404, conflicto de revisión 409 y validación 422. Reutilizar error común 009 con `code`, `detail`, `operation_ref`, `field_errors`, sin secretos; ningún endpoint de inyección, modificación de mediciones o gestión de cuentas.
- [X] T028 [US1] Implementar cliente/tipos de las cuatro operaciones en `frontend/src/lib/api/consumption.ts` desde OpenAPI, conservando energía como cadenas, fechas textuales y revisiones, sesión común 006 y respuestas sin caché; documentar origen/procedimiento si genera código y manejar Problem sin exponer detalles técnicos. El cliente no recalcula energía ni totales. Incorporar tipos de category_revision, basis_sources y diagnóstico calculation_configuration_changed; excluir campos derivados de servidor de los cuerpos PUT y mantener dominios individuales/calculados como cadenas.
- [X] T029 [US1] Implementar formato compartido en `frontend/src/components/consumption/format.ts` para tabla, tooltip y etiquetas: conservar precisión decimal íntegra y microsegundos textuales, zona IANA/offset del edificio y unidad kWh; usar `decimal.js` solo para razones geométricas acotadas, sin `Number(value).toFixed`, redondeo distinto por vista o conversión de positivo a cero. Verificar etiquetas exactas para q, M y 6*M; configurar precisión 50 para proyección decimal local, sin redondear las cadenas de negocio.
- [X] T030 [P] [US1] Tras T028/T029, crear `frontend/src/components/consumption/EnergyChart.tsx` como SVG de intervalos independientes de una sola respuesta, con nombre/descripción y acceso por foco/tooltip al valor exacto e inicio/fin; representar una lectura, cero y marcador diferenciado para positivo inferior al píxel, mantener huecos y escala visible en todos ceros, sin interpolar ni reducir registros (FR-007/009/010/015).
- [X] T031 [P] [US1] Tras T028/T029, crear `frontend/src/components/consumption/EnergyTable.tsx` con tabla HTML semántica y encabezados inicio/fin/kWh/procedencia, mismos registros/valores que el gráfico y detalles de originales o contribuciones; mostrar "Total medido" o "Total calculado de las categorías presentes", base por revisión y advertencia de cargas no cubiertas sin inventar filas (FR-008..010).
- [X] T032 [P] [US1] Tras T028/T029, crear `frontend/src/components/consumption/CategorySelector.tsx` con siete opciones fijas y nombres distinguibles, todas seleccionables sin importar medidor/datos; mostrar presencia/modo recibidos del catálogo y distinguir "Sin medidor" en las parciales ausentes, conservar el período del contenedor y no inferir presencia de fuente ni enviar una consulta de otra categoría.
- [X] T033 [P] [US1] Tras T028/T029, crear `frontend/src/components/consumption/ConfigurationForm.tsx` para Administrador con siete entradas, fuentes UUID/etiquetas, zona/vigencia inicial explícitas y base CAT-01 derivada por servidor; admitir medidores ausentes/base vacía, revisión esperada, vigencia de servidor en cambios y recarga ante conflicto, sin campos de credenciales SFTP ni modificación de mediciones. Mostrar categorías cuya firma cambia sin tratar etiquetas como cambio de fuente; conservar configuración ante fallo 503 del proveedor de límites. category_revision es salida derivada y no se envía en PUT.
- [X] T034 [US1] Montar consulta en `frontend/src/components/consumption/ConsumptionView.tsx` y `frontend/src/app/consumption/page.tsx` usando catálogo inicial CAT-01, un único resultado para ambas representaciones y encabezado categoría/energía/kWh/período/zona/offset; cargar solo en cliente tras autorización, conservar filtro al alternar categoría/representación y no incrustar datos privados en export estático. Dar comportamiento básico seguro de carga/vacío hasta completar US4.
- [X] T035 [US1] Registrar router/proveedores en el `backend/src/ecs_ec/main.py` existente y montar formulario en `frontend/src/app/administration/consumption/page.tsx`, ampliando el layout administrativo existente de 006 en `frontend/src/app/administration/layout.tsx` solo para navegación autorizada; verificar API/URL directa y frontend servido por FastAPI. No crear autenticación, layout base o composición general ausentes: mantener el gate de su propietario.
- [X] T036 [US1] Ejecutar T021..T024 con PostgreSQL, recepción e identidad reales y verificar gráfico/tabla contra las tres lecturas conocidas por categoría y los dos modos CAT-01; registrar precisión, procedencia, intervalos, preparación local y resultados FR-001/006..010, SC-001/002 en `specs/001-visualizar-consumo-categorias/validation/us1.md`. La aceptación humana y VPS permanecen en T059/T060.

**Checkpoint**: MVP visible local con reglas/recepción US2 y siete consultas verificables;
no afirmar completitud P2 ni aceptación SFTP/humana/VPS a partir de esta demostración.

## Phase 5: User Story 3 — Consultar un período específico (P2)

**Goal**: seleccionar período sin perder la última consulta válida ni mezclar categorías,
con contención completa y fechas inequívocas en zona del edificio.
**Independent Test**: datos antes/dentro/después y cruzados, cambio de categoría/rango y
dos horas repetidas; ambas vistas mantienen exactamente el filtro y los datos esperados.

### Pruebas primero

- [X] T037 [P] [US3] Escribir `backend/tests/unit/consumption/test_periods.py` para `start < end`, offsets válidos en zona IANA, hora repetida con dos instantes distintos, hora inexistente, microsegundos, medianoche local y día actual sin historia; rechazar fechas ambiguas sin resolución y no aplicar la política de aniversario de retención al formulario.
- [X] T038 [P] [US3] Escribir `backend/tests/integration/consumption/test_detail_periods.py` para contención exacta, cruces de ambos límites contados una vez, todas las lecturas excluidas, filtros de diagnósticos, datos de varias categorías/revisiones y período inicial global; rechazos de selección no modifican datos ni conservación (FR-011..013). Verificar contención y exclusión avisada de diagnósticos calculation_configuration_changed, con segmentos explícitos; un cruce de revisión global ajena no excluye una lectura válida del período.
- [X] T039 [P] [US3] Escribir `frontend/tests/unit/consumption/PeriodForm.test.tsx` para borrador frente a último rango válido, inicio igual/posterior al fin, selección de offset en repetición estacional, conservación al cambiar categoría/representación y navegador con otra zona; un rango inválido conserva la consulta válida y explica cómo corregirlo.

### Implementación e integración

- [X] T040 [US3] Implementar validación/resolución de período en `backend/src/ecs_ec/consumption/periods.py` y conectarla a `backend/src/ecs_ec/consumption/schemas.py`: "`start < end`; intervalo `[start,end)`", zona del edificio, ida/vuelta con ZoneInfo y offset explícito, precisión hasta microsegundos sin truncamiento, rechazo de inexistencia/ambigüedad no resuelta y fechas de consulta devueltas con offset del edificio.
- [X] T041 [US3] Completar filtro/avisos de detalle en `backend/src/ecs_ec/consumption/queries.py` y su conexión en `backend/src/ecs_ec/consumption/router.py`, usando puertos 002 para incluir solo inicio >=inicio seleccionado y fin <=fin seleccionado, excluir/contar cruces una vez también en diagnósticos y avisar incluso con conjunto vacío; no recortar, prorratear o modificar el filtro ni publicar agregados hora/día/mes/año desde este endpoint.
- [X] T042 [US3] Crear `frontend/src/components/consumption/PeriodForm.tsx` e integrarlo en `frontend/src/components/consumption/ConsumptionView.tsx` con borrador separado de selección válida, offset del edificio explícito y avisos del servidor; preservar período al cambiar categoría/representación y mantener última consulta válida ante errores del rango, sin normalizar silenciosamente una hora inexistente.
- [X] T043 [US3] Ampliar `frontend/tests/e2e/consumption.spec.ts` con selección antes/dentro/después, intervalo cruzado, rango inválido, cambio de categoría, dos offsets de una hora repetida y contexto de navegador en otra zona; comparar límites/valores del gráfico y tabla y confirmar exclusión avisada sin prorrateo.
- [X] T044 [US3] Ejecutar T037..T039/T043 y registrar fixtures, zona/tzdata, límites/offsets, consulta inicial global y resultados FR-011..013, SC-002/004 en `specs/001-visualizar-consumo-categorias/validation/us3.md`; comprobar que el reloj/zona del navegador o VPS no sustituyen los del edificio.

**Checkpoint**: US3 verificable sobre datos conocidos de US1/US2; sin incorporar la
agrupación/retención de 002 dentro de tareas de período de 001.

## Phase 6: User Story 4 — Reconocer ausencia de datos y fallos de consulta (P2)

**Goal**: distinguir carga, disponible, sin medidor, sin datos, total incompleto y error,
preservando cero válido y evitando resultados de una petición anterior.
**Independent Test**: escenarios de fuente ausente/instalada sin datos, cero, huecos,
base incompleta/vacía, CAT-01 física sin lectura y errores/respuestas tardías A→B; la
persona identifica el estado y puede consultar otra categoría o reintentar.

### Pruebas primero

- [X] T045 [P] [US4] Escribir `backend/tests/integration/consumption/test_detail_states.py` para cero físico/calculado, parcial sin medidor, instalada sin lecturas, base vacía, contribución faltante/desalineada, filas válidas junto con diagnósticos, CAT-01 pendiente temporalmente y física con hueco pese a parciales; comprobar estados/razones sin energía ficticia, fallos de DB distintos de respuesta sin datos y transición a 20 tras incorporación permitida real de 002. Añadir cambio calculado con category_revision null, segmentos con revisiones distintas, sin faltantes ni fecha próxima ficticios y parciales consultables; revisión global ajena sigue permitiendo el total y seis M conserva 6*M.
- [X] T046 [P] [US4] Escribir `frontend/tests/unit/consumption/useConsumptionQuery.test.tsx` para carrera A→B, respuesta ya resuelta tras abort, reintento/error de B, navegación a categoría disponible y vencimiento/cierre de sesión; ninguna respuesta con clave/generación anterior puede publicarse como selección actual (FR-014/016).
- [X] T047 [P] [US4] Escribir `frontend/tests/unit/consumption/QueryState.test.tsx` para las seis presentaciones de carga/disponible/sin medidor/sin datos/incompleto/error, base vacía y pendiente de incorporación con razón propia; verificar texto además de color, acción Reintentar por teclado y diagnósticos separados de las filas numéricas (FR-014/015, SC-004). Añadir texto de cambio de configuración calculada y segmentos, distinguiéndolo de categorías faltantes y espera hasta próxima incorporación.

### Implementación e integración

- [X] T048 [US4] Completar estados/diagnósticos en `backend/src/ecs_ec/consumption/queries.py` y `backend/src/ecs_ec/consumption/schemas.py` con "`state: available|no_meter|no_data|incomplete`" y "`source_mode: measured|calculated|mixed|unavailable`"; prioridad incompleto → filas disponibles → parcial sin fuente todo el período → sin datos. Distinguir `missing_contributions`, `pending_incorporation` y `calculation_configuration_changed`: este último tiene category_revision null, faltantes vacíos, próxima fecha null y segmentos que cubren el intervalo con al menos dos revisiones CAT-01, modo/base/fuentes por segmento. Otros diagnósticos conservan revisión positiva y sus campos específicos. Conservar filas válidas, base vacía no_calculation_basis, huecos/cruces/alcance y conteos no negativos; no fabricar valores ni invocar cálculo/incorporación desde GET.
- [X] T049 [US4] Implementar `frontend/src/components/consumption/useConsumptionQuery.ts` con clave categoría/inicio/fin/zona y generación, invalidación inmediata al aceptar nueva selección válida, AbortController y descarte adicional de respuestas obsoletas, reintento ligado a selección actual y limpieza de datos al cerrar/vencer sesión; sin localStorage de datos privados ni streaming/refresco automático no especificado.
- [X] T050 [US4] Crear `frontend/src/components/consumption/QueryState.tsx` con mensajes de estado compartidos por ambas vistas, diagnóstico de categorías faltantes o incorporación pendiente, aviso de base vacía y acción de reintento; cero válido permanece dato y CAT-01 física sin lectura muestra "Total medido"/"Sin datos", sin suma sustituta ni filas/series de diagnóstico numéricas. Para calculation_configuration_changed mostrar "Cambió la configuración de cálculo dentro del intervalo" con modo/base/fuentes por segmento, sin faltantes ni fecha de reintento temporal inventados.
- [X] T051 [US4] Integrar hook/estados en `frontend/src/components/consumption/ConsumptionView.tsx` y `frontend/src/app/consumption/page.tsx`, ocultando resultados anteriores durante carga/error de nueva selección y manteniendo filas válidas cuando haya diagnósticos de otros intervalos; permitir otra categoría independientemente de error/ausencia de la anterior y conservar el último rango válido de US3.
- [X] T052 [US4] Ampliar `frontend/tests/e2e/consumption.spec.ts` con todos los escenarios US4, retraso A→B, error/reintento, hueco visible, un único dato, cero y positivo minúsculo, llegada tardía que completa total y CAT-01 física sin sustitución; contrastar cada cifra/intervalo con fixture y verificar foco/teclado sin depender solo de color. Añadir flujos de cambio global ajeno aceptado, fuente propia cambiada rechazada y base calculada cambiante con parciales visibles; verificar q, M y 6*M íntegros en gráfico/tabla.
- [X] T053 [US4] Ejecutar T045..T047/T052 y registrar estados observados, secuencias de solicitudes, datos numéricos permitidos y resultados FR-014..016, SC-004 en `specs/001-visualizar-consumo-categorias/validation/us4.md`; comprobar con 002 que la espera temporal/recuperación del total no se resuelve mediante GET ni incorporaciones anticipadas. Registrar además resultados de los casos I1/U1/A1 aprobados: cambios ajenos/propios/calculados, límites bajo coordinación e individuales frente a total exacto máximo.

**Checkpoint**: cuatro historias verificadas localmente con dependencias reales;
aceptación transversal/humana/VPS aún requiere las tareas siguientes.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: cerrar evidencia y operación del módulo, sin implementar capacidades ajenas.

- [X] T054 Con gate Emisión técnica disponible, instrumentar solo operaciones propias en `backend/src/ecs_ec/consumption/telemetry.py` y conectarlas desde `backend/src/ecs_ec/consumption/router.py` usando emisor 007 existente; verificar con `backend/tests/integration/consumption/test_telemetry.py` correlación y saneamiento sin credenciales, cuerpos de entrada ni valores de consumo personales. No crear emisor común, recolectores o visores ni duplicar eventos de recepción de 002.
- [X] T055 Escribir y ejecutar `backend/tests/integration/consumption/test_availability_and_audit.py` con identidad/DB/auditoría reales para consultas con consumidor 008, SMTP y visores indisponibles, cambios de configuración/eventos atómicos, rollback y denegaciones administrativas conforme a 006; verificar `no-store`, ausencia de secretos y que ninguna consulta reinicie incorporación/retención, sin usar telemetría como prueba de cobertura funcional.
- [ ] T056 Con gates Recepción física/Emisión técnica/Correo de prueba satisfechos, ejecutar perfiles locales existentes de specs-003/007/008 con archivos nativos CSV/JSON por SFTP, receptor/visores locales y Mailpit; contrastar resultados de recepción y consultas de 001 con datos esperados, documentar sustitutos/contratos preservados y comandos en `specs/001-visualizar-consumo-categorias/validation/local-integrations.md` (FR-019, SC-006). No crear esos servicios ni equiparar fixture interno con aceptación SFTP.
- [X] T057 Ejecutar build/export estático y consulta con historial representativo completo, registrando cantidad de registros, medidas observadas y limitaciones en `specs/001-visualizar-consumo-categorias/validation/build-and-volume.md`; comprobar una imagen/proceso de aplicación, build sin datos privados, ausencia de servidor Node en runtime y ningún truncamiento/downsampling/paginado oculto. No inventar SLO ni completar esta tarea con una optimización no medida.
- [X] T058 Actualizar `specs/001-visualizar-consumo-categorias/quickstart.md`, `specs/001-visualizar-consumo-categorias/contracts/http.md`, `specs/001-visualizar-consumo-categorias/contracts/ui.md` y `deploy/README.md` existente con comandos reales, provisión de contexto/zona/fuentes por entorno, configuración autorizada, fallos/reintento e integración/operación propia de consumo; revisar docstrings/TSDoc de todo código/prueba propio y sincronía OpenAPI/cliente. No recrear operación común 009 ni marcar revisiones sin evidencia.
- [ ] T059 Realizar evaluación con personas representativas y registrar diez tareas de localizar categoría/comprobar consumo y período en gráfico/tabla en `specs/001-visualizar-consumo-categorias/validation/usability.md`: SC-005 requiere al menos 9/10 sin ayuda en <=60 segundos por tarea. Registrar tiempos/aciertos/estados; sin participantes o resultado suficiente, conservar aceptación pendiente, sin sustituirla por Playwright.
- [ ] T060 Con gate VPS disponible, verificar en el entorno ya provisto por sus propietarios acceso por HTTPS desde red externa con equipo de desarrollo apagado, una cuenta activa de cada perfil funcional, denegación sin sesión y mismas categorías/kWh/zona; registrar configuración sin secretos, comandos y resultados de FR-017/018 y SC-007 en `specs/001-visualizar-consumo-categorias/validation/vps.md`. No provisionar la VPS ni declarar este criterio a partir del entorno local.
- [ ] T061 Ejecutar los comandos reales de `specs/001-visualizar-consumo-categorias/quickstart.md` y checks exigidos por plataforma, recopilar evidencia de T020/T036/T044/T053/T054..T060 y cerrar matriz FR-001..FR-019/SC-001..SC-007 en `specs/001-visualizar-consumo-categorias/validation/acceptance.md`; registrar resultados observados, versiones/corte/zona y pendientes externos, humanos o VPS. Marcar únicamente trabajo efectivamente completado; ninguna generación documental acredita implementación o aceptación.

## Dependencies & Execution Order

### Dependencias de fases y gates

```text
Plataforma 009 real
  → Phase 1: T001..T004
  → Phase 2: T005..T012 (modelos/puertos/configuración 001)
       ├─→ T013/T014 → T016/T017 (reglas puras US2)
       └─→ proveedor real de almacenamiento/incorporación de spec-002
             + reglas US2 → T015/T018..T020 (US2 integrada, sin UI)
Identidad 006 real + US2 integrada
  → Phase 4: T021..T036 (US1, MVP visible local)
  → Phase 5: T037..T044 (US3, período)
  → Phase 6: T045..T053 (US4, estados/carreras)
  → Phase 7: T054..T061 (cierre con gates específicos)
```

002 depende de contratos/reglas iniciales de 001, **no** de su aceptación completa.
001 depende de su proveedor real para recepción persistida y consulta. La flecha a 002
expresa una capacidad externa, no autorización para ejecutar sus tareas aquí.

### Orden dentro de las fases

- Setup: T001 → T002 → T003/T004; la inicialización no crea infraestructura ajena.
- Foundation: escribir T005..T007 (DTO/puertos aislados aquí; proveedores reales en T018) → T008 → T009 → T010 → T011 → T012; corregir fallos
  de comportamiento antes del checkpoint. Concurrencia contra almacenamiento espera el
  proveedor 002; los contratos y reglas iniciales pueden entregarse antes.
- US2: escribir T013..T015 antes de T016/T017; T015 se redacta contra los puertos y se
  ejecuta cuando exista almacenamiento, sin bloquear las pruebas puras T013/T014 ni sus implementaciones.
  T016/T017 + gate Almacenamiento → T018 → T019 → T020. T019 vuelve a editar `queries.py`
  después del contrato estable; no se trabaja ese archivo en paralelo con US1/US3/US4.
- US1: escribir T021..T024 → T025 → T026 → T027 → T028 → T029 → T030..T033 → T034 →
  T035 → T036. T021/T024 necesitan Identidad para su ejecución integrada, además de 002.
- US3: escribir T037..T039 → T040 → T041 → T042 → T043 → T044.
- US4: escribir T045..T047 → T048 → T049 → T050 → T051 → T052 → T053.
- Cierre: T054/T055 después de historias y sus gates; T056 espera 003/007/008, T057/T058
  preparación local completa, T059 personas y T060 VPS real. T061 recopila todas las
  evidencias; no declarar aceptación final si alguna requerida sigue pendiente.

### Dependencias entre historias e independencia de prueba

| Historia | Depende de | Prueba independiente |
| --- | --- | --- |
| US2 P1 | Base 001 y proveedor 002 para aceptación durable; reglas puras entregables antes. | Recepción/resultado/DB sin gráficos ni otras historias. |
| US1 P1 | Reglas US2, almacenamiento 002 e identidad 006 reales. | Instalación y tres intervalos conocidos, comparación gráfico/tabla y procedencia. |
| US3 P2 | Consulta/UI de US1; no necesita los estados avanzados US4. | Filtrado temporal/DST contra datos conocidos, sin SFTP ni correo. |
| US4 P2 | Consulta/UI de US1 y selección válida US3 para carreras de categoría/período. | Fixtures de estado/error y respuestas controladas, contrastados con recepción real. |

La independencia se refiere al escenario observable, no a duplicar servicios/almacenamiento.
En archivos compartidos `main.py`, `models.py`, `ports.py`, `queries.py`, `schemas.py`,
`router.py`, `ConsumptionView.tsx`, el E2E y manifiestos, los cambios son secuenciales.
No incluir agregados/retención ni adaptadores de costos/PDF/notificaciones como tareas
ocultas de 001; sus contratos se conectan al incorporar a cada propietario.

## Parallel Opportunities & Examples

Solo los grupos siguientes comparten prerrequisitos completos y escriben archivos distintos;
no ejecutarlos a la vez que sus implementaciones ni que cambios de otra fase en esos archivos.

| Grupo | Ejemplo de ejecución paralela | Condición |
| --- | --- | --- |
| Foundation | T005 catálogo, T006 configuración, T007 puertos. | T001..T004 y herramientas/DB disponibles; son escritura de pruebas. |
| US2 pruebas | T013 validación + T014 totales + T015 semántica persistida. | Base completada para escribirlas; la ejecución integrada de T015 requiere almacenamiento real. |
| US2 implementación | T016 `validation.py` + T017 `totals.py`. | Tipos/contratos estables, pruebas escritas; no editar `models.py`/`ports.py` simultáneamente. |
| US1 pruebas | T021 HTTP + T022 consultas + T023 componentes + T024 E2E inicial. | Base, reglas y proveedores requeridos; cada tarea posee sus archivos de prueba. |
| US1 componentes | T030 gráfico + T031 tabla + T032 selector + T033 configuración. | T028/T029 completos; integración en contenedor/layout posterior y secuencial. |
| US3 | T037 fechas + T038 contención + T039 formulario. | US1 completa y fixtures estables; integración temporal posterior. |
| US4 | T045 estados del servidor + T046 respuestas tardías + T047 mensajes. | US1/US3 completas; T048..T051 van después de escribir pruebas. |

T004 puede prepararse junto a T003 después de T002. `[P]` no autoriza escrituras
simultáneas a manifiestos, migraciones con el mismo head ni registros de composición.

## Implementation Strategy

### MVP primero

Entregar base → reglas US2 para habilitar almacenamiento de 002 → recepción US2 real →
US1 con siete categorías/gráfico/tabla/configuración y procedencia exacta. Ese es el MVP
visible local; no basta una UI con datos ficticios. Validar T020/T036 antes de añadir P2.
Sin proveedor externo, avanzar reglas/componentes aislados y conservar la integración
pendiente, sin ampliar el alcance a otra spec.

### Entrega incremental y cierre

Añadir US3 para períodos y US4 para estados/carreras; luego verificar aislamiento,
instrumentación y los procedimientos locales. Integración SFTP/correo/visores, prueba
humana y VPS tienen gates distintos; mantenerlos visibles hasta conseguir resultados.
No publicar ni desplegar por generar esta lista. No marcar checklists por reorganizarla.

## Trazabilidad del traslado

Los identificadores de la columna izquierda pertenecen al **borrador anterior de spec-001**,
no a dependencias ejecutables ni a los nuevos números coincidentes.

| Procedencia | Alcance conservado | Tareas nuevas de spec-001 |
| --- | --- | --- |
| Borrador 001 T001; originalmente pruebas/validación de 008 | Unidades, finitud, fuente/categoría, equivalencia, conflicto y solapamiento/contigüidad. | T013, T015, T018, T020. |
| Borrador 001 T002; originalmente dominio de 008 | Catálogo/fuentes/semántica y CAT-01 sin sustitución, base completa y trazabilidad; coordinación 002. | T008..T012, T016, T017, T018. |
| Borrador 001 T003; originalmente consulta de 008 | Detalle/estado de fuentes/CAT-01, cero/ausencia/sin medidor/incompleto, base/intervalo/revisión y puertos sin notificaciones. | T017, T019, T026, T045, T048..T053. |

El alcance trasladado queda trazado en esta tabla. Sus reglas puras y configuración de 001
ya están implementadas donde las tareas llevan [X]; recepción, consulta e integración
siguen pendientes en las tareas sin marcar. No se declara el traslado completo.

## Cobertura de requisitos y contratos

| Alcance | Tareas de spec-001 |
| --- | --- |
| FR-001, catálogo/presencia/configuración | T005..T012, T021, T025..T028, T032..T036. |
| FR-002..005, mediciones confiables | T007, T009, T013, T015, T016, T018..T020. |
| FR-006, CAT-01 | T008, T011, T014, T017..T020, T022, T026, T031, T045, T048, T050, T052. |
| FR-007..010, gráfico/tabla/precisión/procedencia | T013, T016, T021..T036, T052. |
| FR-011..013, período/zona | T022, T026, T037..T044. |
| FR-014..016, estados/vacíos/respuestas obsoletas | T030, T034, T045..T053. |
| FR-017..019, entornos/acceso/pruebas locales | T001, T012, T021, T024, T027, T035, T054..T058, T060, T061. |
| SC-001/002 | T022..T024, T030..T036, T038, T043/T044. |
| SC-003/004 | T013..T020, T037..T044, T045..T053. |
| SC-005/006/007 | T059 / T056 / T060, consolidados en T061. |
| OpenAPI/HTTP, cuatro operaciones | T021, T025, T027, T028, T035; fechas/estados se completan en T040/T041/T048. |
| UI, consulta/configuración | T023/T024, T028..T035, T039/T042/T043, T046/T047/T049..T052. |
| Puertos 001/002 e integración real | T007/T009, T015..T020, T022/T026/T045; consumidores 004/005/008 se conectan en sus propias specs. |
| Aclaraciones I1/U1/A1 | T005..T018, T021/T025, T028/T029/T033, T038, T045..T053; revisiones por categoría, puerto de límites históricos y dominio numérico aprobado. |
| Auditoría/eventos propios e instrumentación | T006, T011, T054/T055; productores de recepción/incorporación siguen en 002. |
