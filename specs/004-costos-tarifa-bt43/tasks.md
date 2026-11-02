---
description: "Implementación del productor real BT4.3, boletas y comparación por historias"
---

# Tasks: Análisis de costos eléctricos con tarifa BT4.3

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/) y [quickstart.md](quickstart.md).
**Tests**: Necesarios por los casos independientes de la especificación y la exigencia constitucional de validar cálculos, conversiones y datos ausentes. Escribir las pruebas primero y constatar el fallo correspondiente antes del comportamiento nuevo.
**Organization**: US1 costo desglosado (P1), US2 contraste (P1), US3 vigencias (P2), US4 historial y limitaciones (P2).

## Format: `[ID] [P?] [Story] Description`

Las rutas son relativas a la raíz del repositorio. `[P]` permite tareas en archivos distintos de una misma tanda, una vez cumplidos sus prerrequisitos. Todos los cambios incluyen documentación de archivos y de elementos públicos/privados, pruebas y fórmulas. Los identificadores son propios de este archivo; no se confunden con T del archivo 008.

## Phase 1: Setup

**Purpose**: Incorporar costos al entregable compartido sin crear otra aplicación.

**Continuación (2026-11-02)**: proveedores físicos de001/002 verificados con PostgreSQL
real; T001–T063/T065–T067 completas (66/67). El bloqueo previo quedó resuelto tras
implementar002 sus proveedores. [Validación local](validation/acceptance.md). T064/SC-006
sigue pendiente por falta de participantes; los precios/condiciones reales deben configurarse.
No se modificaron checklists de revisión ni se acredita aceptación humana/VPS.

- [X] T001 Verificar las capacidades base reales en `backend/src/ecs_ec/core/database.py`, `backend/src/ecs_ec/identity/services.py`, `backend/src/ecs_ec/consumption/queries.py` y `backend/src/ecs_ec/audit/events.py` contra `contracts/integrations.md`; reutilizar plataforma009 y las capacidades de 001/002/006; si faltan, resolverlas en sus specs antes de continuar, sin construirlas dentro de costos ni depender del scheduler/SMTP o de completar 008, y registrar responsables/evidencia de cualquier prerequisito pendiente en `specs/004-costos-tarifa-bt43/validation/prerequisites.md`.
- [X] T002 Crear paquete documentado `backend/src/ecs_ec/costs/__init__.py` y rutas estáticas iniciales en `frontend/src/app/costos/page.tsx` y `frontend/src/app/administracion/costos/page.tsx`; incorporar dependencias de pruebas a `pyproject.toml` y `frontend/package.json` solo si faltan, conservando lockfiles compartidos. Prerrequisito: T001.
- [X] T003 Configurar fixtures sintéticos documentados en `backend/tests/costs_fixtures.py` y contexto de prueba en `backend/tests/conftest.py`, con PostgreSQL 18 real desechable, identidad vigente, reloj controlable, perfiles sin precios reales y barrera contra base de producción. Prerrequisito: T002.

**Checkpoint**: Paquete y datos de referencia reproducibles, sin reclamar funcionalidad implementada.

## Phase 2: Foundational

**Purpose**: Núcleo de perfil y evidencia necesario para calcular antes de entregar su editor completo en US3.

- [X] T004 [P] Escribir pruebas de puertos, permisos y restricciones comunes en `backend/tests/integration/costs/test_foundations.py`, usando identidad/consumo/auditoría reales de T001, y rechazando sustitución de medidor físico por CAT-01 calculada. Prerrequisitos: T001–T003.
- [X] T005 Implementar tipos comunes y aritmética en `backend/src/ecs_ec/costs/schemas.py` y `backend/src/ecs_ec/costs/money.py`: «UUID para identidades; revisión entera >=1», «Instantes UTC y zona IANA; ventanas [inicio,fin), inicio < fin», «Decimal finito en cadenas y NUMERIC; sin float, NaN o infinito» y «created_at, actor_id o process_ref y retain_until en toda revisión histórica»; documentar redondeo capturado y causas funcionales.
- [X] T006 Definir suministro y perfil/calendario/segmentos/cargos en `backend/src/ecs_ec/costs/models.py` conforme a `specs/004-costos-tarifa-bt43/data-model.md`: «UNIQUE building_id», suministro con revisión positiva para ETag, CAT-01 física y captura de sus datos/revisión; «UNIQUE (supply_id,revision); versiones inmutables», anterior nullable solo en primera revisión, estado draft/published fijado al crear; cada revisión contiene el calendario completo con segmentos [inicio,fin) sin solapamientos internos, fin nullable, zona IANA y «UNIQUE (segment_id,code)». Incluir BT4.3/CLP, cargos tipados, políticas mensuales/fuentes por segmento, Decimal >=0 y precisión/quantum/modo/etapa explícitos; revisiones históricas pueden cubrir las mismas vigencias.
- [X] T007 Implementar repositorio, selección de la última revisión publicada visible al corte y catálogo cerrado inicial en `backend/src/ecs_ec/costs/repository.py` y `backend/src/ecs_ec/costs/profiles.py`, más idempotencia en `backend/src/ecs_ec/costs/models.py`: «UNIQUE (actor_id,operation,key); misma clave/cuerpo reutiliza resultado, cuerpo distinto conflicto». Resolver segmentos de una sola revisión completa, limitar huecos/estrategias sin fuente y mantener borradores fuera de la selección publicada; autorizar antes del replay y no ejecutar expresiones libres.
- [X] T008 Incorporar proveedor común de eventos y unidad de trabajo en `backend/src/ecs_ec/costs/ports.py` y `backend/src/ecs_ec/costs/adapters.py`, apuntando a `backend/src/ecs_ec/audit/models.py` y `backend/src/ecs_ec/audit/events.py`; aplicar «UNIQUE (source_module,source_entity_id,source_revision,type)», sin importar notifications ni requerir un consumidor en ejecución.
- [X] T009 Crear migración `backend/migrations/versions/costs_004_initial.py` para suministro/perfil/segmentos/cargos/idempotencia y conectar esquema al head real; ejecutar T004 sobre PostgreSQL e identificar la migración común de auditoría sin duplicar su tabla. Los modelos de cada historia amplían la migración con revisiones semánticas adicionales y no reutilizan identificadores globales ya ocupados.

**Checkpoint**: Contratos base reales, motor monetario y perfil tipado disponibles; cualquier capacidad común ausente de T001 sigue siendo un bloqueo explícito, no una integración acreditada por dobles.

## Phase 3: User Story 1 — costo desglosado del suministro (P1) — MVP

**Goal**: Cálculo real, persistido y reproducible del costo por ciclo, con desglose visible y eventos durables de fallo.
**Independent Test**: Perfil sintético completo y CAT-01 física producen energía 100000 CLP, bloque 40 kW y bases 55/25 kW; datos horarios/incompletos o total calculado producen limitaciones sin costo completo inventado. Gráfico/tabla concuerdan; sin consumidor 008 el productor funciona.

### Pruebas de US1

- [X] T010 [P] [US1] Escribir `backend/tests/unit/costs/test_engine.py` con 1000×100=100000 CLP, cargos/impuestos sintéticos, cero válido y redondeos explícitos; rechazar no finitos, doble impuesto, consumo parcial agregado al total y precios faltantes. Verificar que mes de demanda no resuelto limita solo cargos dependientes. Prerrequisito: fase 2.
- [X] T011 [P] [US1] Escribir `backend/tests/unit/costs/test_demand.py` con 10 kWh/0,25 h=40 kW, máximos 60/50→55 y punta 30/20→25, empates de meses distintos, bloques incompletos y datos horarios insuficientes. Añadir ciclo entre meses con distinta condición de punta: política/fuente mensual explícita, ventana histórica y máximos esperados, sin inferir mes de emisión/inicio/fin; ausencia/contradicción conserva limitación. Prerrequisito: fase 2.
- [X] T012 [P] [US1] Escribir contrato de GET ciclos/detalle/suministro y POST cálculo en `backend/tests/contract/costs/test_calculations_api.py`, incluidos lectura administrativa de suministro/ETag o 404, sesión actual, mutación solo Administrador, CSRF/origen, decimales como texto, mes/evidencia validada, errores saneados, no-store e idempotencia. Prerrequisito: fase 2.
- [X] T013 [P] [US1] Escribir `backend/tests/integration/costs/test_calculation_events.py` para persistencia/reinicio, captura coherente, fallo del motor y atomicidad de resultado fallido + `cost.failed`, rollback de ambos e indisponibilidad del consumidor 008. Prerrequisito: fase 2.

### Implementación de US1

- [X] T014 [US1] Añadir ciclo a `backend/src/ecs_ec/costs/models.py` y migración `backend/migrations/versions/costs_004_calculations.py`, con «UNIQUE (supply_id,start_at,end_at); start_at < end_at», límites efectivos/declarados, zona, criterio temporal y limitación por fechas sin horas; no sustituir por mes de emisión ni guardar el mes de demanda como propiedad mutable del ciclo: pertenece a la captura de cada revisión.
- [X] T015 [US1] Añadir captura de reproducción en `backend/src/ecs_ec/costs/models.py` y `backend/src/ecs_ec/costs/snapshots.py`, usando REPEATABLE READ y corte único; aplicar «Solo CAT-01 de origen medido; nunca sustituir por total calculado». Conservar valores/unidades/bloques/máximos/cobertura, suministro y su revisión, revisión completa del perfil/segmentos, billing_month_ref/fuente/versión de política, hash canónico y versión del motor aunque las fuentes caduquen; mes no resuelto nullable con razón.
- [X] T016 [US1] Añadir cálculo/componentes en `backend/src/ecs_ec/costs/models.py` y migración de T014: «UNIQUE (cycle_id,revision); previous_id nullable solo en primera revisión», ejecución «completado o fallido», temporalidad «en_curso o cerrado», suficiencia «completo, parcial o no_calculable», «complete_total nullable; solo presente si sufficiency=completo y execution_state=completado» y «UNIQUE (calculation_id,code); importes/base nullable si no calculables»; preservar razones/versiones y subtotal disponible separado.
- [X] T017 [US1] Implementar bloques/máximos en `backend/src/ecs_ec/costs/demand.py` y punta/ventanas en `backend/src/ecs_ec/costs/calendar.py`: resolución exacta de 15 minutos, cobertura real, meses distintos aun con igual máximo e historia de 12 meses. Resolver billing_month_ref mediante política documentada del perfil o evidencia explícita validada, capturar fuente/versión y limitar cargos dependientes con billing_month_unresolved si falta o contradice; no inferir desde emisión/inicio/fin sin regla ni rellenar históricos con ceros.
- [X] T018 [US1] Implementar motor puro en `backend/src/ecs_ec/costs/engine.py` con componentes de energía, transmisión/servicio público, fijo, potencia suministrada, punta, impuestos y otros documentados; aplicar estrategias capturadas por vigencia, base y redondeo, rechazando prorrateo arbitrario y campos faltantes como cero.
- [X] T019 [US1] Implementar servicio de cálculo en `backend/src/ecs_ec/costs/services.py`: capturar entradas, evaluar, persistir revisión/componentes/evidencia/auditoría atómicamente y permitir reproducción por versión; consultas leen resultados sin crear revisiones, recálculo nuevo exige Administrador y razón/identidad de operación.
- [X] T020 [US1] Implementar resultado fallido y publicación `cost.failed` en `backend/src/ecs_ec/costs/services.py` mediante el writer común; si el cálculo abortó, iniciar nueva UoW válida para guardar ambos juntos, sanear causa y respetar deduplicación; base indisponible no afirma persistencia y datos insuficientes esperados no son fallo técnico.
- [X] T021 [US1] Implementar rutas de ciclos/cálculos y lectura administrativa GET /costs/supply en `backend/src/ecs_ec/costs/api.py`, con DTOs de `backend/src/ecs_ec/costs/schemas.py`, permisos actuales, CSRF, idempotencia, límites/cursor, errores y headers de `specs/004-costos-tarifa-bt43/contracts/http.md`. GET suministro lee configuración/id/revisión/ETag de los datos preparados para US1 o devuelve 404, sin crearlos; US3 completa su alta/edición. Registrar rutas bajo /api/v1 en la aplicación común.
- [X] T022 [US1] Crear cliente tipado en `frontend/src/lib/api/costs.ts`, conservando decimales como cadenas y distinguiendo datos disponibles, ausencia y fallo; gestionar sesión/CSRF e idempotencia sin realizar aritmética autoritativa en navegador.
- [X] T023 [US1] Crear consulta en `frontend/src/app/costos/page.tsx` y `frontend/src/components/costs/CostBreakdown.tsx`, con ciclo/zona/corte, conceptos/unidades/bases, temporalidad/suficiencia y total completo nullable; CAT-01 calculada indica falta de medición física. Crear `frontend/src/components/costs/CalculationForm.tsx` y conectarlo a `frontend/src/app/administracion/costos/page.tsx`: Administrador selecciona ciclo, revisa límites, aporta mes/fuente requeridos y confirma cálculo o recálculo con motivo/revisión anterior; invocar POST /costs/calculations y abrir revisión persistida. Conservar entradas ante error, bloquear doble envío y reutilizar clave solo al reintentar mismo cuerpo/operación; Operador solo consulta.
- [X] T024 [US1] Crear evolución y tabla sobre la misma respuesta en `frontend/src/components/costs/CostChart.tsx` y `frontend/src/components/costs/CostTable.tsx`, incluyendo energía cero con cargos independientes, accesibilidad por teclado y estados de espera/vacío/error sin filas inventadas.
- [X] T025 [US1] Añadir y ejecutar `frontend/tests/unit/cost-breakdown.test.tsx` y `frontend/tests/e2e/costs.spec.ts` para igualdad tabla/gráfico, datos incompletos y persistencia visible tras recarga. Recorrer desde la web cálculo y recálculo con motivo, selección mensual documentada y resultado persistido; reintento no duplica revisión, validación conserva entradas y Operador carece de controles y permiso de mutación. Corregir fallos con resultados numéricos de referencia.
- [X] T026 [US1] Ejecutar T010–T013/T025 con módulos reales, reinicio de proceso y consumidor 008 ausente; registrar hashes/cortes/perfiles y resultados saneados en `specs/004-costos-tarifa-bt43/validation/us1.md`, sin afirmar entrega de correo.
- [X] T027 [US1] Documentar entregable del productor real, fallo atómico y preparación sintética para US1 en `specs/004-costos-tarifa-bt43/quickstart.md`, manteniendo pendientes los precios/configuración reales del suministro cuando no estén disponibles.

**Checkpoint**: MVP de cálculo real disponible sin editor avanzado, boleta o consumidor de notificaciones; U1 ya posee motor, persistencia y productor funcional verificables.

## Phase 4: User Story 2 — contraste con boleta mensual (P1)

**Goal**: Registrar boletas manuales versionadas y comparar sobre bases equivalentes sin alterar el cálculo.
**Independent Test**: Ciclo cruza meses; 105 contra 100→+5 CLP/5 %, facturado cero→porcentaje no aplicable; créditos/exclusiones/impuestos y correcciones mantienen signo, bases y revisión anterior.

### Pruebas de US2

- [X] T028 [P] [US2] Escribir `backend/tests/unit/costs/test_comparison.py` para alineación de suministro/ciclo/moneda/concepto/base tributaria, porcentaje con denominador absoluto, facturado cero, créditos y conceptos no comparables. Prerrequisito: US1.
- [X] T029 [P] [US2] Escribir `backend/tests/contract/costs/test_bills_comparisons_api.py` para las seis operaciones de boletas y comparaciones, incluyendo duplicado, revisión 412/428, permisos, CSRF, ComparisonRequest con calculation_id/bill_revision_id explícitos y ausencia de cambios a mediciones/tarifas; las consultas exponen referencias estables sin crear comparaciones. Prerrequisito: US1.

### Implementación de US2

- [X] T030 [US2] Añadir boleta/revisión/líneas en `backend/src/ecs_ec/costs/models.py` y migración `backend/migrations/versions/costs_004_bills.py`, con «UNIQUE (supply_id,external_identifier_normalized)», «UNIQUE (bill_id,revision)» y «amount firmado; quantity/tax_amount nullable si no constan»; conservar magnitudes leídas separadas de bases facturadas, referencia documental y límites de ciclo.
- [X] T031 [US2] Añadir comparación/líneas en `backend/src/ecs_ec/costs/models.py` y migración de T030, con «UNIQUE (calculation_id,bill_revision_id,revision)» y «delta=calculado-facturado; delta_percent=100*delta/abs(facturado) si facturado!=0; NULL si facturado=0»; retener ambos lados/versiones y exclusiones.
- [X] T032 [US2] Implementar registro/corrección manual en `backend/src/ecs_ec/costs/bills.py` y `backend/src/ecs_ec/costs/repository.py`, con identificador repetido reconocido, revisión explícita y procedencia inmutable; no carga/OCR ni actualización de fuente para igualar importes.
- [X] T033 [US2] Implementar comparación en `backend/src/ecs_ec/costs/comparison.py`, con pares alineados, subtotal comparable distinto del total a pagar y causas de exclusión; conservar signo y evitar doble impuesto o contraste ficticio sin boleta. Añadir en `backend/src/ecs_ec/costs/repository.py` resolución compartida de último cálculo/boleta al corte y comparación exacta: missing_for_selected_revisions sin diferencias si falta, sin retroceder a versiones anteriores ni crear comparaciones al leer; historia/snapshot de US4 reutilizan este resolver.
- [X] T034 [US2] Implementar operaciones de boletas/comparaciones y ampliar GET ciclos con selección de revisiones/IDs/comparison_status en `backend/src/ecs_ec/costs/api.py` y sus uniones tipadas en `backend/src/ecs_ec/costs/schemas.py`, según contrato, con auditoría/If-Match/idempotencia y lectura permitida a ambos perfiles funcionales. Exponer referencias para elegir par actual o histórico sin generar comparación automáticamente.
- [X] T035 [US2] Crear entrada/corrección de boleta en `frontend/src/components/costs/BillEditor.tsx` y conectarla con `frontend/src/app/administracion/costos/page.tsx`, conservando valores introducidos y ofreciendo nuevas revisiones solo a Administrador.
- [X] T036 [US2] Crear `frontend/src/components/costs/ComparisonTable.tsx` y `frontend/src/components/costs/ComparisonActions.tsx`, ampliar `frontend/src/lib/api/costs.ts`, conectar tabla de consulta a `frontend/src/app/costos/page.tsx` y acciones a `frontend/src/app/administracion/costos/page.tsx`. Administrador selecciona revisiones compatibles y confirma POST /costs/comparisons; mostrar recurso persistido, referencias históricas, importe comparable/total a pagar, exclusiones/signos y porcentaje no aplicable. Corregir boleta ofrece actualizar contraste explícitamente; mostrar pendiente si falta comparación del par actual. Conservar entradas/idempotencia de reintento y no duplicar envíos ni crear comparaciones al consultar; Operador solo lee.
- [X] T037 [US2] Añadir y ejecutar `backend/tests/integration/costs/test_bill_revisions.py` con identificadores simultáneos/correcciones y captura anterior conservada sobre PostgreSQL real; el registro de boleta no altera mediciones ni perfil.
- [X] T038 [US2] Añadir y ejecutar `frontend/tests/e2e/cost-comparisons.spec.ts` con todos los escenarios de US2 y datos sintéticos. Crear contraste desde la web eligiendo revisiones, recuperar tras recarga, corregir boleta y confirmar otra comparación; preservar comparación histórica, gestionar validación/reintentos sin duplicación y denegar mutación al Operador. Corregir errores de alineación y permisos.
- [X] T039 [US2] Ejecutar T028–T029/T037–T038 y registrar ciclos, pares/revisiones y resultados conocidos en `specs/004-costos-tarifa-bt43/validation/us2.md`.

**Checkpoint**: Contraste interpretable y reproducible; una boleta incompleta o ausente no elimina el costo disponible.

## Phase 5: User Story 3 — condiciones y vigencias BT4.3 (P2)

**Goal**: Administración completa del perfil, fuentes y vigencias, ampliando el núcleo ya usado por US1.
**Independent Test**: Revisiones con calendarios completos sustituyen vigencias abiertas o corrigen segmentos sin alterar cálculos previos; solapamientos internos, huecos o reglas ausentes limitan resultado. Alta/edición del suministro y publicaciones concurrentes respetan sus precondiciones.

### Pruebas de US3

- [X] T040 [P] [US3] Escribir `backend/tests/unit/costs/test_profile_vigencies.py` para calendarios completos por revisión, segmentos superpuestos dentro de una revisión rechazados y vigencias coincidentes entre revisiones históricas válidas. Probar cambio por cargo, punta/DST, política mensual de ciclo entre meses, fuentes ausentes y estrategias no soportadas, sin prorratear fijo/demanda. Prerrequisito: US1.
- [X] T041 [P] [US3] Escribir `backend/tests/contract/costs/test_profiles_api.py` para GET/POST perfiles y GET/PUT suministro: administración exclusiva, lectura de configuración/id/revisión/ETag, alta If-None-Match: * (201/412), edición If-Match (200/412), ausencia 428 y cabeceras incompatibles 422. Probar expected_previous_version_id obligatorio/null inicial/conflicto 409, borradores y errores que preservan último estado válido; replay autorizado precede precondiciones nuevas. Prerrequisito: US1.

### Implementación de US3

- [X] T042 [US3] Completar validación/publicación y resolución de calendarios en `backend/src/ecs_ec/costs/profiles.py`: nueva revisión contiene todos los segmentos, resuelve vigencia abierta o corrección retroactiva sin modificar original y captura fuente/estrategia/calendario/política mensual/históricos/redondeo. Rechazar solapamientos internos; aceptar coincidencias entre revisiones históricas y limitar huecos/estrategias sin soporte. Los cálculos seleccionan una sola revisión publicada al corte; borradores no cambian selección.
- [X] T043 [US3] Implementar alta/lectura/modificación del suministro y creación/publicación de revisiones de perfil en `backend/src/ecs_ec/costs/services.py`, con auditoría y autorización vigentes e idempotencia. Alta única por edificio con revisión 1; edición incrementa revisión bajo precondición. Bajo bloqueo del suministro comparar expected_previous_version_id con última revisión guardada (incluidos borradores), devolver 409 si cambió y asignar secuencia/anterior atómicos; cambios no recalculan automáticamente el pasado.
- [X] T044 [US3] Implementar las cuatro operaciones GET/POST perfiles y GET/PUT suministro en `backend/src/ecs_ec/costs/api.py`; DTOs tipados en `backend/src/ecs_ec/costs/schemas.py`. GET suministro devuelve 404 si falta y configuración/id/revisión/ETag si existe; PUT alta If-None-Match: * o edición If-Match responde según contrato. GET perfiles expone latest_version_id y selected_published_version_id; POST recibe calendario completo/publication_state/expected_previous_version_id y responde 409 ante base desactualizada.
- [X] T045 [US3] Crear `frontend/src/components/costs/ProfileEditor.tsx` y `frontend/src/components/costs/SupplyEditor.tsx`, conectar con página administrativa. Leer suministro/ETag por GET; 404 permite alta con If-None-Match: *, edición con If-Match, 412 conserva entradas y exige revisar estado actual; recuperar tras recarga. Perfil muestra solo BT4.3, calendario completo/segmentos, fuentes, tributación, política mensual y redondeo; copiar calendario para nueva revisión, distinguir borrador/publicado y enviar expected_previous_version_id leído, resolviendo 409 mediante revisión explícita del último estado.
- [X] T046 [US3] Añadir y ejecutar `backend/tests/integration/costs/test_profile_concurrency.py` sobre PostgreSQL real: alta simultánea del suministro permite una creación, edición con ETag antiguo no sobrescribe y dos publicaciones con igual expected_previous_version_id permiten una sola. Probar V1 abierta, V2 con segmentos antes/después del cambio y V3 con corrección retroactiva: versiones/capturas previas reproducibles; borrador no cambia perfil seleccionado y fallo de publicación no guarda calendario parcial.
- [X] T047 [US3] Añadir y ejecutar `frontend/tests/e2e/cost-profiles.spec.ts` para todos los escenarios de US3: alta/lectura/edición del suministro tras recarga y conflicto conservando entradas; edición del calendario completo, vigencia abierta/corrección retroactiva y borrador/publicación concurrente. Incluir consulta histórica y recálculo administrativo autorizado mediante el formulario de US1, con revisión distinta y evidencia anterior intacta.
- [X] T048 [US3] Ejecutar T040–T041/T046–T047 y registrar políticas/sources sintéticas/versiones y resultados en `specs/004-costos-tarifa-bt43/validation/us3.md`, conservando pendientes los datos reales no suministrados.
- [X] T049 [US3] Documentar procedimiento de registrar pliego real, publicación del calendario completo y sustitución de vigencias abiertas/correcciones en `specs/004-costos-tarifa-bt43/quickstart.md`, incluyendo política mensual documentada, fuentes, límites de vigencia/redondeo y lectura/alta/edición concurrente de suministro; sin asignar distribuidora ni tasa tributaria universal.

**Checkpoint**: Administración completa del perfil reproducible; configurar una referencia no altera el pasado ni concede permisos nuevos.

## Phase 6: User Story 4 — historial y cálculos incompletos (P2)

**Goal**: Explorar historia, reproducir resultados protegidos y proporcionar capturas coherentes a PDF005.
**Independent Test**: Doce meses sintéticos, estados temporales/parciales y revisión histórica; detalle original vencido no impide reproducción. Puerto 005 selecciona últimas revisiones a corte por ciclo cerrado con fin efectivo en ventana y solo comparación del par exacto; una corrección sin nuevo contraste queda pendiente.

### Pruebas de US4

- [X] T050 [P] [US4] Escribir `backend/tests/integration/costs/test_reproduction_retention.py` para reproducción tras retirar detalle vencido, máximos/perfil preservados, 12 meses calendario y aniversarios especiales, sin prolongar por consultas o duplicados. Prerrequisitos: US1–US3.
- [X] T051 [P] [US4] Escribir `backend/tests/contract/costs/test_history_snapshots.py` para GET historial y Costs.read_snapshot: ciclos cerrados por fin efectivo; último cálculo y boleta visibles al corte y última comparación del par exacto. Probar corrección de boleta o recálculo sin nueva comparación: missing_for_selected_revisions, diferencias null y exclusión del agregado; no retroceder a versiones previas. Corte anterior conserva comparación original y consulta no crea otra; distinguir recursos ausentes y facturado cero con comparación available. Prerrequisitos: US1–US3.

### Implementación de US4

- [X] T052 [US4] Implementar consulta histórica en `backend/src/ecs_ec/costs/history.py` y `backend/src/ecs_ec/costs/repository.py`, con cursor estable, rango/corte, al menos 12 meses cuando existan y distinción de ejecución/temporalidad/suficiencia. Resolver últimas revisiones y comparación del par exacto; exponer referencias estables/comparison_status/diferencias null si pendiente y mantener comparaciones anteriores como históricas sin inventar historia ni mutar al consultar.
- [X] T053 [US4] Implementar reproducción pura desde captura en `backend/src/ecs_ec/costs/reproduction.py`, verificando hash y versión del motor, criterios de redondeo y cantidades originales; no depender de precios/perfil actuales ni del detalle ya retirado.
- [X] T054 [US4] Implementar protección de conservación en `backend/src/ecs_ec/costs/retention.py` con helper temporal común, aniversario calendario en zona del edificio y extensión de padres/evidencia hasta el máximo de dependientes; no cascadas destructivas ni borrado automático obligatorio.
- [X] T055 [US4] Implementar Costs.read_snapshot en `backend/src/ecs_ec/costs/snapshots.py` conforme al contrato compartido con 005, admitiendo su UoW REPEATABLE READ: ciclos cerrados por fin efectivo, último cálculo y boleta al corte y comparación solo de ese par exacto. missing_for_selected_revisions conserva referencias/valores y diferencias null, excluye ciclo del contraste agregado y no retrocede revisiones ni genera comparaciones; subtotales disponibles separados y evidencia inmutable.
- [X] T056 [US4] Implementar GET historial y completar GET ciclos en `backend/src/ecs_ec/costs/api.py`, más DTOs de captura/historia en `backend/src/ecs_ec/costs/schemas.py`: IDs/revisiones seleccionados, comparison_status y referencias históricas según contrato; preservar permisos actuales, moneda/base, diferencias nulas por contraste pendiente y motivos sin ciclos/boletas/pares.
- [X] T057 [US4] Crear filtros y evidencia histórica en `frontend/src/components/costs/CostHistory.tsx` y `frontend/src/components/costs/ReproductionDetail.tsx`, mostrando corte/versiones/calidad/punto de medición, suministro/perfil/segmentos y mes/fuente/política capturados. Mostrar contraste pendiente para las revisiones seleccionadas sin diferencias inventadas; conservar acceso histórico a comparación anterior y coherencia gráfico/tabla.
- [X] T058 [US4] Añadir y ejecutar `backend/tests/integration/costs/test_snapshot_consistency.py` con cambios concurrentes de cálculo/boleta y captura compartida con consumo. Corregir boleta/recalcular sin nueva comparación excluye el par pendiente del agregado; crear comparación exacta lo incorpora y repetir corte anterior conserva selección original. Exigir diferencias null donde faltan y ausencia de mutaciones, duplicación/prorrateo para PDF.
- [X] T059 [US4] Añadir y ejecutar `frontend/tests/e2e/cost-history.spec.ts` para todos los escenarios de US4, incluidos período en curso, resolución insuficiente, revisión, punto de medición distinto sin ajuste implícito y contraste pendiente tras corregir boleta/recalcular; comparación anterior solo histórica y diferencias ausentes hasta confirmar el nuevo par.
- [X] T060 [US4] Ejecutar T050–T051/T058–T059 y registrar evidencias de reproducción/conservación/captura en `specs/004-costos-tarifa-bt43/validation/us4.md`.
- [X] T061 [US4] Documentar contrato de lectura real para 005 y criterio de suficiencia/reproducción en `specs/004-costos-tarifa-bt43/contracts/integrations.md` y `specs/004-costos-tarifa-bt43/quickstart.md`, reflejando la implementación final y sus versiones.

**Checkpoint**: Productor y lectura financiera completos y trazables; PDF005 puede consumirlos sin recalcular costos y 008 integrar eventos reales.

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T062 Añadir y ejecutar `backend/tests/integration/costs/test_security_isolation.py` con sesión revocada, roles, secretos sintéticos y caída del consumidor008/correo/telemetría; costos y eventos comunes no dependen de ellos ni filtran datos sensibles.
- [X] T063 Ejecutar todas las suites y la guía reproducible con PostgreSQL real, exportación Next y módulos comunes reales; registrar comandos, lockfiles, conteos y duración/tamaño de casos en `specs/004-costos-tarifa-bt43/validation/acceptance.md` sin afirmar capacidad no medida.
- [ ] T064 Realizar diez tareas con personas representativas conforme a SC-006 y registrar resultados en `specs/004-costos-tarifa-bt43/validation/usability.md`; nueve sin ayuda en <=2 minutos. Sin participantes o resultados reales, dejar la tarea pendiente.
- [X] T065 Revisar documentación completa de archivos/elementos propios, fórmulas/conversiones y contratos en `backend/src/ecs_ec/costs/`, `frontend/src/components/costs/` y `specs/004-costos-tarifa-bt43/validation/acceptance.md`, resolviendo desviaciones constitucionales antes de aceptar.
- [X] T066 Entregar evidencia U1 de motor real, persistencia tras reinicio, fallo/evento atómicos y puerto snapshot real en `specs/004-costos-tarifa-bt43/validation/producer-handoff.md`, con referencias para integración posterior de 008 y PDF005; un test de stub no acredita estos entregables.
- [X] T067 Actualizar trazabilidad FR-001..FR-023 y SC-001..SC-006 en `specs/004-costos-tarifa-bt43/validation/coverage.md`, consignando resultados y cualquier configuración/criterio aún pendiente sin cambiar marcadores de checklists de revisión.

## Dependencies & Execution Order

```text
Núcleo compartido real → Setup → Fundaciones → US1 ─┬→ US2 ─┐
                                                  └→ US3 ─┴→ US4 → Transversal
US1 productor cost.failed → integración posterior 008
US4 Costs.read_snapshot → PDF005
```

GET suministro y formulario de cálculo pertenecen a US1; US3 completa su alta/edición y administración. US2 añade el resolver de comparación exacta y referencias de GET ciclos antes del formulario de contraste; US4 los reutiliza para historia/snapshot. US2 y US3 requieren US1; pueden prepararse pruebas independientes después de ese checkpoint, pero cambios en `models.py`, `services.py`, `api.py`, `repository.py` o cliente compartido se realizan secuencialmente. US4 requiere ambas revisiones/boletas y perfiles completos. El núcleo compartido no depende de aceptar 008 ni de su consumidor, evitando el ciclo 004→008→004.

Las migraciones semánticas de una misma aplicación forman una cadena según el head real; no se ejecutan ramas de esquema inconexas ni se altera una migración aplicada. En un proyecto nuevo se construyen los modelos/migraciones iniciales; si ya existe esquema, añadir migración posterior.

| Fase/historia | Tareas | Cantidad |
| --- | --- | ---: |
| Setup | T001–T003 | 3 |
| Fundaciones | T004–T009 | 6 |
| US1 P1 | T010–T027 | 18 |
| US2 P1 | T028–T039 | 12 |
| US3 P2 | T040–T049 | 10 |
| US4 P2 | T050–T061 | 12 |
| Transversal | T062–T067 | 6 |
| Total | T001–T067 | 67 |

## Parallel Examples

| Historia | Tanda independiente con prerrequisitos cumplidos |
| --- | --- |
| US1 | T010 `test_engine.py`, T011 `test_demand.py`, T012 `test_calculations_api.py`, T013 `test_calculation_events.py` |
| US2 | T028 `test_comparison.py` y T029 `test_bills_comparisons_api.py` |
| US3 | T040 `test_profile_vigencies.py` y T041 `test_profiles_api.py` |
| US4 | T050 `test_reproduction_retention.py` y T051 `test_history_snapshots.py` |

Los nombres abreviados se refieren a las rutas completas de las tareas. T004 puede prepararse como prueba antes de implementar fundaciones. Las tandas `[P]` no permiten omitir los checkpoints de dependencia.

## Cobertura

| Requisitos | Tareas |
| --- | --- |
| FR-001, FR-005, FR-013 | T018–T026, T036, T052, T057 |
| FR-002, FR-006, FR-007, FR-008, FR-009, FR-010 | T010–T011, T015, T017–T020 |
| FR-003, FR-004, FR-012 | T006–T007, T040–T049 |
| FR-008, FR-011: mes de referencia documentado | T010–T011, T014–T017, T023, T040 |
| FR-019: flujos web y suministro/publicación concurrentes | T023, T025, T036, T038, T041–T047 |
| FR-016: contraste del par exacto al corte | T036, T051–T059 |
| FR-011, FR-015, FR-016, FR-017, FR-018, FR-019 | T014, T028–T039, T043, T046 |
| FR-014, FR-020, FR-021, FR-022, FR-023 | T015–T016, T050–T061 |
| SC-001 | T010–T013, T026 |
| SC-002 | T028–T029, T037–T039 |
| SC-003 | T010–T011, T040, T059 |
| SC-004 | T046, T050, T053–T054, T060 |
| SC-005 | T024–T025, T036, T057–T059 |
| SC-006 | T064 |
| U1 productor real e integración sin ciclos | T008, T013, T020, T055, T062, T066 |

## Implementation Strategy

Primero completar núcleo común y US1 con un perfil sintético válido: motor/persistencia/eventos funcionan sin boletas, editor completo o consumidor 008. Añadir contraste US2 y administración US3, después historia/reproducción/snapshot US4. Cerrar con seguridad, evidencias y prueba humana. Los datos reales del suministro se configuran con sus fuentes antes de afirmar un cálculo real aplicable; no se sustituyen por fixtures.

Los checklists de calidad permanecen a cargo de quien revisa. Una tarea marcada completa durante implementación significa trabajo/evidencia realizado; no evalúa automáticamente la calidad de requisitos ni afirma aceptación de los criterios humanos pendientes.
