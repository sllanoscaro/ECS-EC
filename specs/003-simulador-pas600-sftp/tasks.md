# Tasks: Simulador PAS600 con publicación SFTP

**Fecha**: 2026-11-01. **Funcionalidad**: `003-simulador-pas600-sftp`.
**Estado**: tareas generadas, todas pendientes; revisión de consistencia, implementación y aceptación pendientes.
**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [CLI](contracts/cli.md),
[perfil PAS600](contracts/pas600-profile.md), [SFTP/recepción](contracts/sftp-reception.md),
[ejemplos](contracts/examples/README.md) y [quickstart.md](quickstart.md).
No había `tasks.md` anterior ni alcance trasladado que conservar en 003.

## Contexto compartido del proyecto (ECS-EC)

Leer [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y la
[constitución](../../.specify/memory/constitution.md). 009 posee scaffold/core/UoW/reloj/
auditoría/lifespan; 006, cuentas/sesiones/autorización; 001/002, consumo; 007, emisor
común. 003 implementa herramienta externa y adquisición PAS600/SFTP; no implementa
capacidades ajenas como prerrequisitos. No hay código de aplicación implementado aún.

**Tests**: se incluyen por la verificación de conformidad independiente exigida en FR-004,
los Independent Test/Acceptance Scenarios de las cuatro historias y SC-001..006; la
constituciónIV exige pruebas de validaciones/conversiones. Escribir las pruebas de
comportamiento nuevo antes de su implementación y comprobar el fallo por esa falta,
no por una configuración rota. Pruebas de resultados conocidos y fallos/concurrencia,
sin suites que solo repitan internamente la implementación.

## Formato y rutas

`- [ ] TNNN [P?] [USn?] Descripción con ruta`.
Los IDs son locales a **spec-003**; las dependencias externas usan capacidad/documento/ruta,
nunca un TNNN de otra spec. `[P]` solo permite archivos distintos tras prerrequisitos;
no autoriza concurrencia sobre Compose, locks, CLI, models.py, puertos o migraciones.
Las rutas de código son relativas a la raíz y previstas: no prueban existencia.
No se modifica la spec ni se marcan sus checklists al generar estas tareas.
Cada tarea de código incluye su documentación de archivo y contratos de todos sus
símbolos (propósito/entradas/salidas/errores/efectos), aunque no se repita en cada línea.

## Prerrequisitos por capacidad

| Propietario / documentos | Capacidad y ruta de integración 003 | Momento |
| --- | --- | --- |
| [Plataforma009](../009-fundaciones-plataforma/plan.md), [contrato](../009-fundaciones-plataforma/contracts/integrations.md) | `backend/src/ecs_ec/core/`, `backend/src/ecs_ec/audit/`, `backend/src/ecs_ec/main.py`, Alembic/Compose reales: UoW, reloj/aniversario, auditoría y registro de lifecycle. | Antes del backend US2; no bloquea generación US1. |
| [Consumo001](../001-visualizar-consumo-categorias/contracts/integrations.md), [modelo](../001-visualizar-consumo-categorias/data-model.md) | Fuentes/configuración/revisiones/validación pura de `backend/src/ecs_ec/consumption/`, asociadas con `acquisition/mapping.py`. | Antes de adaptación y configuración real US2. |
| [Historial002](../002-registro-retencion-consumo/contracts/integrations.md), [modelo](../002-registro-retencion-consumo/data-model.md) | `backend/src/ecs_ec/consumption/ports.py` y `reception.py`: Reception.accept/read_attempt con ID/entrada fija, recuperación exclusiva, resultados e idempotencia/cadencia/cobertura. | Verificar contratos de intento definidos y proveedor real antes de service.py/aceptación US2; lectura de cobertura recibe UoW/corte del exportador. |
| [Acceso006](../006-acceso-usuarios-rbac/spec.md), [HTTP consumo](../001-visualizar-consumo-categorias/contracts/http.md) | Sesión/permisos de la UI/GET consumo; identidad SFTP técnica distinta. | Solo para verificar vistas/consultas protegidas, sin crear cuentas en 003. |
| [Observabilidad007](../007-observabilidad-externa/spec.md) | Emisor común de `backend/src/ecs_ec/observability/`, consumido por acquisition. | Para instrumentación propia; visores caídos no bloquean commits ni generación. |

Si falta un proveedor, el responsable de implementación registra el bloqueo de integración
y continúa solo el trabajo que no dependa de él. No sustituir una integración real por
dobles para cerrar aceptación. Inicializar el paquete externo003 sí es alcance propio;
inicializar el monolito/core, identity o consumption corresponde a sus propietarios.

## Phase 1: Setup — preparación propia de 003

**Objetivo**: Preparar el paquete externo y las referencias documentales; registrar las capacidades ajenas sin implementarlas.

**Prueba independiente / checkpoint**: Paquete instalable sin importar backend; procedencia de referencias registrada y faltantes externos identificados por capacidad/documento/ruta.

- [ ] T001 Registrar disponibilidad y límites de las capacidades 009/001/002/006/007 en `specs/003-simulador-pas600-sftp/validation/prerequisites.md`, siguiendo la tabla de dependencias de este archivo; distinguir generación local de recepción integrada, mantener pendientes los faltantes y no ejecutar implementación de otras specs como setup de 003.
- [ ] T002 Crear el paquete independiente y su entrypoint `pas600-sim` en `tools/pas600_simulator/pyproject.toml`, `tools/pas600_simulator/uv.lock`, `tools/pas600_simulator/src/pas600_simulator/__init__.py` y `tools/pas600_simulator/README.md`; fijar Python `>=3.14,<3.15`, declarar Pydantic2/AsyncSSH/simplejson en `project.dependencies` y pytest/herramientas de pruebas en `dependency-groups.dev`, verificar instalación bloqueada `--no-dev` y ausencia de imports/dependencias runtime del backend. Documentar propósito/contratos desde el primer archivo.
- [ ] T003 [P] Preparar referencias independientes CSV/JSON y resultados esperados estáticos en `tools/pas600_simulator/tests/fixtures/reference/README.md` y `tools/pas600_simulator/tests/fixtures/reference/expected.json`: registrar DOCA0172EN-19, páginas, procedencia y SHA-256; contrastar visualmente las filas CSV y las convenciones JSON, separar ejemplos documentales de tensión/IO del caso energético sintético 100/104 y no producir el oráculo con el serializador bajo prueba. Registrar el límite de IDs físicos y de la frontera de sesión.

## Phase 2: Foundational — contratos y utilidades locales

**Objetivo**: Fijar esquemas, calendario, exactitud, identidad y persistencia local utilizados por las historias; esta fase no requiere infraestructura app.

**Prueba independiente / checkpoint**: Pruebas de configuración válida/inválida, DST, determinismo y recuperación de escritura local; completar antes de comenzar US1–US4.

- [ ] T004 Escribir primero pruebas de configuración/tiempo/identidad/estado en `tools/pas600_simulator/tests/unit/test_scenario.py`, `tools/pas600_simulator/tests/unit/test_calendar.py`, `tools/pas600_simulator/tests/unit/test_identity.py` y `tools/pas600_simulator/tests/unit/test_journal.py`; cubrir duplicación de medidor, ausencia de categorías, offsets/DST, extremo no divisible, Decimal no finito, hash estable, output existente y escritura interrumpida. Verificar fallo por comportamiento faltante antes de T005/T006/T007.
- [ ] T005 Definir `SimulationScenario`, `SimulatedPublisher`, `SimulatedMeterChannel` y descriptor en `tools/pas600_simulator/src/pas600_simulator/scenario.py`, con todos los campos de modelo/CLI/perfil: `schema_version`, `algorithm_version`, `profile_id`, semilla, publicador, categorías, período/zona, muestreo, `publication_time`, formato/rangos/anomalías. Conservar literalmente las restricciones “siete estados de categoría”, “uno por escenario”, “identidad local/ReducedID únicos por PAS600”, “categoría medida única”, “Sin origen ficticio para CAT-01 calculada”; campos desconocidos rechazados, CAT-01..07 únicas, sin canal/rango/tasas si no hay medidor, `Wh|kWh|MWh`, `cumulative|interval` y timestamp_role explícito. Incluir descriptores sintéticos identificados y evidencia obligatoria para soporte no inicial; defaults siete medidores, 15 minutos y cero anomalías.
- [ ] T006 Implementar validación temporal/decimal y claves canónicas en `tools/pas600_simulator/src/pas600_simulator/calendar.py` y `tools/pas600_simulator/src/pas600_simulator/identity.py`: “`start < end`, extremos con offset, zona IANA válida y diferencia divisible por muestreo”, “`min>=0`, `max>=min`, finitos”, unidad/duración compatibles y valores representables con quantum positivo. Usar UTC/zoneinfo sin inventar horas DST, enteros/Decimal sin float, SHA-256 versionado por dominios; hash lógico excluye formato/output/tiempos reales y hash completo identifica formato. Documentar algoritmo e impedir períodos truncados o escalado implícito de rangos.
- [ ] T007 Implementar almacenamiento local base en `tools/pas600_simulator/src/pas600_simulator/journal.py`: `LocalRun` con UUID real, hash lógico, rutas, fecha real y estado “`generating|generated|publishing|stopped|completed|failed`”; “escritura temporal, fsync y rename atómico”, output nuevo/vacío y evidencia inmutable tras generación. Crear estructura `data/` y `control/` del contrato; preservar estado ante caída sin presentar generación incompleta como terminada, reservando campos de journal de transferencia para US2.

## Phase 3: User Story 1 — Generar archivos compatibles con un PAS600 (P1, MVP)

**Objetivo**: Generar escenarios normales equivalentes en CSV/JSON, atribuibles a cada medidor, incluidos subconjuntos sin total e histórico local.

**Prueba independiente / checkpoint**: Con igual semilla/período, CSV/JSON representan valores e instantes iguales según un lector de pruebas independiente; 100/104 produce 4 kWh sin consumo inicial, siete categorías y >=12 meses se generan sin red. El cálculo integrado de CAT-01 del escenario US1.6 se verifica al disponer de US2 + consumo001/002.

- [ ] T008 [P] [US1] Escribir pruebas de contrato CSV contra referencias revisadas en `tools/pas600_simulator/tests/contract/test_csv_profile.py`: siete filas de preámbulo, campos/UTF-8/comillas/CRLF, filas de tópico con tres celdas iniciales, número real de filas, offset y nombres nativos; valores conocidos y ausencia de columnas privadas. Mantener el lector de verificación en el test independiente de los writers y del backend; deben fallar antes de T014.
- [ ] T009 [P] [US1] Escribir pruebas de contrato JSON contra referencias revisadas en `tools/pas600_simulator/tests/contract/test_json_profile.py`: CewsMessage, remoteId, series/records, números Decimal finitos, UTC+offset t, nombre y ausencia de propiedades de prueba. Verificar equivalencia energética/temporal con resultados estáticos, sin leer mediante el parser ECS-EC; deben fallar antes de T015.
- [ ] T010 [P] [US1] Escribir casos conocidos de generación en `tools/pas600_simulator/tests/unit/test_generator.py` y `tools/pas600_simulator/tests/contract/test_generation_equivalence.py`: siete medidores distintos, CAT-03/CAT-05 sin CAT-01, cero medidores, CAT-01 medida independiente, rango degenerado representable, energía por intervalo frente a contador N+1 y referencia inicial; añadir repetición con distinto orden de serialización y cortes 24 h/256000 bytes antes de T013/T016.
- [ ] T011 [P] [US1] Escribir pruebas de `validate`/`generate` en `tools/pas600_simulator/tests/contract/test_generation_cli.py`: no red ni backend, configuración inválida sin efectos, formato seleccionable, output existente rechazado, manifiesto/oráculo separado y códigos 0/2/5; deben fallar antes de T018.
- [ ] T012 [US1] Definir `ExpectedSample` y `LocalPublication` en `tools/pas600_simulator/src/pas600_simulator/publication.py`: “Clave lógica determinista categoría/origen/canal/índice”, inicio/fin, energía, contador previo/posterior y estado normal; publicación con clave estable, tiempo simulado, categorías, lista completa nombre/tamaño/hash, perfil y manifiesto canónico. Aplicar “No aparece en los bytes nativos” a claves de control y “Cambiar bytes exige nueva generación, nunca reintento”; documentar identidades distintas de las del servidor.
- [ ] T013 [US1] Implementar generador normal en `tools/pas600_simulator/src/pas600_simulator/generator.py` usando T005/T006/T012: solo medidores presentes, ninguna suma CAT-01, rangos por intervalo, valores deterministas y acumulados exactos. Cumplir “Para acumulados generar N+1 lecturas, con una referencia inicial no alterable por las tasas” y “Cada intervalo completo pertenece a N”; historial por ciclos sin sleep/red, sin convertir 12 meses calendario en un plazo fijo de días.
- [ ] T014 [P] [US1] Implementar serializador normal CSV en `tools/pas600_simulator/src/pas600_simulator/csv_writer.py` tras T012/T013 y con T008 escrito: metadatos nativos, IDs del descriptor, siete filas previas, tres celdas vacías de presentación de tópicos, estado Error 0, offset/fecha local, unidad y Decimal exactos; encabezado Historical Intervals según filas emitidas, UTF-8/CRLF/comillas y ninguna marca ECS-EC.
- [ ] T015 [P] [US1] Implementar serializador normal JSON en `tools/pas600_simulator/src/pas600_simulator/json_writer.py` tras T012/T013 y con T009 escrito: envoltura CewsMessage, contentType data/cewsVersion 3.0.0, remoteId explícito, series y t entero en milisegundos, v numérico con simplejson Decimal; omitir s en salida normal y cualquier campo propio de pruebas.
- [ ] T016 [US1] Completar nombres/división/manifiestos de publicación en `tools/pas600_simulator/src/pas600_simulator/publication.py` tras ambos writers: CSV por dispositivo/frecuencia, JSON multidispositivo, “hasta 24 horas de muestreo” y “JSON además <=256000 bytes UTF-8” incluida envoltura, sin partir registros; n desde 1 contiguo, publication_time fijo con milisegundos, saneado con ~, rechazo de colisiones/traversal y lista completa con hashes congelados.
- [ ] T017 [US1] Crear oráculo/informe base en `tools/pas600_simulator/src/pas600_simulator/report.py`: `ControlReport` con configuración saneada, perfil/semilla, ExpectedSample anteriores a cualquier alteración, asignaciones vacías, cantidades y manifiestos de generación; “`not_configured` difiere de categoría medida con 100 % de omisión”. Guardar expected.jsonl/scenario.safe.json/manifest.json y distinguir tiempos/UUID reales de datos simulados; este control mínimo permite aceptar US1 sin esperar US4.
- [ ] T018 [US1] Implementar `validate` y `generate --format` en `tools/pas600_simulator/src/pas600_simulator/cli.py`, integrando escenario/generador/writers/journal/control; resumen humano, JSON local versionado y stderr saneado, códigos 0/2/5; validar configuración completa antes de escribir. Rechazar salida no vacía y mantener generación local independiente del backend; los comandos de transferencia/contraste se incorporan en US2/US4.
- [ ] T019 [P] [US1] Crear ejemplos saneados por defecto y correspondencias sintéticas explícitas en `tools/pas600_simulator/examples/seven-meters.json` y `tools/pas600_simulator/examples/descriptors.synthetic.json`: siete iEM3150 de IDs distintos, total medido propio, muestreo 15 minutos, rangos expresos por categoría/duración/unidad y tasas cero. Validarlos mediante el CLI y explicar que tópicos sintéticos no son IDs certificados del dispositivo.
- [ ] T020 [P] [US1] Crear `tools/pas600_simulator/examples/partial-no-total.json` y `tools/pas600_simulator/examples/historical-12m.json` con CAT-03/CAT-05 sin CAT-01 y, respectivamente, doce meses calendario/siete categorías; añadir prueba de conteo/streaming y generación sin red en `tools/pas600_simulator/tests/contract/test_historical_generation.py`. No inventar rangos físicos de instalación ni reclamar retención temporal ya transcurrida.
- [ ] T021 [US1] Ejecutar pruebas y validación local US1 de `specs/003-simulador-pas600-sftp/quickstart.md` y registrar comandos/locks, conformidad por referencia independiente, igualdad CSV/JSON, caso 100/104, ausencia de medidores ficticios, conteos y duración/tamaño históricos en `specs/003-simulador-pas600-sftp/validation/us1.md`. Verificar todos los formatos/cortes; no afirmar integración de CAT-01 calculada ni compatibilidad física a partir de estos resultados locales. Tras disponer de CLI/ejemplos, ejecutar uv sync/run del paquete con --locked --no-dev, validar seven-meters.json y generar en output temporal nuevo; comprobar salidas sin pytest ni backend instalado y registrar los comandos.

## Phase 4: User Story 2 — Publicar al destino SFTP de ECS-EC (P1)

**Objetivo**: Entregar lotes completos con identidad estable, normalizarlos dentro del monolito y registrar resultados reales de recepción sin confundirlos con transferencia.

**Prueba independiente / checkpoint**: Con receptor local y PostgreSQL/consumo reales: solo EOF limpio tras todos los CLOSE sella el lote; probar password/clave, host no reconocido, transferencia lenta/interrumpida, reenvío/deduplicación y tres intentos totales. Los ciclos/reintentos respetan >=900 segundos reales desde fin anterior; una publicación produce una actualización lógica por categoría.

- [ ] T022 [US2] Verificar antes de integración los proveedores reales de 009 (UoW/reloj/aniversario/auditoría/lifespan/migración), 001 (fuentes/configuración/validación) y 002 (Reception.accept/read_attempt, entrada fija, recuperación exclusiva del mismo intento, resultados y lectura de cobertura con UoW/corte del exportador), registrando interfaces/estado en `specs/003-simulador-pas600-sftp/validation/prerequisites.md`; comprobar el contrato ya definido de attempt_id y read_attempt en `backend/src/ecs_ec/consumption/ports.py` con su propietario. Si falta la capacidad, registrar bloqueo externo, sin implementar almacenamiento/recepción/catálogo ajenos ni declarar E2E con dobles.
- [ ] T023 [US2] Preparar `backend/src/ecs_ec/acquisition/__init__.py` y `backend/tests/integration/acquisition/conftest.py` sobre plataforma existente; incorporar dependencias 003 en `pyproject.toml` y `uv.lock` secuencialmente, fijar marcadores de pruebas largas/DB y fixtures PostgreSQL 18/SFTP locales con identidades técnicas de prueba; usar TEST_DATABASE_URL aislada y conservar scaffold 009 sin crear otro proceso de aplicación.
- [ ] T024 [P] [US2] Escribir pruebas de cliente/cadencia en `tools/pas600_simulator/tests/unit/test_transport.py` y `tools/pas600_simulator/tests/contract/test_transport_cli.py`: password/clave, known_hosts obligatorio, probe excluido, 899/900 s desde fin incluso fallido/lento, lock entre procesos, cambio UTC/reinicio, tres intentos totales, fallo permanente, hashes alterados y reenvío íntegro. Verificar fallos antes de T041/T042/T045.
- [ ] T025 [P] [US2] Escribir contrato de listener/lote en `backend/tests/contract/acquisition/test_sftp_session_batch.py`: CLOSE explícito frente a cierre implícito, EOF limpio frente a connection_lost/close genérico, excepción del cliente tras primer archivo y handles pendientes; verificar ninguna promoción por tamaño/mtime/parser, sesión vacía/probe, nombres/índices, cuotas/traversal y acceso técnico limitado. Usar SFTP local real con clave administrada; fallar antes de T035/T036.
- [ ] T026 [P] [US2] Escribir pruebas de lectores/correspondencia/deltas en `backend/tests/unit/acquisition/test_native_readers.py` y `backend/tests/unit/acquisition/test_counters.py`: CSV LF/CRLF/tres-cuatro celdas/offset/DST/Error19/NaN, JSON Decimal/t/s, magnitud no admitida, 100/104=4, cero, primera referencia, hueco, descenso/reset, tardío, inválida luego corregida y cambio de descriptor. Tomar fixtures independientes; fallar antes de T037/T038/T039/T040.
- [ ] T027 [P] [US2] Escribir pruebas PostgreSQL de exclusión/reinicio/retención en `backend/tests/integration/acquisition/test_recovery.py`: caídas antes/después de fsync/sellado/commit/copia de resultado002, dos procesadores, reenvío equivalente/conflictivo, revisión semántica distinta, too_early y reenvío admisible, observación inválida sin reserva canónica, candidato aún rechazado conservado y protección de dependientes. Verificar fallos antes de T029/T030/T031/T033/T043. Congelar ID/entrada antes de llamar; recuperar concurrentemente el mismo intento sin repetir categorías, comprobar resultado completed original incluso too_early, not_found solo tras lectura autorizada satisfactoria y attempt_payload_conflict para igual ID con otra entrada; DB caída no es inexistencia ni éxito vacío.
- [ ] T028 [P] [US2] Preparar prueba larga seleccionable `real_time` en `backend/tests/integration/acquisition/test_real_time_publication.py` que mida con transporte y reloj reales el fin→inicio >=900 s para ciclos y reintentos, incluidos lento/fallo; comprobar aceptación/deduplicación/categorías con 002 real. No introducir endpoint de reloj ni variable que reduzca intervalo en aceptación; ejecutarla en T048, manteniendo unitarias virtuales separadas.
- [ ] T029 [US2] Definir `AcquisitionBinding`, `SftpSessionAttempt` y `ReceivedFile` en `backend/src/ecs_ec/acquisition/models.py` y DTOs en `backend/src/ecs_ec/acquisition/schemas.py`, con todos los campos de data-model.md: binding con edificio/identidad/directorio/perfil/descriptores/fuentes/zona/muestreo/habilitación y “Versiones históricas inmutables”; sesión “`receiving|sealed|aborted`”, “manifiesto sellado nullable”, “`publication_id|null`”, correlación/plazo; archivo con ruta interna/offsets/hash/CLOSE/plazo, “`writing|closed|sealed|aborted`” y “`parse_status: pending|parsed|unreadable`”. Aplicar “UUID internos generados por el servidor; revisiones positivas; `timestamptz`, NUMERIC y JSONB tipado”, sin usar IDs remotos como actor ni crear fuentes001.
- [ ] T030 [US2] Añadir `NativePublication` y `PublicationEvaluation` a `backend/src/ecs_ec/acquisition/models.py` y `backend/src/ecs_ec/acquisition/schemas.py`: publicación con binding/revisión semántica/perfil/publicador/ciclo, publication_ref, lista completa ordenada nombres/tamaños/hashes, bytes/sealed_at/plazo y “`queued|processing|evaluated|partial_failure`”; evaluación con publicación/correlación/fechas, “attempt_id002 nullable antes de preparar la entrada” y “`pending|processing|completed|partial_failure`”. Aplicar “Comparar lista además del hash” y “Una reevaluación tiene nuevo ID, recuperación conserva el suyo”; reenvío no suprime evaluación de rechazos temporales. Añadir input_schema_version positiva e input_records canónicos ordenados/input_digest SHA-256: null antes de preparar recepción, fijados juntos con attempt_id antes de llamar002 e inmutables después; la recuperación no reconstruye entrada desde nuevas lecturas.
- [ ] T031 [US2] Añadir `NativeReading`, `IntervalCandidate` y `AdaptationResult` a `backend/src/ecs_ec/acquisition/models.py` y `backend/src/ecs_ec/acquisition/schemas.py`: observación con identidad nativa/binding semántico/token/valor/unidad/calidad/archivo-posición/plazo, “instante UTC nullable si ilegible”, “referencia canónica válida nullable” y “`valid|invalid|conflict|reference_only`”; candidato con origen/categoría/inicio-fin/valor-unidad/extremos/perfil-revisión/evidencia, sin aceptación propia; adaptación con evaluación/archivo/posición, causa/candidato nullable y “`parsed|invalid|reference_only|gap|counter_decreased|unsupported_quantity|candidate|conflict`”. Aplicar “Unicidad de observación: archivo/serie/posición”, canónica válida por “binding/revisión semántica/origen/canal/instante” y candidato por “edificio/origen/categoría/inicio/fin y pares originales equivalentes”; inválidas no bloquean una válida posterior.
- [ ] T032 [US2] Crear migración de tablas/índices/constraints 003 en `backend/migrations/versions/acquisition_003_initial.py`, enlazada al head Alembic real de 009/001/002; persistir nulabilidad/estados/unicidades de T029/T030/T031 y referencias históricas protegidas “sin DELETE CASCADE”. Probar upgrade y rollback de migración en DB aislada; no reservar número de revisión global ni recrear tablas consumo/audit/identity.
- [ ] T033 [US2] Implementar repositorio/UoW de adquisición en `backend/src/ecs_ec/acquisition/store.py`: manifiestos inmutables y comparación completa, sesiones/claims PostgreSQL, observaciones versus primera canónica válida, candidatos/evaluaciones recuperables y referencias a resultados002. Conservar “mínimo doce meses calendario desde registro o revisión sustantiva con helper 009 y zona/plazo persistidos” y evidencia hasta “máximo plazo de sus dependientes”; sin purga automática ni pérdida de candidatos/identidades tras retirada permitida. Leer estado después del lock y no mantener locks003 durante recepción002.
- [ ] T034 [US2] Implementar settings y carga de bindings versionados en `backend/src/ecs_ec/acquisition/config.py` y comando técnico documentado en `backend/src/ecs_ec/acquisition/cli.py`: habilitación PAS600_SFTP_ENABLED, puerto local2222, host key persistida, directorio virtual, secreto/verificador externo y fuentes001 existentes. Validar edificio/publicador/descriptor y mantener versión semántica; no crear cuentas ni fuentes ni derivar autorización del archivo. El comando de mantenimiento exige proceso autorizado del despliegue y registra auditoría saneada.
- [ ] T035 [US2] Implementar staging/commit recuperable en `backend/src/ecs_ec/acquisition/staging.py`: archivo nuevo privado por sesión, prefijo contiguo de offsets desde cero, hash/fsync antes de CLOSE OK y sellado inmutable con manifiesto durable solo tras EOF limpio; recuperar caídas sin inventar bytes faltantes. Aplicar literalmente “JSON <=256000 bytes”, “CSV <=8 MiB”, “<=10000 archivos/sesión y <=128 MiB/sesión”, “<=2 sesiones activas por binding, solo una publicación en escritura por publicador”; resource_limit aborta lote y conserva pendientes, sin heurísticas de completitud.
- [ ] T036 [US2] Implementar listener AsyncSSH en `backend/src/ecs_ec/acquisition/sftp_server.py` sobre T035/T034: SFTP exclusivo por binding y sin shell/forwarding, contraseña o clave autorizada, raíz virtual sin symlinks/traversal/sobrescritura; distinguir explícitamente CLOSE de protocolo de limpieza y SSH CHANNEL_EOF de desconexión. Cero handles/errores antes de sellar; abortar sesión incompleta y excluir probe/vacías; comprobar algoritmos configurados compatibles sin activar heredados débiles. Documentar que el firmware real debe demostrar esta convención antes de habilitarlo.
- [ ] T037 [P] [US2] Implementar lector CSV en `backend/src/ecs_ec/acquisition/csv_reader.py` tras esquema y fixtures, sin importar writer del simulador: estructura nativa, dos variantes de celdas de presentación, nombre/metadata/tópicos/filas, Decimal y “instant_UTC = local_timestamp - offset_minutes”; validar contra zona, separar error estructural/registro y conservar token/posición/original. Error19/NaN no son cero y los registros independientes válidos continúan.
- [ ] T038 [P] [US2] Implementar lector JSON en `backend/src/ecs_ec/acquisition/json_reader.py` tras esquema y fixtures, sin importar writer: validar envoltura nativa, serie/tópico/remoteId, Decimal numérico finito y t entero; “instant_UTC = series.timestamp + t milliseconds”. Conservar tokens/posiciones/calidad; s ausente normal, s=false inválido y s=true como invalid con causa unsupported_quality según perfil inicial; distinguir JSON ilegible y registro no interpretable, sin inventar unidad.
- [ ] T039 [US2] Implementar correspondencias explícitas y resolución histórica en `backend/src/ecs_ec/acquisition/mapping.py`: vincular publicador CSV/JSON, medidor, canal, magnitud/unidad/semántica a fuente y categoría001 del binding; preservar descriptor/revisión de evidencia y no deducir categoría del modelo/texto ni corregir configuración001. Magnitud ajena/fuente no conocida/sin medidor/cambio incompatible produce diagnóstico trazable; CAT-01 calculada no se publica como medidor.
- [ ] T040 [US2] Implementar normalización/candidatos en `backend/src/ecs_ec/acquisition/counters.py`: “`E([t0,t1))=C(t1)-C(t0)`” solo para válidas compatibles y “`t1=t0+sampling`”, “igualdad produce cero válido con cobertura”, primera lectura referencia; omisión/inválida/descenso impide par, descenso inicia segmento nuevo, tardías completan solo pares adyacentes. Canónica solo primera válida, conflicto entre válidas distintas sin sustituir pares incorporados; interval usa timestamp_role+sampling. Mantener origen/unidad/extremos y nunca puentear/repartir huecos.
- [ ] T041 [US2] Implementar cliente SFTP y TransferAttempt en `tools/pas600_simulator/src/pas600_simulator/transport.py`: resolver secretos solo en memoria, known_hosts/pin obligatorio, host desconocido/cambiado detiene, contraseña/clave y probe reservado; subir lista completa original secuencialmente, CLOSE confirmado por archivo y EOF explícito solo después de todos. Excepción/fallo aborta sin EOF normal aun dentro de context manager; preservar UUID/ordinal/inicio-fin UTC/duración monotónica/destino saneado/resultados/código/próxima espera, nunca credenciales o volcado de transporte.
- [ ] T042 [US2] Implementar coordinación durable de envío/reintento en `tools/pas600_simulator/src/pas600_simulator/journal.py` y `tools/pas600_simulator/src/pas600_simulator/transport.py`: “un candado por destino/publicador protege la cadencia entre procesos” y “El journal conserva ordinales al reiniciar”; mínimo900s desde fin de cada intento, uno activo y espera completa tras reinicio, independiente de tiempo simulado/adelantos UTC. Tres intentos totales iniciales configurable>=1, errores permanentes detienen, transitorios limitados y agotamiento conserva archivos; reenviar conjunto completo sin regenerar nombres/bytes ni resetear historial.
- [ ] T043 [US2] Implementar `Acquisition.process_sealed` en `backend/src/ecs_ec/acquisition/service.py` sobre store/readers/mapping/counters: procesar solo lote sellado y persistir evaluación, pares/candidatos, attempt_id generado por003, correlación y entrada canónica completa/ordenada con versión/digest antes de llamar002; liberar locks003. Consumir Reception.accept/read_attempt definidos por002: tras pérdida de respuesta consultar estado, crear/continuar con mismo ID/entrada congelada solo lo no confirmado, devolver completed original y tratar DB fallida como error, no not_found. Coordinar dos recuperaciones y detectar attempt_payload_conflict sin mutar resultados/reloj; llamada lógica por evaluación y no por fragmento. Reenvío explícito completo abre nuevo intento; too_early confirmado no se reevalúa en recuperación ni autoacepta. Con solo referencia/ilegibles no crear actualización/evento de consumo.
- [ ] T044 [US2] Registrar listener y trabajo cancelable/recuperación en `backend/src/ecs_ec/acquisition/lifecycle.py` y composición existente `backend/src/ecs_ec/main.py` de 009, secuencialmente y tras T043/T036: recuperar publicaciones selladas/evaluaciones inconclusas al arrancar, abortar sesiones de escritura antiguas sin promoverlas, exclusión PostgreSQL ante dos procesadores y parada ordenada. No crear worker/receptor de aplicación separado ni iniciar trabajo desde GET; deshabilitar simulador no afecta operación de plataforma.
- [ ] T045 [US2] Añadir `test-connection`, `publish --resume` y `resend --publication` en `tools/pas600_simulator/src/pas600_simulator/cli.py`: validar transporte/timeouts y hashes/manifiesto exacto antes de conectar, excluir control/configuración, presupuesto nuevo explícito de resend sin eludir espera. Conservar “`file_status: generated|pending|transferred|failed`”, “`session_end: clean|aborted|unknown`” y publicación “`pending|transferred|failed|uncertain`”; transferred solo con CLOSE OK, sin afirmar aceptación002. Códigos0/2/3/4/5 y estados durables; el control base se actualiza con referencias a intentos saneados.
- [ ] T046 [US2] Integrar únicamente settings/puerto2222, host key/credenciales montadas y volumen persistente003 en `compose.yaml` y `.env.example` existentes; actualizar `deploy/README.md` y `specs/003-simulador-pas600-sftp/quickstart.md` con carga concreta de binding y verificación de clave local administrada. Usar la imagen/proceso app de009 y secuenciar cambios de archivos compartidos; sin contenedor SFTP/worker ni secretos versionados, con destino VPS configurable sin cambiar contrato.
- [ ] T047 [US2] Crear `tools/pas600_simulator/examples/transport.local.json` y fixtures privados de prueba en `backend/tests/fixtures/pas600/local/README.md`: host/puerto/directorio/usuario/alias/known_hosts y auth por password_env o private_key_file con passphrase_env opcional, separación900, max_attempts3 y timeouts30/60/300 positivos. No aceptar contraseña inline; documentar provisión de host key/credenciales efímeras verificadas para ambos modos, fuera de datos/informes.
- [ ] T048 [US2] Ejecutar T024/T025/T026/T027 y T028 con dependencias reales y registrar evidencia en `specs/003-simulador-pas600-sftp/validation/us2.md`: lotes multiarquivo, interrupciones/EOF perdido/agotamiento, reenvío sin doble consumo, mismo intento recuperado y rechazo demasiado temprano seguido de reenvío explícito válido. Medir >=900s reales desde fin; demostrar una actualización lógica por categoría y resultados002. Incluir CAT-01 calculada de CAT-03/CAT-05 y total medido propio del caso US1.6/SC-001; no declarar integración con dobles. Verificar recuperación/read_attempt sin efectos, payload distinto con igual ID rechazado y completed original sin reevaluar; incluir test-connection/publicación con paquete --no-dev para comprobar dependencias runtime.

## Phase 5: User Story 3 — Introducir anomalías configurables (P1)

**Objetivo**: Seleccionar defectos exactos y reproducibles por categoría/posición, conservando el oráculo y separando defectos por muestra de corrupción de archivo.

**Prueba independiente / checkpoint**: 100 previstas y tasas10/10/10 dan exactamente10 omitidas,10 de formato,10 fuera de rango y70 normales; cubrir0/100%, categorías no elegidas intactas y configuración inválida antes de efectos. Un archivo corrupto puede transferirse correctamente mientras otros independientes se analizan.

- [ ] T049 [P] [US3] Escribir pruebas de tasas/selección/configuración en `tools/pas600_simulator/tests/unit/test_anomaly_selection.py`: floor con denominadorN original,100=10+10+10+70,0/100%, tasas fraccionarias/suma>100, posiciones explícitas y exclusión de categorías sin medidor; comprobar ranking/orden/semilla y no solapamiento antes de T052/T053.
- [ ] T050 [P] [US3] Escribir pruebas de efectos conocidos en `tools/pas600_simulator/tests/unit/test_anomaly_values.py`: omisión sin cero, tipo/fecha erróneos, outlier estrictamente por encima/debajo del rango por duración/unidad, incrementos acumulados con desplazamiento posterior y vecino afectado por extremo inválido; combinación no representable rechazada antes de generar. Deben fallar antes de T054/T055.
- [ ] T051 [P] [US3] Escribir contrato de corrupción explícita CSV/JSON en `tools/pas600_simulator/tests/contract/test_structural_anomalies.py`: selector de archivo válido, estructura rota solicitada, archivos no elegidos intactos, conteos de archivo separados de muestras, Historical Intervals tras omisiones y snapshots anteriores a alteración. Deben fallar antes de T056/T057.
- [ ] T052 [US3] Completar reglas de anomalía y `AnomalyAssignment` en `tools/pas600_simulator/src/pas600_simulator/scenario.py` y `tools/pas600_simulator/src/pas600_simulator/anomalies.py`: “Clase `missing|format|out_of_range`, índice/muestra, antes/después, causa y alcance; una clase por muestra”, “Archivo corrupto tiene asignación aparte por archivo/operación”, “Tasas Decimal entre 0 y 100 y suma <=100” y “posiciones explícitas deben tener exactamente el conteo requerido, ser válidas y no solaparse”. Incluir categorías/posiciones y corrupción elegida explícitamente, no defectos aleatorios fuera de alcance.
- [ ] T053 [US3] Implementar asignación excluyente en `tools/pas600_simulator/src/pas600_simulator/anomalies.py`: “`n_missing=floor(N*p_missing/100)`”, análogo para las otras clases, ranking SHA-256 con dominios separados entre posiciones libres; “Las categorías sin medidor no tienen N ni asignaciones” y “No asignar muestras a categorías desconocidas/inactivas”. La referencia inicial acumulada no se altera ni cuenta enN; conservar selección estable para ambos formatos.
- [ ] T054 [US3] Implementar omisiones y alteraciones de tipo/fecha por muestra en `tools/pas600_simulator/src/pas600_simulator/anomalies.py`: conservar ExpectedSample original, aplicar solo posiciones/categorías asignadas y omitir realmente la lectura correspondiente sin reemplazar por0. Registrar tanto defecto deliberado como intervalos no normalizables por extremos ausentes/inválidos, sin contar esos vecinos como asignaciones extra ni inventar filas del medidor ausente.
- [ ] T055 [US3] Implementar anomalías fuera de rango en `tools/pas600_simulator/src/pas600_simulator/anomalies.py`: “Outlier superior: `max+quantum`; inferior: `min-quantum`, con conversiones exactas”, rango por duración y unidad, alterar incremento y desplazar contadores posteriores conservando los demás incrementos. Rechazar configuración imposible antes de efectos y documentar el delta, sin usar el contador absoluto como consumo ni cambiar reglas de limpieza001.
- [ ] T056 [US3] Implementar corrupción de estructura como etapa final en `tools/pas600_simulator/src/pas600_simulator/anomalies.py`, después de serializar/fragmentar archivos normales: resolver selector de nombre/índice contra manifiesto, rechazar archivo inexistente/selector ambiguo y aplicar solo la operación CSV/JSON elegida. Conservar relación con archivo previo/control y calcular hash final publicado; no agregar flags de defecto al archivo nativo ni reclasificar cada registro de un archivo roto.
- [ ] T057 [US3] Integrar etapas/validación completa en `tools/pas600_simulator/src/pas600_simulator/generator.py`, `tools/pas600_simulator/src/pas600_simulator/publication.py`, `tools/pas600_simulator/src/pas600_simulator/csv_writer.py`, `tools/pas600_simulator/src/pas600_simulator/json_writer.py` y `tools/pas600_simulator/src/pas600_simulator/report.py`, secuencialmente tras US1: validar antes de generar, snapshot→asignar→alterar→serializar→corromper→congelar; actualizar counts/manifiesto y distinguir muestras asignadas, consecuencias y archivos corruptos. El emisor no limpia sus defectos antes de enviarlos.
- [ ] T058 [US3] Crear `tools/pas600_simulator/examples/anomalies-100.json` y casos CSV/JSON de0/100%, inferior/superior y archivo corrupto en `tools/pas600_simulator/tests/fixtures/anomalies/README.md`, con oráculos de conteo/posición y banda0..10kWh/15min; cien intervalos más referencia acumulada extra, otras categorías sin anomalías. Documentar posibilidad legítima de que001 acepte un outlier positivo al no definir esa banda física.
- [ ] T059 [US3] Ejecutar pruebas US3 y recepción local real de archivos corruptos junto a archivos válidos independientes, usando suites de US2 y ejemplos; registrar en `specs/003-simulador-pas600-sftp/validation/us3.md` cantidades/posiciones exactas, tipos/fechas, límites/alcance, semilla y hashes. Distinguir transferencia exitosa, file_unreadable, diagnóstico nativo y rechazo/aceptación002; comprobar ausencia/cobertura y cero/ausencia sin revelar el oráculo al receptor.

## Phase 6: User Story 4 — Repetir y evaluar una prueba de limpieza (P2)

**Objetivo**: Completar informe/control, exportar evidencia durable y comparar resultados; conservar estado ante parada/reanudación y permitir reproducción por otra persona.

**Prueba independiente / checkpoint**: Dos ejecuciones iguales reproducen100% de valores/instantes/defectos; informe+exportación+consumo permiten localizar todas las diferencias, separando entrega y aceptación. Una señal detiene nuevos ciclos y conserva estado; otra persona reproduce usando configuración saneada/documentación.

- [ ] T060 [P] [US4] Escribir pruebas de reproducibilidad integral en `tools/pas600_simulator/tests/contract/test_reproducibility.py`: dos ejecuciones/configuración/semilla/período iguales con anomalías reproducen valores/tiempos simulados/omisiones/posiciones y bytes del mismo formato; CSV/JSON conservan igualdad lógica, UUID/tiempos reales identificados aparte. Cubrir hashes lógicos/completos y repetición después de reordenar serialización.
- [ ] T061 [P] [US4] Escribir pruebas del informe/contraste en `tools/pas600_simulator/tests/unit/test_compare.py` y `tools/pas600_simulator/tests/contract/test_evaluation_cli.py`: aceptado/rechazado/duplicado/too_early, omisiones y pares vecinos, manifiesto ajeno/ausente/incompleto, fuente no disponible y banda del escenario no aplicada por001; hashes originales inmutables y códigos0/5/6. Deben fallar antes de T065/T066/T068. Contrastar consumption_snapshot/selection/snapshot_id/cutoff_at: unavailable o alcance insuficiente produce partial/not_evaluable y código5 si no hay diferencias demostradas, nunca código0; código6 conserva diferencias junto a limitaciones. Tres intervalos de15min implican2700s/75% y deben detectar cobertura real falsamente completa.
- [ ] T062 [P] [US4] Escribir pruebas de SIGINT/SIGTERM/reanudación en `tools/pas600_simulator/tests/contract/test_stop_resume.py`: señal durante espera/escritura/tras CLOSE antes de EOF, ningún nuevo ciclo, finalizar transferencia bajo timeout o abortar sin sello, salida130, journal persistente/reenvío íntegro y espera900 al reanudar. Deben fallar antes de T067.
- [ ] T063 [P] [US4] Escribir contrato de exportación autorizada/captura consistente en `backend/tests/contract/acquisition/test_evidence_export.py`: manifiesto/fechas/lecturas/pares/adaptación/resultados002/cobertura referenciada al mismo corte, rechazo de proceso o edificio no autorizado, permisos no derivados de Programador, ausencia de secretos/excepciones y diagnóstico de resultado desconocido. Deben fallar antes de T064. Exigir selección explícita de categorías/período/zona/vista y snapshot_id/cutoff_at; resultados reales de consumo y recepción deben compartir UoW REPEATABLE READ, no solo una fecha igual. Probar available con no_data, unavailable con causa/listas vacías y pérdida de capturaDB sin reemplazar exportación válida.
- [ ] T064 [US4] Implementar `Acquisition.export_results` en `backend/src/ecs_ec/acquisition/evidence.py` y `export-results --publication-ref --start --end --timezone --categories --view --output` en `backend/src/ecs_ec/acquisition/cli.py`, con DTOs en `backend/src/ecs_ec/acquisition/schemas.py`: proceso de mantenimiento autorizado con edificio del binding y filtros validados, categorías únicas/view detail|hour|day|month|year, inicio<fin y zona/offsets del edificio. Exportar schema_version, snapshot_id/cutoff_at/selection, manifiesto/sellado/posiciones/pares/causas e historial de evaluaciones/resultados002 al corte, junto con consumption_snapshot real001/002 mediante la misma UoW REPEATABLE READ. Reutilizar contratos de detalle/agregados y liberar UoW antes de escribir; Decimal como cadenas, sin secretos ni oráculo. Available no implica cobertura completa; unavailable exige causa y listas vacías, nunca cero inventado. Si fallaDB/pierde captura, fallar sin sustituir evidencia válida ni inventar coherencia; sin endpoint público ni autorización humana propia.
- [ ] T065 [US4] Completar `report`/ControlReport en `tools/pas600_simulator/src/pas600_simulator/report.py`: configuración saneada/perfil/semilla/datos lógicos anteriores a alteración, asignaciones por muestra/archivo y consecuencias, identidades/correlaciones y journal/estados de transferencia; nunca afirmar aceptación sin evidencia real. Conservar informes locales hasta retiro explícito, sin copiar secretos, valores del entorno, rutas sensibles de claves ni transport file.
- [ ] T066 [US4] Implementar contraste offline en `tools/pas600_simulator/src/pas600_simulator/compare.py` usando el esquema de exportación definido en [contrato SFTP](contracts/sftp-reception.md) y fijado en T064: validar snapshot_id/cutoff_at/selection, enlazar manifiesto/hash/nombre/posición y extremos de delta, y contrastar omisiones contra consumption_snapshot real. Informar selección, diferencias y limitaciones con comparison_status complete|partial|not_evaluable; no considerar evaluados intervalos fuera de alcance, bloques excluidos o evidencia retirada/insuficiente. Código0 solo con comparación completa sin diferencias, código6 con diferencias observadas y código5 si falta evidencia para concluir sin diferencias demostradas; cobertura unavailable no da éxito global vacío. No asumir rechazo de toda anomalía, mutar originales ni enviar oráculo al backend; conservar criterio aplicado y resultados por intento.
- [ ] T067 [US4] Completar parada cooperativa/reanudación en `tools/pas600_simulator/src/pas600_simulator/cli.py`, `tools/pas600_simulator/src/pas600_simulator/transport.py` y `tools/pas600_simulator/src/pas600_simulator/journal.py`: señales impiden nuevo ciclo, finalizar actual bajo timeout o abortar sin EOF limpio, persistir estado/resultados y código130; conservar espera900, lock/ordinales y publicación completa al reanudar. Una caída abrupta recupera desde hechos confirmados, sin presumir transferencia por un intento iniciado.
- [ ] T068 [US4] Integrar `report --run --output` y `compare --run --reception --output` en `tools/pas600_simulator/src/pas600_simulator/cli.py`: solo lectura de originales, diagnóstico stderr saneado, códigos0 comparación completa sin diferencias/5 evidencia ilegible o insuficiente/6 diferencias observadas, aun con limitaciones declaradas y salida JSON versionada; documentar que6 puede señalar un hallazgo legítimo de limpieza. Reejecutar pruebas de comandos anteriores para conservar contrato CLI completo.
- [ ] T069 [US4] Completar instrucciones de configuración/repetición/contraste en `tools/pas600_simulator/README.md` y `specs/003-simulador-pas600-sftp/quickstart.md`, con comandos implementados, ejemplos sin secretos, perfil/procedencia/mapping, errores/códigos y separación tiempo real/simulado. Incluir exportación autorizada y comparación con GET de consumo protegido006, sin presentar acceso técnico007 como permiso funcional ni requerir hardware/VPS para la prueba local. Documentar parámetros obligatorios --start/--end/--timezone/--categories/--view del exportador, snapshot de cobertura y códigos5/6 ante comparación parcial; incluir prueba de instalación/validación/generación --no-dev y separación project.dependencies/dependency-groups.dev.
- [ ] T070 [US4] Ejecutar T060/T061/T062/T063 y prueba reproducida por otra persona según quickstart; registrar en `specs/003-simulador-pas600-sftp/validation/us4.md` todas las diferencias conocidas con manifiesto/pares/resultados002/detalle-cobertura001/002,100% igualdad lógica y parada/reanudación. Conservar archivos originales y estados; si falta evaluación humana o proveedor real, dejar ese resultado pendiente explícitamente y no declarar SC-003/SC-005 aceptados. Registrar snapshot_id/cutoff_at/selection y casos2700s/75%, cobertura unavailable y pérdida de captura, verificando que el contraste parcial no devuelve éxito global; distinguir resultados históricos de intentos recuperados y reenvíos nuevos.

## Phase 7: Polish — operación, documentación y aceptación transversal

**Objetivo**: Completar auditoría/instrumentación propia y verificar todo el alcance con evidencia real y documentación del código.

**Prueba independiente / checkpoint**: No quedan requisitos sin tarea/evidencia; pruebas/documentación coherentes, secretos excluidos, restauración de adquisición comprobada y limitaciones de hardware/VPS explícitas.

- [ ] T071 Conectar `FunctionalAudit`009 en `backend/src/ecs_ec/acquisition/service.py` y `backend/src/ecs_ec/acquisition/store.py`, con pruebas en `backend/tests/integration/acquisition/test_audit.py`: resultado/estado003 y auditoría en misma UoW, actor/correlación internos y cargas saneadas; 002 conserva propiedad de reception.completed/consumption.accepted. Probar falloDB sin falsa durabilidad ni evento de éxito y ausencia de dependencia de008/SMTP; no crear tipos comunes de FunctionalEvent no registrados.
- [ ] T072 Instrumentar adquisición/parseo/deltas/errores/esperas/reintentos/recuperación mediante el emisor real007 en `backend/src/ecs_ec/acquisition/lifecycle.py` y `backend/src/ecs_ec/acquisition/service.py`; documentar señales en `deploy/README.md` y verificar fallo del destino sin revertir commits ni bloquear consumo. Consumir su capacidad cuando exista; si falta registrar dependencia pendiente en validation/prerequisites.md, sin implementar observabilidad007 ni usar logs como evidencia funcional.
- [ ] T073 Ampliar procedimientos del propietario009 para volumen/metadatos de adquisición en `deploy/README.md` y ejecutar restauración local aislada registrándola en `specs/003-simulador-pas600-sftp/validation/restore.md`: recuperar manifiestos/bytes/resultados/pares protegidos, detectar archivo faltante y conservar sesiones abortadas/pendientes con cuotas. No reescribir backup/restore común en003, ni purgar originales o completar lotes por heurística.
- [ ] T074 Revisar documentación de cada archivo/función/método/clase/componente propio en `tools/pas600_simulator/src/pas600_simulator/` y `backend/src/ecs_ec/acquisition/`, junto a pruebas/migración; registrar resultado en `specs/003-simulador-pas600-sftp/validation/documentation.md`. Cubrir propósito/entradas/salidas/errores/efectos, fórmulas/conversiones/calendario/supuestos y procedencia/regeneración de cualquier código generado, conforme a constituciónIII; corregir documentación en el mismo cambio de comportamiento.
- [ ] T075 Verificar redacción de secretos/aislamiento y límites del despliegue en `backend/tests/integration/acquisition/test_isolation.py` y `specs/003-simulador-pas600-sftp/validation/deployment.md`: password/clave/known_hosts, host key persistida, bindings/edificios/directorios aislados, sin shell/forwarding y sin derechos humanos derivados. Documentar destino VPS configurable y gate para hardware: IDs/topología reales y captura que demuestre la convención de sesión antes de habilitar; no exigir hardware para aceptación local ni certificarlo desde ejemplos sintéticos.
- [ ] T076 Ejecutar suites aplicables y todos los escenarios de `specs/003-simulador-pas600-sftp/quickstart.md` con locks/versiones/referencias fijas, incluidos real_time y consumidores reales, y consolidar `specs/003-simulador-pas600-sftp/validation/acceptance.md` con FR-001..FR-022 y SC-001..SC-006, comandos/fechas/evidencias/resultados y limitaciones. Comprobar todo dato/estado del informe contra origen y evitar regresiones US1–US4; mantener tareas/resultados no ejecutados pendientes, sin marcar revisión o aceptación solo por existencia de archivos.

## Dependencias y orden de ejecución

La fase2 bloquea todas las historias hasta completar sus contratos locales. Dentro de
cada fase, seguir el orden de las tareas salvo grupos `[P]` indicados abajo. Las pruebas
se preparan antes del comportamiento al que apuntan; contratos/modelos preceden servicios,
y estos preceden integración/aceptación. Las tareas de aceptación no autorizan cerrar un
criterio si el resultado real falta.

| Fase / historia | Requisitos para comenzar / completar |
| --- | --- |
| Phase 1: Setup (T001–T003) | Sin capacidad de aplicación ajena; usar documentos y herramientas locales. |
| Phase 2: Foundational (T004–T007) | Completar Setup; sus utilidades locales son prerrequisito común de historias. |
| Phase 3: User Story 1 (T008–T021) | Setup + fundaciones; aceptación local sin backend. Su total calculado integrado se valida en US2. |
| Phase 4: User Story 2 (T022–T048) | Fundaciones + generador normal US1; backend requiere proveedores reales009/001/002. Aceptación incluye transporte/cadencia reales. |
| Phase 5: User Story 3 (T049–T059) | Fundaciones + generación US1. Núcleo local independiente de US2; aceptación de recepción defectuosa requiere US2. |
| Phase 6: User Story 4 (T060–T070) | Control base US1, transporte/recepción US2 y anomalías US3; exportación/contraste usan resultados durables y sesión006 al comprobar vistas. |
| Phase 7: Polish (T071–T076) | Setup antes de fundaciones; cierre transversal después de todas las historias. |

Grafo de dependencias de finalización (las flechas no implican dependencia de aceptación
completa entre specs externas):

```text
Setup → Fundaciones → US1 (MVP local)
                        ├→ US2 + plataforma009/consumo001-002 reales
                        └→ US3 (generación de anomalías)
US2 + US3 → aceptación integrada US3
US1 + US2 + US3 → US4 → Cierre transversal
006 → contraste web protegido; 007 → instrumentación propia
```

US2 y US3 permiten trabajo parcial concurrente después de US1, sujeto a archivos distintos
y contratos fijados. La prueba de recepción de US3 espera US2. No se requiere integrar008,
SMTP, costos o PDF. No convertir pruebas históricas por puerto interno en evidencia SFTP.

## Oportunidades de ejecución paralela

Hay **23 tareas `[P]`**, condicionadas por sus prerrequisitos. Los ejemplos son grupos de trabajo posibles, no instrucciones para lanzar agentes
ni permiso para editar archivos compartidos simultáneamente.

### Preparación

Tras revisar alcance/documentos, T003 puede prepararse mientras se instala el paquete en T002: fixtures y manifiesto del paquete son archivos distintos.

### US1

Después de fundaciones y referencias, T008, T009, T010 y T011 pueden escribirse a la vez en archivos de prueba distintos. Tras T012/T013, T014 y T015 pueden implementarse en paralelo; T016 espera ambos. Tras el CLI estable, T019 y T020 usan archivos distintos.

### US2

Después de T022/T023 y contratos fijados, T024, T025, T026, T027 y T028 preparan suites diferentes. Con esquemas/fixtures estables, T037 y T038 pueden implementarse a la vez; mapping/counters/service esperan sus resultados. Models, migración, store, CLI, locks y Compose siguen secuenciales.

### US3

Después de US1, T049, T050 y T051 pueden prepararse en paralelo. La implementación T052→T053→T054→T055→T056 es secuencial porque comparte anomalies.py; T057 espera todas.

### US4

Después de US2/US3 y esquema de exportación acordado, T060, T061, T062 y T063 pueden escribirse en paralelo. Reporte/CLI/señales se integran secuencialmente por archivos compartidos; no ejecutar publish/resume simultáneamente para una misma identidad de destino/publicador.

## Trazabilidad de requisitos y criterios

Cada fila nombra tareas concretas de esta spec. No acredita que se hayan implementado.
Los criterios se evalúan con todos sus escenarios, no solo por un archivo presente.

| Requisito | Tareas principales | Criterios / alcance |
| --- | --- | --- |
| FR-001 | T002, T018, T044 | SC-006; fuente externa opcional y monolito sin depender de ella. |
| FR-002 | T005, T019, T020, T047 | SC-001; categorías/subconjuntos, parámetros/identidades y defaults. |
| FR-003 | T003, T014, T015, T016 | SC-001; perfil/nombres/estructura nativos sin marcas ECS-EC. |
| FR-004 | T008, T009, T010, T021 | SC-001; conformidad independiente y equivalencia CSV/JSON. |
| FR-005 | T012, T013, T039, T048 | SC-001; medidor/publicador y CAT-01 medida/calculada. |
| FR-006 | T010, T013, T026, T040 | SC-001; delta100/104 y sin puente de huecos. |
| FR-007 | T034, T036, T041, T047 | SC-004; destino/autenticación/identidad local o VPS. |
| FR-008 | T024, T028, T042, T048 | SC-004; >=900s reales desde fin y sin simultaneidad. |
| FR-009 | T025, T027, T035, T043, T048 | SC-004; lote completo, agrupación y reenvío sin doble consumo. |
| FR-010 | T024, T042, T045, T048 | SC-004; tres intentos totales y pendientes conservados. |
| FR-011 | T007, T041, T045, T065 | SC-004/SC-005; estados de archivo/sesión/funcionales distintos. |
| FR-012 | T049, T052, T053 | SC-002; floor exacto, tasas0/100 y posiciones disjuntas. |
| FR-013 | T054, T056, T057, T059 | SC-002; omitir sin cero, tipos/fechas y corrupción por archivo. |
| FR-014 | T006, T050, T055, T058 | SC-002; rango/intervalo/unidad, límite superior/inferior e incrementos. |
| FR-015 | T053, T054, T051, T059 | SC-002; categorías/posiciones/archivos fuera de alcance intactos. |
| FR-016 | T017, T057, T065, T068 | SC-005; oráculo previo y journal de transferencia separados de nativos. |
| FR-017 | T006, T010, T060, T070 | SC-003;100% lógica reproducible, tiempos reales separados. |
| FR-018 | T063, T064, T066, T070 | SC-005; contraste íntegro sin revelar oráculo ni mutar originales. |
| FR-019 | T004, T005, T006, T052, T045 | SC-001/SC-002/SC-004; configuración válida antes de efectos. |
| FR-020 | T020, T021, T062, T067, T070 | SC-006/SC-004; doce meses local y parada conservando estado. |
| FR-021 | T026, T039, T040, T043, T033, T059 | SC-001/SC-004/SC-005; contratos001/002, ilegible≠transporte≠rechazo. |
| FR-022 | T019, T069, T074, T075 | SC-005; reproducción/documentación y datos/informes sin credenciales. |

### Trazabilidad inversa de tareas

Las filas anteriores agrupan las tareas principales por requisito y criterio. Esta tabla
explicita las tareas habilitadoras o transversales que no aparecían en esas filas, para que
cada tarea tenga una relación visible con una historia, capacidad o regla del proyecto.
Las tareas pueden aparecer en ambas tablas cuando tienen una función habilitadora y otra
de aceptación; todas continúan pendientes.

| Tarea | Historia / capacidad relacionada | Relación con el alcance |
| --- | --- | --- |
| T001 | Fundacional; dependencias 009/001/002/006/007 | Registra prerrequisitos por capacidad y delimita la integración de US2/US4. |
| T011 | US1; FR-019 | Comprueba que validate/generate rechacen configuración inválida antes de producir efectos. |
| T022 | US2; integración 009/001/002 | Verifica los contratos reales requeridos para recepción, recuperación y exportación; no implementa capacidades de otros propietarios. |
| T023 | US2; integración del paquete con plataforma 009 | Prepara el módulo acquisition y su entorno de integración dentro del monolito existente. |
| T029 | US2; FR-009/FR-021 | Modela binding, sesión SFTP y archivos recibidos que sustentan la recepción nativa. |
| T030 | US2; FR-009/FR-021 | Modela publicaciones y evaluaciones recuperables con identidad e entrada de recepción fijadas. |
| T031 | US2; FR-005/FR-006/FR-021 | Modela lecturas, candidatos y resultados de adaptación con origen y evidencia. |
| T032 | US2; persistencia de FR-009/FR-021 | Persiste los modelos de adquisición con sus restricciones y referencias protegidas. |
| T037 | US2; FR-003/FR-004/FR-021 | Lee y valida el formato CSV nativo con procedencia y errores trazables. |
| T038 | US2; FR-003/FR-004/FR-021 | Lee y valida el formato JSON nativo con calidad y errores trazables. |
| T046 | US2; FR-007/FR-009 | Configura el listener y el almacenamiento de recepción en el despliegue común. |
| T061 | US4; FR-018/SC-005 | Define pruebas del informe y el contraste contra la evidencia de recepción. |
| T071 | Cierre transversal; auditoría 009 y FR-011 | Registra los resultados de adquisición con la auditoría común, sin apropiarse de eventos de 002. |
| T072 | Cierre transversal; instrumentación 007 | Emite señales técnicas de adquisición mediante el proveedor común cuando esté disponible. |
| T073 | Cierre transversal; respaldo 009 y SC-006 | Verifica recuperación de evidencia persistente usando los procedimientos del propietario de plataforma. |

| Criterio | Evidencia de aceptación requerida |
| --- | --- |
| SC-001 | T021 y T048:100% de archivos normales conformes e igualdad CSV/JSON/origen; CAT-01 integrada según001. |
| SC-002 | T059:100% de conteos/posiciones exactos, extremos0/100, corrupción separada y alcance intacto. |
| SC-003 | T060 y T070:100% igualdad de valores/instantes/omisiones/alteraciones con misma configuración/semilla/período. |
| SC-004 | T048, T067 y T070:estados verificables, ningún parcial procesado/duplicado de consumo ni envío antes de900s. |
| SC-005 | T064/T066 y T070:localizar todas las diferencias para cada caso con resultados reales y cobertura, sin mutar originales. |
| SC-006 | T020/T021 y T076:>=12 meses/siete categorías generados localmente; preparar agrupaciones/retención002 sin afirmar tiempo de conservación transcurrido. |

## Estrategia de implementación

1. **MVP local**: completar Setup + Fundaciones + US1, ejecutar sus pruebas independientes
   y documentar resultados. Entrega generación normal CSV/JSON e histórico sin red;
   no acredita todavía recepción SFTP ni la aceptación integrada de toda spec-003.
2. **Camino de recepción real**: incorporar US2 sobre proveedores009/001/002 disponibles,
   verificar cierre/CLOSE/EOF, deduplicación, recuperación y cadencia real. Sesión006 se
   requiere al comprobar vistas de consumo, no para autenticar cada entrega automática.
3. **Limpieza medible**: añadir US3 manteniendo el oráculo previo y cantidades exactas;
   puede desarrollarse su núcleo local junto a subtrabajos de US2 sin compartir archivos.
4. **Repetición y evaluación**: completar US4 con informe/exportación/contraste, parada
   y reproducción por otra persona, después de tener recepción y anomalías reales.
5. **Cierre**: auditoría/instrumentación propias, restauración, documentación y matriz
   completa de aceptación. No ejecutar despliegue ni marcar aceptación con este documento.

Las pruebas largas pueden seleccionarse aparte, pero son necesarias para acreditar
SC-004 con red real. La generación rápida de un año no permite acelerar publicaciones.
El gate del PAS600 físico sigue en la documentación de despliegue: el contrato de sesión
es convención003, no una capacidad del firmware ya probada. Los ejemplos sintéticos no
certifican IDs de instalación ni capturas; la aceptación local especificada no exige VPS
ni hardware. No añadir esas dependencias a la generación local.

## Resumen y control de formato

**Total**: 76 tareas pendientes en siete fases; 23 con `[P]`.

| Bloque | Cantidad | Rango |
| --- | --- | --- |
| Phase 1: Setup | 3 | T001–T003 |
| Phase 2: Foundational | 4 | T004–T007 |
| Phase 3: User Story 1 | 14 | T008–T021 |
| Phase 4: User Story 2 | 27 | T022–T048 |
| Phase 5: User Story 3 | 11 | T049–T059 |
| Phase 6: User Story 4 | 11 | T060–T070 |
| Phase 7: Polish | 6 | T071–T076 |

Todas las tareas usan checkbox pendiente, ID secuencial y rutas concretas; solo las
fases de historia llevan etiqueta US1–US4. Ninguna casilla representa trabajo hecho.
La ausencia de `.specify/extensions.yml` implica que no hay hooks before_tasks/after_tasks
registrados al generar este archivo; comprobar nuevamente si se añaden extensiones.
