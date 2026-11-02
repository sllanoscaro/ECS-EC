---
description: "Tareas por historia para el productor real de reportes PDF de una página"
---

# Tasks: Reportes PDF de una página por período

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md) y [constitución](../../.specify/memory/constitution.md).
**Tests**: La spec solicita pruebas independientes y resultados de referencia; la constitución exige verificación automatizada de validaciones/cálculos y contraste de visualización contra fuentes. Escribir primero las pruebas del comportamiento nuevo y constatar su fallo esperado; no exigir fallos artificiales en capacidades ya implementadas.
**Organization**: Cuatro historias de spec-005, precedidas por setup/fundaciones y seguidas de validación transversal. Todos los marcadores quedan pendientes.

## Format: `[ID] [P?] [Story] Description`

- `[P]` permite trabajo en archivos distintos dentro de la tanda y después de sus prerrequisitos; no autoriza omitir dependencias.
- `[US1]` a `[US4]` corresponden a historias de esta spec, no a las de costos o notificaciones.
- Rutas relativas a la raíz del repositorio; no existen todavía los módulos propuestos.
- Todo cambio documenta archivo, funciones/métodos/clases/componentes, pruebas, errores y decisiones no evidentes junto al código.
- Las restricciones entre comillas en las tareas de persistencia proceden de `data-model.md`; aplicar también nulabilidad/relaciones y transiciones de ese modelo.

## Phase 1: Setup

**Purpose**: Preparar dependencias PDF y verificar capacidades compartidas reales sin introducir un ciclo con notificaciones.

- [ ] T001 Inventariar y satisfacer los puertos reales de identidad/consumo/auditoría y `Costs.read_snapshot` en `backend/src/ecs_ec/reports/ports.py` y `specs/005-generar-reportes-pdf/validation/dependencies.md`; reutilizar capacidades implementadas o registrar como bloqueante su ausencia en las specs propietarias 009/001/002/006/004. Inventariar además el emisor común de spec-007, según [su especificación](../007-observabilidad-externa/spec.md) e [investigación trasladada](../007-observabilidad-externa/research.md), previsto en `backend/src/ecs_ec/observability/logging.py` y `tracing.py`; su ausencia bloquea T062 y la aceptación US1. No implementar capacidades ajenas dentro de PDF ni depender de visores activos, consumidor008 o SMTP.
- [ ] T002 Añadir ReportLab 5.1.0 y pypdf 6.21.4 a `pyproject.toml` y `uv.lock`, comprobar instalación CPython 3.14 y registrar fuente TTF Unicode redistribuible/licencia/versionado en `backend/src/ecs_ec/reports/fonts/README.md`; conservar el stack compartido y no añadir un servicio de PDF independiente.
- [ ] T003 [P] Preparar exportación estática y herramientas de frontend para `/reportes/` en `frontend/src/app/reportes/page.tsx` y `frontend/tests/unit/reports.test.tsx`, reutilizando sesión y API del mismo origen sin datos privados en build. Prerrequisito: T001.
- [ ] T004 [P] Preparar fixtures de PostgreSQL aislado, entradas conocidas y lector PDF independiente en `backend/tests/conftest.py` y `backend/tests/support/pdf_assertions.py`, con protección contra base de producción. Prerrequisito: T001.
- [ ] T005 Documentar límites de la nueva capacidad, ejecución local y dependencia productora de spec-004 en `README.md` y `deploy/README.md`; incorporar paquetes/fuentes al `Dockerfile` existente sin exponer carpeta estática de binarios privados. Prerrequisitos: T002–T004.

**Checkpoint**: Herramientas instalables y dependencias verificadas por capacidad; ningún productor ausente se considera satisfecho por un doble.

## Phase 2: Foundational

**Purpose**: Persistencia de captura/resultado, lectura coherente, autorización y ejecución interna compartidas por todas las historias.

### Pruebas de fundaciones

- [ ] T006 [P] Escribir `backend/tests/integration/reports/test_snapshot_foundations.py` para una única captura/corte, versiones vigentes, restricciones de estado/binary/result y transacción compartida con consumo/costos; usar PostgreSQL real. Prerrequisito: fase 1.
- [ ] T007 [P] Escribir `backend/tests/contract/reports/test_reports_api.py` para las tres operaciones de `contracts/http.md`, sesión actual, origen/CSRF, no-store, idempotencia, errores por campo y descarga solo de bytes íntegros autorizados. Prerrequisito: fase 1.
- [ ] T061 Escribir `backend/tests/integration/reports/test_observability.py` para correlación desde solicitud hasta executor, etapas y resultados de éxito/rechazo/fallo, conteos sin inflación por replay/consulta/descarga y duración observada según `contracts/integrations.md`; verificar ausencia de secretos/valores funcionales/etiquetas únicas y continuidad funcional ante transporte caído o cola técnica saturada. Preparar después de T007; la ejecución positiva con emisor real se completa en T063, sin exigir visores activos.

### Implementación compartida

- [ ] T008 Crear solicitud e idempotencia en `backend/src/ecs_ec/reports/models.py`: «UUID generado por la aplicación», escala «`diario`, `mensual` o `anual`», selección «Exactamente los campos aplicables: fecha; año/mes; o año», ventana «`[inicio,fin)`, siempre inicio < fin», estado «`pendiente`, `generando`, `generado`, `fallido`», revisión «Entero positivo para transición exclusiva» y «UNIQUE `(requested_by, operation, idempotency_key)`»; conservar actor/edificio conocidos, corte fijo y aniversario mínimo.
- [ ] T009 Añadir captura a `backend/src/ecs_ec/reports/models.py`: «UUID; UNIQUE `request_id`», versión de esquema «Entero positivo», «Exactamente siete filas, CAT-01..CAT-07, sin categorías repetidas», «Decimal finito serializado como cadena; ausencia es NULL con motivo, nunca cero imputado», «estructura tipada y versionada, sin secretos ni detalles técnicos de excepción» e «inmutable después de confirmarse»; incluir todos los campos, referencias y restricciones de `report_snapshot`, sin sumar monedas o bases incompatibles. Filas y bloques conservan `source_mode: measured|calculated|mixed|unavailable` y `provenance_segments` con límites, modo, fuente, revisiones y `basis_sources`; sin medidor es un estado separado del modo de origen.
- [ ] T010 Añadir resultado/binario a `backend/src/ecs_ec/reports/models.py`: «UUID; UNIQUE `request_id`; snapshot opcional solo si falló su captura», estado «`generado` o `fallido`», página «Exactamente 1 para resultado generado», dimensiones «210 y 297 para resultado generado», fuente «>=10 para todo el texto del resultado generado», hash/longitud/binario «Presentes solo para generado; hash/longitud corresponden a bytes íntegros» y «Acceso solo mediante descarga autenticada y autorización vigente»; resultado inmutable, BYTEA con longitud positiva y sin binario descargable para fallido.
- [ ] T011 Crear `backend/migrations/versions/reports_initial.py` sobre las capacidades compartidas existentes, con FKs, unicidad/CAS y restricciones de T008–T010; aplicar «al menos 12 meses calendario desde registro o revisión sustantiva; no borrar evidencia referenciada todavía protegida» mediante la función común de aniversario, sin recrear tablas de identidad/audit ni destruir fuentes.
- [ ] T012 Implementar validación calendario en `backend/src/ecs_ec/reports/calendar.py` y `backend/src/ecs_ec/reports/schemas.py`: fecha real, mes 1..12, solo campos aplicables, zona del edificio, límites diarios/mensuales/anuales reales y rechazo de futuro total; conservar período actual provisional y pasado sin datos.
- [ ] T013 Implementar repositorio e idempotencia en `backend/src/ecs_ec/reports/repository.py`, autenticando antes del replay, misma clave/cuerpo devuelve original y cuerpo distinto 409; publicar bytes/resultado atómicos y guardar fallido + evento con «UNIQUE `(source_module, source_entity_id, source_revision, type)`», usando `audit/events.py` en la misma unidad de trabajo, sin importar `notifications`.
- [ ] T014 Implementar adaptadores de captura en `backend/src/ecs_ec/reports/snapshots.py` con una sesión REPEATABLE READ y corte inicial compartidos por `Consumption.read_report_snapshot` y `Costs.read_snapshot`; copiar siete filas, bloques, procedencia y conjuntos financieros reales inmutables, con revisiones registradas al corte y sin mantener transacción durante render. Conservar modo y segmentos completos del productor, incluidos cambios de fuente/base, sin reconstruirlos ni recalcular energía o convertir diagnósticos no numéricos en cero.
- [ ] T015 Implementar claim y supervisor interno ampliable en `backend/src/ecs_ec/reports/worker.py`, con dos plazas iniciales, ejecución fuera del event loop, estado durable y reconciliación de `generando` interrumpidos a fallo único mediante audit; registrar el supervisor en `backend/src/ecs_ec/core/lifecycle.py` sin depender de trabajos de correo.

**Checkpoint**: Pruebas T006–T007/T061 preparadas y fundaciones integradas. Las verificaciones positivas de generación real e instrumentación con el emisor común se completan con US1; no se afirma un binario válido todavía.

## Phase 3: User Story 1 — elegir período y descargar (P1)

**Goal**: Solicitud validada, captura real, generación íntegra y descarga protegida con selección conservada ante error.
**Independent Test**: Cubrir los seis escenarios US1 con datos reales de día/mes/año, período actual/pasado sin datos, selección inválida y fallo/reintento. Desde este incremento se incluyen todas las secciones obligatorias; no se admite un MVP con PDF ficticio o incompleto.

### Pruebas de US1

- [ ] T016 [P] [US1] Escribir `backend/tests/integration/reports/test_report_requests.py` para selección/provisionalidad, corte, pasado vacío, fechas inválidas/futuras, idempotencia y descarga autorizada repetible; asegurar que solicitar reportes no actualiza mediciones ni se limita a 15 minutos. Prerrequisito: fase 2.
- [ ] T017 [P] [US1] Escribir `frontend/tests/e2e/reports.spec.ts` para las tres escalas, progreso/fallo, conservación de campos, retorno seguro de sesión y descarga con nombre/identidad apropiados. Prerrequisito: fase 2.

### Implementación de US1

- [ ] T018 [US1] Implementar creación y captura de solicitud en `backend/src/ecs_ec/reports/services.py`, fijando opciones, ventana/corte y snapshot antes de responder; marcar fallo admitido de captura con resultado/evento durables cuando la base permite confirmarlos, sin afirmar persistencia ante 503.
- [ ] T019 [US1] Implementar `POST /api/v1/reports` y `GET /api/v1/reports/{report_id}` en `backend/src/ecs_ec/reports/api.py` según `contracts/http.md`: permisos actuales, CSRF/origen, clave 1..100, respuesta 202/estado y errores saneados, sin manifiesto técnico ni datos personales innecesarios.
- [ ] T020 [US1] Implementar ensamblado funcional completo en `backend/src/ecs_ec/reports/content.py`, consumiendo captura real para identificación, tabla, gráfico, costos, pares y calidad; mantener origen/base de CAT-01, estado sin cierres/sin boleta y todos los datos indispensables dentro del documento.
- [ ] T021 [US1] Implementar motor real ReportLab en `backend/src/ecs_ec/reports/renderer.py` con seis bandas A4 vertical y fuente TTF incrustada, salida en memoria y manifiesto de cajas/fuentes; no usar PDF de fixture como resultado ni depender de navegador/servicio remoto.
- [ ] T022 [US1] Implementar preflight básico obligatorio en `backend/src/ecs_ec/reports/preflight.py`: abrir bytes con pypdf, una página 210×297 mm con tolerancia <=0,1 mm, texto efectivo >=10 pt, secciones y cajas válidas; cualquier incumplimiento impide publicar éxito, sin reducir fuente u ocultar contenido.
- [ ] T023 [US1] Conectar render/preflight/publicación y manejo de fallo en `backend/src/ecs_ec/reports/services.py` y `backend/src/ecs_ec/reports/worker.py`; éxito confirma BYTEA/hash/longitud/estado juntos y fallo confirma resultado + `pdf.failed` juntos, descartando buffers parciales y preservando fuentes.
- [ ] T024 [US1] Implementar `GET /api/v1/reports/{report_id}/download` en `backend/src/ecs_ec/reports/api.py`, con permiso actual, no-store, Content-Disposition seguro y binario generado íntegro; descarga repetida no regenera ni crea evento de fallo del productor.
- [ ] T025 [US1] Implementar cliente, selección y estados en `frontend/src/lib/api/reports.ts`, `frontend/src/components/reports/ReportForm.tsx` y `frontend/src/components/reports/ReportStatus.tsx`, integrados en `frontend/src/app/reportes/page.tsx`; etiquetas/teclado, campos aplicables, progreso, selección conservada y enlace privado solo al generar.
- [ ] T062 [US1] Instrumentar `backend/src/ecs_ec/reports/services.py`, `backend/src/ecs_ec/reports/worker.py` y `backend/src/ecs_ec/reports/api.py` mediante el emisor común real de spec-007: correlación de solicitud a executor y etapas de captura/espera/render/preflight/publicación/descarga; logs saneados, trazas y eventos `report.admitted`/`report.completed` con conteos, duración y dimensiones acotadas según `contracts/integrations.md`. Mantener contexto técnico fuera del contenido/hash funcional y emisión desacoplada de red/commits; no implementar infraestructura de observabilidad dentro de PDF. Prerrequisitos: T025, T061 y emisor real en `backend/src/ecs_ec/observability/logging.py` y `tracing.py`, con propiedad en [spec-007](../007-observabilidad-externa/spec.md).
- [ ] T026 [US1] Añadir y ejecutar `backend/tests/integration/reports/test_real_pdf_pipeline.py` con PostgreSQL y productores reales, verificando PDF real reabierto, valores/revisiones, binario/hash persistido y nueva identidad sin alterar anterior; ninguna conexión SMTP debe ser necesaria.
- [ ] T063 [US1] Ejecutar `backend/tests/integration/reports/test_observability.py` con el emisor común real y registrar comandos/resultados saneados en `specs/005-generar-reportes-pdf/validation/observability.md`; comprobar correlación, clasificación de resultados, conteos de nuevas admisiones/terminales y duración, sin inflación por replay/consulta/descarga. Provocar fallo interno y caída de transporte/saturación técnica sin impedir generación, descarga ni commits de resultado/`pdf.failed`; verificar pérdidas visibles, sin exigir visores activos ni acreditar su aceptación externa. Prerrequisitos: T062 y T026; completar antes de T027.
- [ ] T027 [US1] Ejecutar T006–T007/T016–T017/T026 y comprobar evidencia de T063; registrar resultados reales saneados en `specs/005-generar-reportes-pdf/validation/us1.md`. Corregir fallos antes del checkpoint, sin aprobar participantes o revisión visual todavía no realizados.

**Checkpoint**: Generación real y descarga protegida operativas con todas las secciones y controles mínimos; instrumentación propia verificada con el emisor real y evidencia T063, también con transporte técnico caído. Las historias posteriores profundizan extremos y evidencia.

## Phase 4: User Story 2 — siete categorías en una página (P1)

**Goal**: Composición legible y verificable para todas las escalas, textos/cifras extensos y evolución de CAT-01.
**Independent Test**: Los siete escenarios US2 producen una página A4 íntegra, legible al 100 %, tabla de siete categorías y gráfico correcto; CAT-01 calculada/mixta conserva segmentos/base/alcance sin convertirse en medición apta de costos.

### Pruebas de US2

- [ ] T028 [P] [US2] Escribir `backend/tests/unit/reports/test_layout_limits.py` con nombres largos, valores grandes/pequeños, siete filas y advertencias; inspeccionar tamaños/cajas y bytes con lector independiente, sin considerar éxito un PDF que no cabe. Prerrequisito: US1.
- [ ] T029 [P] [US2] Escribir `backend/tests/unit/reports/test_chart_blocks.py` para horas reales/desfases, días/meses, vacíos, cobertura parcial y ausencia total, conservando cada bloque sin interpolar ni recalcular totales desde detalle faltante. Prerrequisito: US1.
- [ ] T030 [P] [US2] Escribir `frontend/tests/unit/report-download.test.tsx` para nombre/escala/período, estados y descarga de la identidad seleccionada, conservando avisos funcionales de composición fallida. Prerrequisito: US1.

### Implementación de US2

- [ ] T031 [US2] Implementar tabla en `backend/src/ecs_ec/reports/energy_table.py` con siete categorías/nombres inequívocos, kWh, cobertura/estado y CAT-01 medida/calculada/mixta con segmentos/base/alcance; identificar «Origen mixto» cuando corresponda y sintetizar períodos, fuentes y bases sin ocultar cambios relevantes. No sumar contribuciones otra vez, recalcular el total del productor ni suprimir categorías sin fuente.
- [ ] T032 [US2] Implementar evolución vectorial en `backend/src/ecs_ec/reports/charts.py` por hora/día/mes según escala, con etiquetas legibles >=10 pt, horas repetidas por desfase y vacíos visibles; espaciar etiquetas sin eliminar bloques ni unir intervalos de información ausente.
- [ ] T033 [US2] Completar reflujo y presupuesto geométrico en `backend/src/ecs_ec/reports/layout.py`, manteniendo seis secciones/márgenes de 10 mm y advertencias esenciales; agrupar información compatible sin truncar su significado y producir fallo funcional si no cabe, jamás anexo o texto menor de 10 pt.
- [ ] T034 [US2] Completar comprobación de cajas, colisiones y tamaño efectivo tras transformaciones en `backend/src/ecs_ec/reports/preflight.py` y `backend/tests/support/pdf_assertions.py`; comparar manifiesto con bytes reales, no acreditar legibilidad solo por extracción de texto o tamaño nominal de fuente.
- [ ] T035 [US2] Incorporar TTF/licencia e incrustación reproducible en `backend/src/ecs_ec/reports/fonts/README.md` y `backend/src/ecs_ec/reports/renderer.py`, verificando caracteres españoles/unidades y ausencia de glifos faltantes sin depender de fuentes remotas al abrir.
- [ ] T036 [US2] Añadir y ejecutar `backend/tests/integration/reports/test_annual_layout.py` con fixtures de referencia del quickstart, CAT-01 calculada y valores positivos pequeños, comparando texto/números/geometría sin redondear a cero aparente ni perder limitaciones. Incluir casos mensual y anual con total válido del productor de 30 kWh: segmentos de 10 medidos y 20 calculados con base CAT-03/CAT-05; conservar total/procedencia en captura y PDF, «Origen mixto» y períodos/fuentes/bases visibles en una página. Incluir cambios de fuente/base con el mismo modo y diagnóstico no numérico por cambio dentro de un intervalo; costos conservan el resultado real de spec-004 sin tratar energía mixta como medición física.
- [ ] T037 [US2] Ejecutar T028–T030/T036 y revisar visualmente los PDFs impresos A4 al 100 %, registrando página/fuentes/cajas y revisión en `specs/005-generar-reportes-pdf/validation/us2.md`; mantener pendiente cualquier revisión no efectuada.

**Checkpoint**: Los PDFs válidos de referencia cumplen una página y >=10 pt con evidencia geométrica y visual; un fallo de composición no sustituye el éxito exigido en esos casos.

## Phase 5: User Story 3 — costos y contraste con boletas (P1)

**Goal**: Presentar cierres efectivos, subtotal disponible y contraste sobre los mismos pares sin duplicar reglas financieras.
**Independent Test**: Los ocho escenarios US3 cubren ciclos cruzados, fuera de período, revisiones, ausencias, créditos/impuestos, contraste pendiente para revisiones seleccionadas y el ejemplo 60 disponible frente a contraste 40/38/diferencia2.

### Pruebas de US3

- [ ] T038 [P] [US3] Escribir `backend/tests/unit/reports/test_financial_summary.py` con ciclos 10/20/30 CLP y boletas 9/29 para primero/tercero: disponible 60/tres ciclos y contraste 40/38/2/dos pares; incluir cierres en inicio/fin, aún no ocurridos, boleta ausente y moneda/base incompatible. Prerrequisito: US2 y productor spec-004 real.
- [ ] T039 [P] [US3] Escribir `backend/tests/integration/reports/test_costs_snapshot_contract.py` contra `Costs.read_snapshot` real, con revisiones vigentes al corte, ciclos contados una vez y signos/bases exactos, sin usar precios actuales ni dobles para aceptación final. Probar corrección de boleta y recálculo sin nueva comparación: `missing_for_selected_revisions`, diferencias nulas y exclusión de importes/conteo del contraste agregado; consultas no crean comparaciones ni retroceden revisiones y capturas anteriores conservan su par exacto. Prerrequisito: US2 y productor spec-004 real.

### Implementación de US3

- [ ] T040 [US3] Implementar presentación de conjuntos por cierre en `backend/src/ecs_ec/reports/financial_summary.py`, usando el snapshot de costos para cantidades, fechas/alcance, moneda/base y subtotal disponible; aplicar «No sumar monedas o bases incompatibles», sin prorratear ni contar revisiones como ciclos distintos.
- [ ] T041 [US3] Implementar presentación pareada en `backend/src/ecs_ec/reports/financial_summary.py`, preservando mismos ciclos/conceptos/bases a ambos lados, cantidad de pares y diferencia de spec-004; separar contraste de totales disponibles con otro alcance.
- [ ] T042 [US3] Incorporar motivos sin cierres, sin boleta, sin pares y cálculo parcial/ausente en `backend/src/ecs_ec/reports/content.py` y `backend/src/ecs_ec/reports/layout.py`; mostrar «Contraste pendiente para estas revisiones» cuando exista cálculo/boleta sin comparación del par seleccionado, distinguiéndolo de recursos ausentes. Excluir ese ciclo del contraste agregado y no mostrar diferencias nulas como cero; conservar importes disponibles con su alcance separado, energía y totalidad de secciones sin inventar importes o presentar subtotales como costo completo.
- [ ] T043 [US3] Concretar formateo financiero en `backend/src/ecs_ec/reports/formatting.py` con moneda, bases, redondeo/signos de spec-004 y créditos/no comparables explícitos; diferenciar facturado comparable y total a pagar sin crear nuevas fórmulas.
- [ ] T044 [US3] Completar persistencia de referencias/revisiones de cierre, cálculo, boleta y comparación en `backend/src/ecs_ec/reports/snapshots.py` y `backend/src/ecs_ec/reports/repository.py`, preservando `comparison_status`, referencias seleccionadas y diferencias nulas cuando el contraste está pendiente; mantener captura inmutable y evidencia de reproducción sin modificar las fuentes ni incorporar comparaciones posteriores a capturas confirmadas.
- [ ] T045 [US3] Añadir y ejecutar `backend/tests/integration/reports/test_costs_pdf_end_to_end.py` con cálculos/boletas reales y PDF reabierto, incluidos CAT-01 calculada sin costo completo, revisión durante render y ciclos sin contraste; operar sin notificaciones ni SMTP. Emitir PDF A con C1/B1/K1, corregir a B2 sin nueva comparación y emitir PDF B pendiente/excluido del contraste, crear K2 para C1/B2 y emitir PDF C con el par; repetir con recálculo C2 sin comparación de C2/B2. Verificar aviso visible, diferencias nulas, ausencia de mutaciones al consultar y captura/bytes/hash de PDF A intactos.
- [ ] T046 [US3] Ejecutar T038–T039/T045 y registrar equivalencia financiera y geometría en `specs/005-generar-reportes-pdf/validation/us3.md`, corrigiendo discrepancias contra fuentes reales antes de aceptar la historia.

**Checkpoint**: Los alcances energético y financiero permanecen distinguibles en la misma página, con pares y limitaciones verificables.

## Phase 6: User Story 4 — calidad y procedencia (P2)

**Goal**: Conservar calidad, origen y coherencia del documento ante ausencias, detalle retirado y cambios concurrentes.
**Independent Test**: Cubrir los siete escenarios US4 con cero válido/sin datos/sin medidor, agregados históricos, procedencia identificada y datos/revisiones recibidos durante render.

### Pruebas de US4

- [ ] T047 [P] [US4] Escribir `backend/tests/unit/reports/test_quality_provenance.py` para cero medido, ausencia, sin fuente, rechazados no atribuibles, procedencia simulada y agregado anual válido con detalle mensual retirado; exigir estados/valores distintos y sin secretos. Prerrequisito: US3.
- [ ] T048 [P] [US4] Escribir `backend/tests/integration/reports/test_cutoff_concurrency.py` con cambios de medición/cálculo/boleta durante captura/render, persistencia y nueva emisión al mismo corte; usar transacciones reales y resultados conocidos. Prerrequisito: US3.

### Implementación de US4

- [ ] T049 [US4] Completar avisos funcionales y procedencia en `backend/src/ecs_ec/reports/quality.py` y `backend/src/ecs_ec/reports/content.py`, indicando origen simulado ya identificado, cobertura/estado y límites por sección; sintetizar períodos/fuentes/bases de procedencia mixta y cambios relevantes dentro del mismo modo sin perder su alcance ni diagnósticos. No incluir credenciales, archivos rechazados ni control privado del simulador.
- [ ] T050 [US4] Completar tratamiento de detalle retirado en `backend/src/ecs_ec/reports/snapshots.py` y `backend/src/ecs_ec/reports/charts.py`: preservar total anual válido de referencia 1200 kWh y declarar detalle mensual ausente, sin sustituirlo por suma parcial ni inventar puntos.
- [ ] T051 [US4] Implementar comparación y hash funcional canónico en `backend/src/ecs_ec/reports/snapshots.py`, excluyendo solo nueva identidad/emisión del contenido comparable; mismas opciones/datos/revisiones/corte conservan valores, agrupaciones y estados, y binario anterior permanece inmutable.
- [ ] T052 [US4] Completar protección de consultas/descargas y retención referenciada en `backend/src/ecs_ec/reports/repository.py` y `backend/src/ecs_ec/reports/api.py`, aplicando permisos vigentes y aniversario común; un permiso técnico no concede PDF y expirar datos técnicos no purga captura/binario protegido.
- [ ] T053 [US4] Añadir y ejecutar `backend/tests/integration/reports/test_failure_events.py` para fallos admitidos de captura/composición/preflight, interrupción y rollback: resultado fallido y `pdf.failed` atómicos, identidad estable y sin duplicación al reconciliar; probar sin consumidor instalado, sin exponer endpoint público de inyección de fallos.
- [ ] T054 [US4] Ejecutar T047–T048/T053 y los casos de calidad/concurrencia del quickstart, registrando fuentes/cortes/hashes y resultados saneados en `specs/005-generar-reportes-pdf/validation/us4.md` sin declarar aprobadas comprobaciones no realizadas.

**Checkpoint**: La captura conserva significado y límites de cada valor, y el productor entrega resultados y fallos durables independientemente del consumidor.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Completar fixtures reproducibles, verificación integral, usabilidad y entrega independiente U1.

- [ ] T055 Crear `scripts/seed_report_reference.py` y documentarlo en `specs/005-generar-reportes-pdf/quickstart.md` para preparar casos diario/mensual/anual y extremos sintéticos mediante módulos reales, incluidos procedencia mixta por segmentos y revisiones financieras con contraste pendiente; rechazar bases de producción y no sobrescribir datos ajenos.
- [ ] T056 Ejecutar instalación bloqueada, suites backend/frontend, exportación Next y pipeline completo con PostgreSQL/costos reales; corregir fallos y registrar versiones, fuentes/tzdata, comandos y resultados en `specs/005-generar-reportes-pdf/validation/acceptance.md` sin sustituir lectura real por un PDF pregrabado.
- [ ] T057 Documentar puertos, estados y entrega productora en `deploy/README.md` y `specs/005-generar-reportes-pdf/contracts/integrations.md`, demostrando generación real, resultado/binario/hash persistidos y `pdf.failed` durable sin consumidor/SMTP; vincular con integración de spec-008 sin importar sus módulos.
- [ ] T058 Realizar diez tareas SC-006 con personas representativas y registrar tiempo/ayuda/interpretación en `specs/005-generar-reportes-pdf/validation/usability.md`; exigir nueve en <=2 minutos y mantener pendiente si no hay resultados reales.
- [ ] T059 Comprobar apertura e interpretación sin red de los documentos de referencia y completar evidencia visual pendiente de T037 en `specs/005-generar-reportes-pdf/validation/offline.md`, preservando una página y contenido indispensable sin enlaces externos necesarios.
- [ ] T060 Auditar documentación de todos los archivos/contratos propios, cobertura FR-001..FR-022/SC-001..SC-006 y limitaciones reales en `specs/005-generar-reportes-pdf/validation/coverage.md`; no marcar checklists de revisión ni afirmar código, pruebas o participantes que no existan.

## Dependencies & Execution Order

| Fase | Tareas | Cantidad | Prerrequisito |
| --- | --- | ---: | --- |
| Setup | T001–T005 | 5 | Especificación y contratos disponibles |
| Fundaciones | T006–T015, T061 | 11 | Capacidades reales core/identity/consumption/audit y productor Costs.read_snapshot; T061 después de T007 |
| US1 P1 | T016–T027, T062–T063 | 14 | Fundaciones y emisor real de spec-007 para T062–T063; T025 → T062 → T026 → T063 → T027 |
| US2 P1 | T028–T037 | 10 | US1 |
| US3 P1 | T038–T046 | 9 | US2 y costos reales |
| US4 P2 | T047–T054 | 8 | US3 |
| Transversal | T055–T060 | 6 | Historias aceptadas; participantes para T058 |
| Total | T001–T063 | 63 | |

```text
core + identidad + consumo + audit/EventWriter ─┐
spec-004 / Costs.read_snapshot ────────────────┴→ Setup → Fundaciones → US1 → US2 → US3 → US4 → Cierre
spec-007 / emisor común real ──────────────────────────────────────────↑
                                                                                   ↓
                                                      resultado real + pdf.failed → consumidor spec-008
```

No existe dependencia inversa del productor hacia el consumidor de notificaciones. Las capacidades comunes pueden implementarse/reutilizarse antes del scheduler/SMTP de spec-008, sin requerir completar esa feature. Si una capacidad real falta, su tarea productora debe resolverse antes del checkpoint afectado; un doble no completa la dependencia.

El emisor común de spec-007 se identifica por capacidad, documentos y rutas en T001/T062. No se implementa dentro de PDF ni se exige terminar visores/recolectores para aceptar esta integración; su caída en ejecución no bloquea operaciones funcionales. Los IDs T061–T063 se incorporan en sus fases para conservar los IDs existentes: T061 después de T007, T062 después de T025/T061 y T063 después de T026/T062 y antes de T027. Todas las tareas siguen pendientes.

Las tareas de un mismo archivo (`models.py`, `services.py`, `snapshots.py`, `api.py`, `layout.py`, `repository.py`) se realizan en orden, nunca en paralelo. Pruebas antes del comportamiento nuevo; modelos antes de migración, captura antes de render, preflight antes de publicación y permisos antes de descarga. Los controles mínimos de una página/seguridad están en US1 y no se difieren a una historia posterior.

## Parallel Opportunities

- T003/T004 en archivos distintos después de T001; T005 espera dependencias preparadas.
- T006/T007 después de setup; T061 espera T007.
- US1: T016 y T017, después de fundaciones.
- T062 modifica archivos compartidos de US1 y se ejecuta secuencialmente después de T025/T061; T063 verifica después de T026 y antes de T027.
- US2: T028, T029 y T030, después de US1.
- US3: T038 y T039, después de US2 y productor real de costos.
- US4: T047 y T048, después de US3.

### Parallel Example: User Story 1

`T016 → backend/tests/integration/reports/test_report_requests.py` y `T017 → frontend/tests/e2e/reports.spec.ts`.

### Parallel Example: User Story 2

`T028 → backend/tests/unit/reports/test_layout_limits.py`, `T029 → backend/tests/unit/reports/test_chart_blocks.py` y `T030 → frontend/tests/unit/report-download.test.tsx`.

### Parallel Example: User Story 3

`T038 → backend/tests/unit/reports/test_financial_summary.py` y `T039 → backend/tests/integration/reports/test_costs_snapshot_contract.py`.

### Parallel Example: User Story 4

`T047 → backend/tests/unit/reports/test_quality_provenance.py` y `T048 → backend/tests/integration/reports/test_cutoff_concurrency.py`.

## Requirement Coverage

| Requisitos | Tareas principales |
| --- | --- |
| FR-001..FR-003 | T012, T016–T019, T024–T027 |
| FR-004..FR-005 | T021–T022, T028, T033–T037 |
| FR-006..FR-009 | T009, T014, T020, T029, T031–T032, T036, T047–T050; modo/segmentos y fixture de procedencia mixta en T009/T014/T031/T036/T049 |
| FR-010..FR-015 | T014, T038–T046 |
| FR-016..FR-019 | T020, T031–T035, T044, T047–T052 |
| FR-020..FR-022 | T013, T015–T027, T048, T051–T054, T059 |
| SC-001 | T028, T033–T037 |
| SC-002 | T006, T016, T029, T036, T048 |
| SC-003 | T038–T039, T045–T046 |
| SC-004 | T042, T047–T050, T054 |
| SC-005 | T026, T037, T059 |
| SC-006 | T058 |
| Entrega productora U1 | T013, T023, T026, T053, T057 |
| FR-013, revisiones sin contraste | T039, T042, T044–T045; diferencias nulas, exclusión del agregado y captura anterior intacta |
| Instrumentación propia — hoja de ruta y spec-007 | T001, T061–T063; emisor real, correlación asíncrona, conteos/duración y continuidad funcional ante caída técnica |

## Implementation Strategy

### MVP First

Completar capacidades compartidas y costos reales, setup/fundaciones y US1. Validar generación real con todas las secciones, corte coherente y mínimos de página/legibilidad, e instrumentación propia T061–T063 con el emisor común real de spec-007. El MVP no usa bytes ficticios ni pospone la seguridad o aceptación mínima de documento.

### Incremental Delivery

Profundizar composición/extremos en US2, escenarios financieros en US3 y calidad/concurrencia en US4. Ejecutar suites pertinentes tras cada cambio y guardar evidencia real. Completar offline/revisión visual y personas antes de declarar todos los criterios satisfechos.

## Notes

Los archivos `validation/` se crean con resultados observados durante implementación. Este backlog no acredita ejecución de aplicación ni altera checklists de revisión. Preservar trabajo previo y no inventar satisfacción de dependencias/participantes ausentes. La lógica de PDF permanece en el monolito.
