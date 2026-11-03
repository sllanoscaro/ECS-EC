---
description: "Tareas integrales de observabilidad externa; conserva el traslado de spec-008"
---

# Tasks: Observabilidad técnica externa y rol Programador

## Contexto compartido del proyecto (ECS-EC)

**Generado**: 2026-11-02. **Estado**: implementación parcial;26/65 tareas con evidencia.
[Emisor](validation/emitter.md) y [acceso](validation/access.md) documentan resultados.
T022 espera PDF005 real; T028/T029 tienen código/guías preparados pero conservan su
cadena de prerrequisitos pendiente. T030 no acredita matriz completa. No hay aceptación
integral ni cierre deT065. La generación original sustituyó el borrador parcial de cinco tareas.

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [quickstart.md](quickstart.md),
[emisión/cobertura](contracts/integrations.md), [señales](contracts/signals.md),
[acceso/políticas](contracts/technical-access.md) y [esquema de log](contracts/log-event.schema.json).
**Prerrequisitos de diseño**: artefactos leídos; revisar consistencia con `$speckit-analyze`
antes de implementar. Aplican [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md), [AGENTS.md](../../AGENTS.md) y
[constitución1.0.0](../../.specify/memory/constitution.md).

**Tests**: incluidos porque la especificación exige pruebas de permisos, carga conocida,
reintentos, límites, privacidad, retención y funcionamiento local (SC-001–009), y el traslado
conserva pruebas previas a capacidades nuevas. Escribirlas antes de implementar el
comportamiento correspondiente, comprobar fallos pertinentes y ejecutarlas para aceptación.
No confundir generar un archivo de prueba con ejecutar y aprobar su escenario.

**Formato**: `- [ ] TNNN [P?] [USn?] Descripción con ruta`. IDs locales a007;
`[P]` solo con prerrequisitos satisfechos y archivos distintos. Rutas de código relativas
a raíz, enlaces Markdown relativos a este archivo. No hay migraciones/tablas/visores
funcionales nuevos de007. Las rutas futuras no prueban implementación existente.

**Documentación en cada tarea**: propósito por módulo y contrato de cada función/clase/
componente/script/prueba propios (entradas, salidas, errores y efectos); fórmulas,
supuestos, unidades y decisiones junto al código. Actualizar procedimiento en el mismo
cambio; el chequeo final no difiere esta obligación.

## Phase 1: Setup — preparar solo observabilidad

**Propósito**: comprobar capacidades externas y preparar el módulo007 en el scaffold de009.
No crear plataforma, identidad, consumo, costos o PDF para satisfacer estos prerrequisitos.
T003/T004 pueden desarrollarse juntos después de T001/T002; escribir fixtures no acredita
la existencia ni la instrumentación de productores reales.

- [X] T001 Verificar scaffold, configuración/reloj/lifespan de009 y disponibilidad por capacidad de001–006 conforme a la matriz de dependencias inferior; registrar estado real, documentos/rutas propietarias y bloqueos en `specs/007-observabilidad-externa/validation/prerequisites.md`. La base009 bloquea implementación del emisor; las capacidades de negocio solo bloquean sus verificaciones de aceptación, nunca se implementan desde este setup.
- [X] T002 Añadir únicamente dependencias007 al `pyproject.toml` y `uv.lock` existentes, mantener CPython3.14 `>=3.14,<3.15`/FastAPI0.162.0 de009, resolver Loguru/OTel/OTLP/HTTPX/jsonschema y fijar versiones/digests de Nginx/Alloy/Loki/Grafana/Jaeger2.22.0 en `deploy/observability/versions.env`; comprobar `uv sync --locked` y registrar resultados, sin recrear manifiestos ni afirmar compatibilidad no ejecutada. Prerrequisitos de007: T001.
- [X] T003 [P] Preparar fixtures sintéticas de reloj, eventos, referencias, transporte y stack con proyectos/volúmenes exclusivos de prueba en `backend/tests/integration/observability/conftest.py` y `backend/tests/unit/observability/conftest.py`; fixtures de dominio consumen proveedores reales cuando existan, sin SQLite, endpoints públicos de inyección ni sustitutos acreditados como negocio real. Prerrequisitos de007: T001, T002.
- [X] T004 [P] Crear `scripts/observability/prepare_local.sh` para preparar CA/TLS y certificados mTLS de aplicación, Alloy y salud por entorno, rutas privadas externas al repo y configuración reproducible; verificar permisos, separación local/test y reutilización segura de recursos, sin importar credenciales006 ni escribir secretos en Git/stdout. Documentar contrato del script y comandos en `scripts/observability/README.md`. Prerrequisitos de007: T001, T002.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 2: Foundational — emisor común y almacenamiento técnico

**Propósito**: entregar el emisor real antes de cualquier historia. Las configuraciones
Alloy/Loki/Jaeger se preparan aquí para que US1 pueda probar las tres señales sin depender
de la instrumentación de negocio de US2. Su integración Compose y gateway ocurre en US1.

**Pruebas primero**: redactar T005–T007 antes de sus implementaciones y demostrar fallos
por comportamiento ausente. Un error de importación o fixture incompleto no acredita el caso.
Todas las funciones, clases, módulos, pruebas y scripts propios documentan propósito,
entradas, salidas, errores y efectos; ese requisito acompaña cada tarea, no se difiere al cierre.

- [X] T005 [P] Escribir pruebas de contrato del sobre y contexto en `backend/tests/contract/observability/test_log_event.py` y `backend/tests/unit/observability/test_context.py`: esquema cerrado, nulls, UTC, límites/NaN, severidad/resultado/código, campos desconocidos, UUID/trace IDs, contexto autodeclarado y aislamiento concurrente; usar `contracts/log-event.schema.json` y casos conocidos, no una copia de la implementación. Prerrequisitos de007: T003.
- [X] T006 [P] Escribir pruebas unitarias de admisión no bloqueante, saturación, límite serializado, spool rotativo, secuencias y redacción previa a cualquier sink en `backend/tests/unit/observability/test_logging.py` y `backend/tests/unit/observability/test_sanitization.py`; demostrar que fallar logger/disco no cambia resultado del llamador. Prerrequisitos de007: T003.
- [X] T007 [P] Escribir pruebas de OTel, salud y lifecycle en `backend/tests/unit/observability/test_tracing.py`, `backend/tests/unit/observability/test_health.py` y `backend/tests/unit/observability/test_lifecycle.py`: límites activos/pendientes, deadline real del exportador, heartbeat15/45s, ausencia distinta de cero, cierre5s y configuración técnica inválida sin impedir arranque funcional. Probar estados/últimos éxitos independientes de logs y trazas, contadores OTLP por lote sin multiplicar por reintento, ausencia de actividad sin fallo inventado y available con evidencia no null. Prerrequisitos de007: T003.
- [X] T008 Implementar catálogo y sobre en `backend/src/ecs_ec/observability/events.py` conforme a `specs/007-observabilidad-externa/contracts/log-event.schema.json`: `schema_version` «`1`»; `event_id`/`boot_id` «UUID del evento/arranque; evento serializado inmutable»; `sequence` «Positivo creciente por arranque, asignado antes de admisión; descarte deja hueco»; `timestamp` «RFC3339 UTC con `Z`, instante técnico original, no período medido»; configuración `environment`/`service_version`/`policy_revision` «Configuración validada y acotada»; `event`/`operation`/`stage` «Catálogos cerrados; nunca texto libre de fuente» y `source_module` «Módulo productor del catálogo; permite distinguir cambios administrativos sin revelar entidad/actor». Conservar enums exactos del esquema, entornos `local|test|vps`, timestamp<=40 caracteres y versión/revisión de1–128 caracteres. Prerrequisitos de007: T005.
- [X] T009 Completar validación de payload en `backend/src/ecs_ec/observability/events.py`: `severity` «`DEBUG`, `INFO`, `WARNING`, `ERROR`»; `outcome` «`success`, `expected_rejection`, `unexpected_error`, `in_progress`, `not_applicable`»; `code` «Código seguro registrado; desconocido → `unclassified`, sin original»; referencias «Contexto anterior, null explícito si no disponible»; `duration_ms` «Número finito >=0 por reloj monotónico, o null si no observable»; `counts` «Enteros tipados >=0 de archivos/registros; sin lecturas, importes ni IDs libres»; `health` «Solo heartbeat/control: contadores acumulados, profundidades y último envío». Aplicar «Máximo 16 KiB UTF-8 serializados.» y «`additionalProperties: false`»; terminal exige resultado final, fallo exige código/ERROR, heartbeat exige salud; JSON estricto sin NaN/Infinity y sin mapas libres. Validar los seis campos obligatorios de salud por señal del esquema, fechas de éxito nullable y condición available→último éxito no null; mantener denominadores y contadores de transporte separados de resultados de negocio. Prerrequisitos de007: T008.
- [X] T010 Implementar `backend/src/ecs_ec/observability/context.py` con `contextvars`: `environment`/`service_version` «Configuración confiable; nunca entrada del cliente.»; `operation_ref` «UUID opaco interno de operación lógica; null solo sin contexto confiable disponible.»; `attempt_ref` «UUID de intento lógico; nuevo en reenvío explícito, el mismo en recuperación.»; `execution_ref` «UUID nuevo por ejecución/reconciliación.»; `publication_ref` «UUID técnico ligado a publicación003; no nombres, hashes de contenido o descriptores nativos.»; `parent_operation_ref` «Relación explícita al iniciar otra operación, nunca coincidencia de texto.»; `trace_id`/`span_id` «Hexadecimal OTel de 32/16 caracteres no nulos, generado por instrumentación confiable.» y `context_status` «`available`, `unavailable` o `recovered`; sin padre inventado.». Reutilizar UUID confiables o HMAC-SHA256 por entorno/versionado de claves semánticas; no guardar entradas/clave ni adoptar traceparent/baggage/X-Request-ID públicos. Prerrequisitos de007: T009.
- [X] T011 Implementar allowlist previa a Loguru/SDK/colas en `backend/src/ecs_ec/observability/sanitization.py`: excluir contraseñas, sesiones, claves, emails/IP, cuerpos, CSV/boletas/PDF, valores energéticos/financieros, URL/query, SQL, objetos y excepciones crudas; convertir solo códigos registrados a texto técnico, rechazar estructura libre y contabilizar `schema_rejected` sin exponer el valor original. Prerrequisitos de007: T009, T006.
- [X] T012 Implementar `backend/src/ecs_ec/observability/logging.py` con sink de sobre saneado, `diagnose=False`/`backtrace=False`, handlers por defecto retirados y sin serializar record/extra completos: cola de1024 eventos (1023 datos+1 control reemplazable), cada uno<=16KiB, put sin espera de red/disco y descarte nuevo contabilizado; worker con8 archivos de16MiB, <=128MiB/TTL de política y secuencias/timestamp/cuerpo inmutables al releer. No usar `enqueue=True` como prueba de capacidad ni registrar recursivamente fallos del logger. Prerrequisitos de007: T010, T011, T006.
- [X] T013 Implementar `backend/src/ecs_ec/observability/tracing.py`: «Allowlist equivalente al sobre; <=32 atributos con cadenas <=128 caracteres, <=16 KiB por span exportable.» y «Máximo 256 spans activos y 2048 pendientes; exceso descartado/contabilizado sin espera.»; lotes<=512, `OTLPSpanExporter(timeout=5)` con presupuesto total5s incluidos hasta3 intentos y pérdidas observables, sin flush por request. Aplicar éxito `OK`, rechazo esperado `UNSET` y fallo inesperado `ERROR`/código seguro, sin captura automática de excepción/stack; spans hijos no cuentan operaciones. Observar resultado de cada lote para actualizar trace_export_status/last_trace_export_success, trace_exported_spans_total una vez por span confirmado y trace_export_failures_total una vez por lote finalmente fallido; los reintentos no multiplican contadores ni una confirmación OTLP prueba persistencia consultable. Prerrequisitos de007: T010, T011, T007.
- [X] T014 Implementar heartbeat/control en `backend/src/ecs_ec/observability/health.py`: cada15s, contadores>=0 de pérdidas/validación/colas/spool y profundidades<=1024/2048; leer solo contadores Alloy permitidos vía credencial de salud y observar el exportador OTLP local con timeout acotado. Incluir los seis campos obligatorios cuando health es objeto: `log_collector_status` «`available`, `degraded` o `unknown`; solo recolección de logs»; `last_log_collector_success` «RFC3339 UTC con `Z`, <=40 caracteres o null si no existe éxito observado»; `trace_export_status` «`available`, `degraded` o `unknown`; solo exportación OTLP»; `last_trace_export_success` «RFC3339 UTC con `Z`, <=40 caracteres o null si no existe éxito observado»; `trace_export_failures_total` «Entero acumulado >=0 por arranque; un lote terminado sin éxito cuenta una vez» y `trace_exported_spans_total` «Entero acumulado >=0 por arranque; spans de lotes confirmados sin multiplicar por reintento». Available exige último éxito no null; sin evidencia usar unknown, fallo observado degraded y fecha anterior si existe. >45s sin heartbeat implica desconocimiento, pero no exigir lotes sin actividad ni inferir trazas sanas por Alloy; no ampliar permisos de consulta de identidades automáticas. Prerrequisitos de007: T012, T013, T007.
- [X] T015 Implementar configuración/política tipada y `Telemetry.begin/stage/complete/continue/health/shutdown` en `backend/src/ecs_ec/observability/lifecycle.py` y `backend/src/ecs_ec/observability/__init__.py`; registrar extensión en `backend/src/ecs_ec/main.py` existente de009, con reloj común UTC/monotónico, revisión visible, `policy.changed`, config inválida→emisión deshabilitada y diagnóstico seguro, arranque funcional permitido y apagado total<=5s con pérdidas residuales; sin tablas/migraciones, locks de dominio ni dependencia de receptores. Prerrequisitos de007: T014, T007.
- [X] T016 [P] Crear `deploy/observability/alloy.alloy` con lectura solo del spool saneado y posiciones en volumen `--storage.path` persistente; preservar timestamp/línea, quitar `filename`, rutas/container/IDs, mantener solo etiquetas del catálogo, push mTLS, timeout5s y hasta3 reintentos, contadores de descartes/último envío. No equiparar healthy a entrega ni depender de WAL experimental. Prerrequisitos de007: T002, T004, T009.
- [X] T017 [P] Crear `deploy/observability/loki.yaml` con TSDB filesystem, índice24h, compactor único, marcadores/delete_request_store persistentes y retención habilitada168h o24h desechable; configurar ingesta/consultas acotadas, sin listener público ni acceso a volúmenes funcionales; no prometer borrado instantáneo ni aplicar TTL nuevo retroactivamente sin verificación. Prerrequisitos de007: T002, T004, T009.
- [X] T018 [P] Crear `deploy/observability/jaeger.yaml` para Jaeger2.22.0/Badger de instancia única, `ephemeral=false`, keys/values persistentes y `ttl.spans=168h` o24h desechable; OTLP/HTTP y query privados, sin habilitar APIs de escritura adicionales o Badger compartido entre procesos. Prerrequisitos de007: T002, T004, T009.
- [X] T019 Ejecutar pruebas unitarias y de contrato fundamentales con `uv run pytest backend/tests/unit/observability backend/tests/contract/observability`; comprobar admisión/cierre con sinks/receptores indisponibles y registrar resultados/versiones/límites reales en `specs/007-observabilidad-externa/validation/emitter.md`. Las configuraciones técnicas aún no acreditan transporte integrado ni productores reales. Prerrequisitos de007: T015, T016, T017, T018.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 3: User Story 1 — Acceder a la observabilidad como Programador (P1) — MVP

**Objetivo**: acceso web técnico de lectura por entorno, revocación en la siguiente
solicitud y separación de perfiles funcionales, personas e identidades automáticas.

**Prueba independiente**: emitir fixtures técnicas con el emisor real y consultar las tres
señales como Programador. Probar toda la matriz, URL/puertos directos, cabeceras manipuladas,
revocación keep-alive y entorno no autorizado. Los casos funcionales de matriz requieren
identidad006 y las interfaces reales de consumo/costos/PDF; si faltan, quedan pendientes.
US1 no espera la cobertura de incidentes/producciones de US2 ni el catálogo completo de US3.

**Pruebas primero**: los cuatro archivos de pruebas siguientes se redactan juntos tras
el checkpoint fundamental; luego se implementa acceso. Un fixture no concede aceptación
de permisos funcionales que todavía no estén implementados.

- [X] T020 [P] [US1] Escribir `backend/tests/contract/observability/test_technical_access.py` para el contrato humano/automático: allowlist de métodos/rutas, TLS/CA, sin wildcard de administración, proxy arbitrario, tail/Live/SSE, bypass por Host/slashes/cabeceras/cookies; límites30s/10000filas/64KiB/4consultas y denegación sin señales. Prerrequisitos de007: T019.
- [X] T021 [P] [US1] Escribir `backend/tests/integration/observability/test_programmer_provisioning.py`: sujetos opacos por entorno, bcrypt/crypt de imagen fijada, contraseña por TTY, transiciones de habilitación/revocación, sustitución atómica en directorio montado y fallo de archivo que deniega, sin caché ni secretos en argumentos/stdout/Git. Prerrequisitos de007: T019.
- [ ] T022 [P] [US1] Escribir `backend/tests/integration/observability/test_technical_access.py` para el100% de matriz SC-001: Programador local/otro entorno, Operador/Admin006/sin autorización, declaraciones de rol, URL/puertos privados, credenciales humanas/mTLS cruzadas, siguiente petición tras revocación con keep-alive/cookies y recolección sin sesión humana. Usar identidad006 real y comprobar permisos funcionales/historial sin modificar su catálogo. Prerrequisitos de007: T019.
- [X] T023 [P] [US1] Escribir `frontend/tests/e2e/observability-isolation.spec.ts`: navegación funcional sin visor, historial006 permitido al admin, visor técnico Viewer con tres señales de fixture, edición/administración denegadas y enlaces/solicitudes posteriores a revocación sin entrega. Distinguir casos que requieren interfaces funcionales reales conforme a prerrequisitos. Prerrequisitos de007: T019.
- [X] T024 [US1] Implementar `scripts/observability/manage_programmer.sh` grant/revoke por entorno: registro `technical_subject` opaco/verificador/entorno/estado/revisión externa, sin FK/cookie/perfil006; «ausente → habilitado → revocado; habilitar de nuevo requiere provisión externa explícita.»; contraseña por TTY, bcrypt verificado, permisos restrictivos y rename atómico sobre directorio montado. Registrar solo revisión/resultado seguro; un Programador de lectura no obtiene acceso operativo al host. Prerrequisitos de007: T021.
- [X] T025 [US1] Implementar frontera humana en `deploy/technical-gateway/nginx.conf`: Basic/TLS individual y por entorno en cada petición, sin caché de autorización/respuesta ni fallback a cookie; allowlist de lectura Grafana/Loki/Jaeger UI/v3 exacta para imágenes fijadas, excepción POST `ds/query`, cabeceras de identidad sobrescritas y Authorization/Cookie retiradas a upstream. Denegar admin/ingesta/borrado/streams/proxy arbitrario por defecto; aplicar límites30s/10000filas/64KiB/4consultas en gateway/fuentes y configurar logs mínimos sin secretos, IP o sujetos. Prerrequisitos de007: T020, T024.
- [X] T026 [US1] Añadir listeners internos TLS/mTLS e identidades separadas a `deploy/technical-gateway/nginx.conf`: aplicación solo POST `/v1/traces`, Alloy solo POST `/loki/api/v1/push`, salud solo GET `/collector-health` de transporte; certificados por proceso/entorno, sin permisos humanos, fuentes privadas y sin sesiones humanas requeridas. Prerrequisitos de007: T025, T004.
- [X] T027 [US1] Configurar `deploy/observability/grafana/grafana.ini`, `deploy/observability/grafana/provisioning/datasources/platform.yaml`, `deploy/observability/grafana/provisioning/dashboards/platform.yaml` y dashboard inicial `deploy/observability/grafana/dashboards/platform.json`: AuthProxy solo desde gateway, Viewer, `sync_ttl=0`, `enable_login_token=false`, sin autorregistro público/anonymous/login humano alternativo; fuentes y señales de fixture exclusivamente del entorno y dashboard consultable sin Editor. Prerrequisitos de007: T026, T016, T017, T018.
- [ ] T028 [US1] Integrar perfil opcional `observability` en `compose.yaml` y configuración en `.env.example` existentes de009: imágenes/digests fijados, app/db y servicios `technical-gateway`, `alloy`, `loki`, `grafana`, `jaeger`, redes privadas y volúmenes por entorno, directorio secreto read-only y spool read-only para Alloy; publicar solo loopback3443/local y3444/test, parametrizar VPS/TLS; sin puertos directos ni `app.depends_on`/readiness ligados a telemetría. No reescribir scaffold, DB o migraciones de009. Prerrequisitos de007: T027, T022, T023.
- [ ] T029 [US1] Documentar alta/revocación, dos entornos, CA/mTLS, allowlist/versiones, Grafana Viewer y recuperación que deniega por defecto en `deploy/technical-gateway/README.md` y `deploy/observability/README.md`; enlazar desde `deploy/README.md` de009 después de existir, con procedimientos técnicos separados de006 y comandos locales reproducibles. Prerrequisitos de007: T028.
- [ ] T030 [US1] Ejecutar suites de acceso/provisión y Playwright contra stack local real, `nginx -t` y `docker compose --profile observability config --quiet`; comprobar tres señales, revocación en siguiente request, entornos, puertos privados y matriz funcional real; registrar evidencias/puntos pendientes en `specs/007-observabilidad-externa/validation/access.md`. No declarar SC-001 completo si faltan proveedores funcionales. Prerrequisitos de007: T029.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 4: User Story 2 — Relacionar un incidente mediante logs y trazas (P1)

**Objetivo**: localizar comienzo, etapas, resultado y ejecuciones de una operación real,
incluidos rechazos esperados, continuaciones y reintentos PAS600 sin cambiar formatos.

**Prueba independiente**: operaciones correctas/rechazadas/fallidas de todas las filas del
catálogo, trazas/logs vinculados, recuperación tras reinicio y publicaciones reintentadas.
SC-002/004 requiere productores reales instrumentados de001–006. 007 añade su emisor,
consumo de contratos y verificaciones; cada propietario añade sus llamadas de dominio.
Si faltan esas llamadas, registrar bloqueo externo, sin sustituirlas con negocio local.

**Pruebas primero**: T031–T036 se escriben tras sus prerrequisitos; las verificaciones con
proveedores reales se ejecutan cuando sus capacidades estén disponibles.

- [ ] T031 [P] [US2] Escribir `backend/tests/contract/observability/test_instrumentation.py` para `Telemetry.begin/stage/complete/continue/health/shutdown`, registro de operaciones/etapas, severidad/resultado común y terminal único; diferenciar eventos técnicos del bus FunctionalEvent009 y generaciones admitidas/terminadas de005. Exigir que processing/partial_failure no produzcan reception.completed; una lectura sin procesamiento no crea execution.completed y el fallo de ejecución usa counts=null. Prerrequisitos de007: T019.
- [ ] T032 [P] [US2] Escribir `backend/tests/integration/observability/test_correlation.py` para contexto concurrente, continuación posterior al request, nueva traza tras reinicio con referencia lógica preservada, links solo confiables, dos bindings/textos iguales no mezclados y contexto no disponible explícito; no modificar archivos nativos. Prerrequisitos de007: T019.
- [ ] T033 [P] [US2] Escribir `backend/tests/integration/observability/test_acquisition.py` consumiendo receptor/adaptador003, validación001 y recepción/agregados/retirada002 reales: SFTP limpio/abortado, archivos ilegibles, válidos/invalidos/duplicados/anticipados, misma publicación/nuevo intento y recuperación del mismo intento; contrastar resultados durables con logs/spans y no añadir CSV/JSON/credenciales técnicas al payload nativo. Añadir caso de un intento que confirma3 registros, falla con2 pendientes y luego los incorpora al recuperar: conservar attempt_ref, cambiar execution_ref y observar dos ejecuciones (fallo/éxito), un terminal lógico y cinco aceptados una vez; releerlo no crea más emisiones. Prerrequisitos de007: T019.
- [ ] T034 [P] [US2] Escribir `backend/tests/integration/observability/test_costs_reports.py` con004/005 reales: cálculo/contraste/consulta, admisión/captura/espera/render/preflight/publicación/descarga PDF y fallos controlados; distinguir report.admitted/report.completed y rechazo previo, terminal tras commit ganado, recuperación sin reemisión y respuesta funcional sin excepción interna. Prerrequisitos de007: T019.
- [ ] T035 [P] [US2] Escribir `backend/tests/integration/observability/test_identity_administration.py` con006 y configuraciones001/004 reales: autenticación/autorización/sesiones, lectura de historial y cambios administrativos, incluidos denegados antes del módulo y rollback; comprobar una emisión de operación objetivo y decisión de autorización separada, sin datos personales ni sustitución de FunctionalAudit009. Prerrequisitos de007: T019.
- [ ] T036 [P] [US2] Escribir prueba de navegación agregado→logs→traza→otra ejecución en `frontend/tests/e2e/observability-diagnosis.spec.ts` con Programador autorizado, filtros de período/entorno/función/resultado/severidad/referencia y mensajes explícitos cuando la traza no esté disponible. Prerrequisitos de007: T030.
- [ ] T037 [US2] Completar semántica común de terminales en `backend/src/ecs_ec/observability/events.py` y `backend/src/ecs_ec/observability/lifecycle.py`: éxito/rechazo/fallo coherentes, una emisión por transición lógica informada por productor, etapas/ejecuciones excluidas de operaciones; mezcla válida de recepción→success con conteos, todo rechazado→expected_rejection y fallo parcial recuperable→execution.completed/unexpected_error con counts=null, sin cerrar el intento002 processing/partial_failure. Emitir reception.completed solo al ganar su transición durable a completed y con resumen completo, incluidas aceptaciones previas a recuperación; una lectura sin procesamiento no crea terminal ni ejecución. Mantener report.admitted/completed y exclusión de rechazos preadmisión; sin commits ni deduplicador de negocio propio. Prerrequisitos de007: T031, T033, T034, T035.
- [ ] T038 [US2] Completar `Telemetry.continue` en `backend/src/ecs_ec/observability/context.py` y `backend/src/ecs_ec/observability/tracing.py` para referencias durables/sobres internos de propietarios, nuevo execution_ref al recuperar, intento estable al continuar y nuevo al reenviar; HMAC/versionado por entorno, span link solo si se conserva contexto y búsquedas por referencia entre trazas. No persistir contexto en mediciones/boletas/PDF ni reconstruir relaciones desde fuentes libres. Prerrequisitos de007: T037, T032.
- [ ] T039 [US2] Añadir paneles de logs y enlaces Jaeger a `deploy/observability/grafana/dashboards/platform.json`, con textos de códigos de catálogo, filtros técnicos, UTC/versión/entorno/resultado, referencias opacas en campos y drilldown por trace/operation/publication. Conservar Viewer y separación de entorno; una traza ausente no afirma que nunca hubo operación. Prerrequisitos de007: T038, T036, T030.
- [ ] T040 [US2] Ejecutar pruebas reales003/001/002 de cobertura y reintentos; identificar en `specs/007-observabilidad-externa/validation/coverage-acquisition.md` cada fila de contrato, resultado, referencia, intento/ejecución y señal observada. Verificar recepción→validación→conservación/agregación, sin confundir archivos/posiciones ni declarar aceptación SFTP con fixtures del puerto002. Prerrequisitos de007: T039, T033.
- [ ] T041 [US2] Ejecutar pruebas004/005/006 y configuraciones001/004 reales y registrar cobertura por operación/resultado en `specs/007-observabilidad-externa/validation/coverage-business.md`; contrastar contra resultados/eventos009 confirmados, comprobar ventanas/fallos/correlación y ejecutar E2E de diagnóstico; mantener pendiente cualquier fila sin productor o llamada de instrumentación propietaria real. Prerrequisitos de007: T040, T034, T035, T036.
- [ ] T042 [US2] Completar catálogo/procedimientos de diagnóstico en `deploy/observability/README.md` y registrar matriz SC-002/004 con todas las filas, resultados e incidencias en `specs/007-observabilidad-externa/validation/coverage.md`; sincronizar `specs/007-observabilidad-externa/contracts/integrations.md` y `research.md` solo si la integración obliga a concretar un mapeo, manteniendo fuentes/anclajes y límites de propiedad. Prerrequisitos de007: T041.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 5: User Story 3 — Revisar métricas de funcionamiento (P1)

**Objetivo**: métricas con unidades/ventanas/denominadores y cobertura interpretables,
sin inflar conteos por etapas, fragmentos, relecturas, recuperación o IDs libres.

**Prueba independiente**: diez consultas (ocho éxitos/dos fallos→20%), cinco registros
(3/1/1), duraciones100/200/300ms→media200ms, cero/N/D frente a ausencia, fronteras
adyacentes, reenvío/replay y cardinalidad estable. Comparar con entradas/resultados conocidos,
no solamente con otro cálculo del mismo log. Fixtures técnicas pueden probar expresiones;
la aceptación con recepción/consultas exige los proveedores reales de US2.

**Pruebas primero**: contrato, consultas y presentación antes de modificar dashboards.
Las tareas de pruebas [P] trabajan en archivos distintos y requieren el mismo checkpoint.

- [ ] T043 [P] [US3] Escribir `backend/tests/contract/observability/test_signal_catalog.py`: nombre/unidad/hecho/ventana/agregación por medida, terminales elegibles, exclusiones, dimensiones cerradas, numerador/denominador y «valor nullable y cobertura»; no API funcional nueva ni IDs como dimensiones, y rechazo esperado fuera del numerador inesperado. Definir execution_unexpected_error_percent exclusivamente sobre execution.completed, distinto del denominador de operaciones lógicas; verificar el caso parcial recuperado con2 ejecuciones/un intento/5 registros,50% de error por ejecución y0% por intento completado. Prerrequisitos de007: T030.
- [ ] T044 [P] [US3] Escribir `backend/tests/integration/observability/test_metrics.py` con consultas reales Loki para10/8/2→20%, recepción1/5/3/1/1, archivos separados, report.admitted/completed, duraciones/percentiles, ventana `[inicio,fin)` y extremos a1ns si corresponde, denominador0/desconocido→N/D; validar contra fixture y resultado de dominio conocido del mismo corte. Contrastar también el caso3 aceptados/fallo/2 recuperados: dos execution.completed, un reception.completed y cinco novedades sin duplicación; execution_unexpected_error_percent=50% y unexpected_error_percent lógico=0%, con coberturas y denominadores explícitos. Prerrequisitos de007: T030.
- [ ] T045 [P] [US3] Escribir `backend/tests/integration/observability/test_collection_continuity.py`: heartbeat45s ausente, descartes/reset/huecos, posiciones perdidas, timestamp/línea repetidos, reinicio Alloy/Loki y cobertura entre heartbeats; nunca cero fabricado, reparación retroactiva de huecos ni total exacto tras replay ambiguo. Comprobar límite de conciliación10000 eventos. Crear casos seleccionables jaeger_only y logs_only: caída aislada Jaeger/OTLP con logs operativos y caída Alloy/Loki con trazas consultables; consultar Jaeger como Programador, contrastar evidencia propia y conservar huecos tras recuperación. Validar que confirmación OTLP no equivale a persistencia consultable ni inactividad a indisponibilidad. Prerrequisitos de007: T030.
- [ ] T046 [P] [US3] Escribir `frontend/tests/e2e/observability-metrics.spec.ts` para unidad/ventanaUTC/operación/corte/política/versión y cobertura visibles, estados de consulta/error/ausencia distintos, proporciones N/D y conteos observados/parciales; sin estadísticas técnicas en UI/PDF funcionales. Prerrequisitos de007: T030.
- [ ] T047 [US3] Implementar consultas completas del catálogo en `deploy/observability/grafana/dashboards/platform.json`: conteos por terminal, archivos por003, registros/novedades por002, generaciones005, duraciones/p50/p95 y deltas de pérdidas que consideran reset, no suma de snapshots; `100 * unexpected_error / (success + expected_rejection + unexpected_error)` con mismo corte/filtros, denominador0/desconocido→N/D. Seleccionar campos JSON necesarios y agrupar solo dimensiones permitidas, nunca referencias/sequence ni promediar percentiles. Añadir execution_unexpected_error_percent sobre execution.completed, sin mezclarlo con los terminales lógicos; counts de ejecución fallida no aportan registros y reception.completed incorpora una sola vez el resumen completo del intento recuperado. Prerrequisitos de007: T043, T044, T039.
- [ ] T048 [US3] Implementar paneles/transformaciones de cobertura en `deploy/observability/grafana/dashboards/platform.json` y completar salud si hace falta en `backend/src/ecs_ec/observability/health.py`: `complete` «Ventana dentro de retención/inicio conocido, secuencias conciliadas, heartbeats/recolectores continuos, sin pérdidas/replays ambiguos y política compatible. Cero significa cero observado.»; `partial` «Pérdida/hueco conocido, muestreo de esa señal, arranque/cierre dentro de ventana o conservación vencida. Valores observados con causa, sin totalidad.»; `unknown` «>45 s sin heartbeat, receptor inaccesible o continuidad/posiciones no verificables. Último dato si existe; total desconocido.». Conciliar filas acotadas entre heartbeats, >=10000/fallo→unknown, ventanas abiertas provisionales y subventanas sin esconder huecos; sin UUID como dimensiones ni nueva API/servicio. Separar log_collector_status/last_log_collector_success de trace_export_status/last_trace_export_success y sus contadores por arranque. Contrastar trazas esperadas/muestreo/pérdidas con Jaeger consultable bajo autorización Programador; confirmación de exportación no basta, consulta fallida/truncada o evidencia insuficiente→unknown, sin trasladar una caída a la otra señal ni inventar fallos por ausencia de nuevos lotes. Prerrequisitos de007: T047, T045.
- [ ] T049 [US3] Completar visualización en `deploy/observability/grafana/dashboards/platform.json`: ventana inicial15min seleccionable1min–24h, `[start,end)`/corteUTC, nombre/unidad/operación, versión/política/filtros, edad del último heartbeat y «Dashboard incluye configuración esperada aunque nunca haya llegado una señal.»; trazas/logs con cobertura independiente, avisos de retención/muestreo y enlaces a los eventos/etapas disponibles. Prerrequisitos de007: T048, T046.
- [ ] T050 [US3] Añadir y ejecutar `backend/tests/integration/observability/test_cardinality.py` con1000 operaciones/referencias distintas e iguales dimensiones: solo service_name/entorno/operación/resultado/severidad, sin filename/user/trace/boot IDs persistentes o intermedios, número de series estable y deduplicación de relectura verificada. No cambiar etiquetas para ocultar un fallo de exactitud. Prerrequisitos de007: T049.
- [ ] T051 [US3] Ejecutar pruebas de catálogo/LogQL/continuidad/cardinalidad/E2E y carga conocida sobre stack local y proveedores reales; registrar consultas/ventanas/resultados/series,10/8/2→20%, recepción5/3/1/1, duraciones y replays en `specs/007-observabilidad-externa/validation/metrics.md`; actualizar catálogo operativo en `deploy/observability/README.md`, sin declarar exactitud donde falte cobertura. Prerrequisitos de007: T050, T042.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 6: User Story 4 — Mantener una observación segura e independiente (P2)

**Objetivo**: verificar protección de contenidos, continuidad funcional, políticas,
recursos acotados y disponibilidad local de las tres señales sin servicios remotos.
Las protecciones básicas ya son obligatorias en fundaciones/US1, no se activan recién aquí.

**Prueba independiente**: marcadores sensibles ausentes antes/después de emitir; red y
receptores caídos; saturación de colas/spool/cuotas; retención24h/168h independiente de
los12meses funcionales; trazas muestreadas con aviso, recolección sin sesión humana y
recorrido local sin salida remota. SC-008 agrega diez tareas con personas: al menos nueve
identifican operación/resultado/etapa sin ayuda; sin participantes, queda pendiente.

- [ ] T052 [P] [US4] Escribir `backend/tests/integration/observability/test_privacy.py` con marcadores sintéticos en contraseña/cookie/token/clave/correo/IP/nombres con controles/cuerpos/CSV/boleta/PDF/energía/importes/excepción; buscar en cola, spool, Loki, Jaeger y logs de herramientas/gateway y exigir cero coincidencias, códigos/severidad/correlación no inyectables y respuestas funcionales saneadas. Prerrequisitos de007: T030, T042.
- [ ] T053 [P] [US4] Escribir `backend/tests/integration/test_observability_isolation.py` para operaciones reales con transporte/recolección/consulta caídos, saturación y shutdown: preservar permisos/commits/mediciones/cálculos/PDF y evidencia009, respetar límites, contabilizar pérdidas y mostrar cobertura desconocida; integrar la regresión trasladada10/8/2→20% y revocación/accesos directos deUS1 sin duplicar la lógica de sus fixtures. Incluir caídas independientes Jaeger/OTLP y Alloy/Loki: la señal disponible conserva su evidencia propia, la afectada declara la limitación y recuperar transporte no borra huecos históricos; no conceder consulta humana a credenciales de ingesta. Prerrequisitos de007: T030, T042.
- [ ] T054 [P] [US4] Escribir `backend/tests/integration/observability/test_retention_sampling.py` para señales persistidas antes/después de reinicio, TTL168h o24h desechable con compactor/GC y verificación hasta60min tras vencimiento, y muestreo1.0/0.1 con revisión/avisos; comprobar que evidencia funcional de12meses e historial006 no se reducen ni cambian permisos, y que ausencia no prueba inexistencia. Prerrequisitos de007: T030, T042.
- [ ] T055 [US4] Completar políticas versionadas/validación en `backend/src/ecs_ec/observability/lifecycle.py` y `.env.example`: logs terminales/control sin muestreo, ratio de raíz de trazas1.0 inicial/aceptación e hijos heredados, perfil dedicado0.1 con aviso; retención por señal/entorno y control de cambio, parámetros y límites previos a activar emisión; config inválida deshabilita solo emisión y registra motivo seguro. Prerrequisitos de007: T052, T053, T054, T051.
- [ ] T056 [US4] Aplicar cuotas reales o volúmenes de tamaño fijo y rechazo de ingesta técnica al>=90% en `compose.yaml`, `deploy/observability/loki.yaml`, `deploy/observability/jaeger.yaml`, `deploy/observability/alloy.alloy` y `backend/src/ecs_ec/observability/logging.py`: spool128MiB, posiciones64MiB, Loki2GiB, Badger2GiB y Grafana256MiB por entorno; medir overhead/RAM aparte, preservar presupuesto OTLP5s/reintentos y no bloquear ni borrar negocio cuando el destino esté lleno. Documentar mecanismo de cuota comprobable y descartes, no confiar solo en TTL. Prerrequisitos de007: T055.
- [ ] T057 [US4] Completar configuración de retención/GC por perfil en `deploy/observability/loki.yaml`, `deploy/observability/jaeger.yaml` y worker de `backend/src/ecs_ec/observability/logging.py`:168h normal/24h desechable, spool<=retención, compactor10min y demora de borrado10min, persistencia y límite de verificación60min tras TTL; sin montaje o retirada de volúmenes funcionales ni cambio retroactivo supuesto. Prerrequisitos de007: T056.
- [ ] T058 [US4] Ejecutar privacidad/aislamiento bajo fallos de emisor, recolector y visor, agotamiento de colas/disco y shutdown contra productores reales; registrar marcadores únicamente sintéticos, resultados/commits comparados, límites y pérdidas, revocación y puertos denegados en `specs/007-observabilidad-externa/validation/isolation.md`; corregir filtraciones en configuración/allowlist propia antes de aceptar. Prerrequisitos de007: T057.
- [ ] T059 [US4] Ejecutar casos de muestreo, persistencia y retención real24h desechable (prueba prolongada) y comprobación de configuración168h; registrar tiempos previos/posteriores aTTL, consulta/disco/GC y protección funcional en `specs/007-observabilidad-externa/validation/retention.md`. No acreditar borrado físico con un test de reloj, ni marcar terminado si no venció/verificó la prueba real. Prerrequisitos de007: T058.
- [ ] T060 [US4] Ejecutar recorrido local de tres señales con imágenes ya descargadas y salida a observabilidad remota bloqueada, autorización Programador y denegaciones funcionales, sin sesión humana para recolectar; repetir arranque/operaciones reales sin perfil `observability` y registrar SC-009/FR-024 en `specs/007-observabilidad-externa/validation/local.md`, sin convertir VPS en prerrequisito local. Prerrequisitos de007: T059.
- [ ] T061 [US4] Preparar y ejecutar diez tareas de diagnóstico con Programadores representativos, sin ayuda: localizar operación/resultado/etapa y reconocer límites; registrar sujetos opacos, éxito y obstáculos por tarea en `specs/007-observabilidad-externa/validation/usability.md`, exigir>=9/10 para SC-008. Mantener esta tarea pendiente si faltan participantes/resultados; E2E no sustituye la evaluación. Prerrequisitos de007: T060.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Phase 7: Polish & Cross-Cutting Concerns — cierre verificable

**Propósito**: completar operación/documentación y aceptación de toda la spec.
T062 puede comenzar tras T060 mientras T061 espera participantes; T063/T064 siguen
su cadena documental y registran SC-008 pendiente. T065 exige T061 y T064 completadas.
Esta fase no autoriza despliegues ni cumplimiento de criterios sin evidencia real.
No marcar checklists de revisión por haber generado este archivo.

- [ ] T062 Completar procedimientos local/VPS en `deploy/observability/README.md`, `deploy/technical-gateway/README.md` y enlaces de `deploy/README.md`: versiones/digests, señales/cobertura/políticas, cuotas/TLS, rotación/revocación, última señal, caídas, retención/restauración técnica y separación funcional; sincronizar `specs/007-observabilidad-externa/quickstart.md` con comandos realmente implementados, sin afirmar VPS validada sin ejecución. Prerrequisitos de007: T060.
- [ ] T063 Revisar docstrings/contratos de todos los archivos propios en `backend/src/ecs_ec/observability/`, pruebas en `backend/tests/unit/observability/`, `backend/tests/integration/observability/`, `backend/tests/contract/observability/`, scripts en `scripts/observability/` y E2E en `frontend/tests/e2e/`; documentar entradas/salidas/errores/efectos, fórmulas/unidades/límites y origen/regeneración de artefactos generados; registrar correcciones reales en `specs/007-observabilidad-externa/validation/documentation.md`. Prerrequisitos de007: T062.
- [ ] T064 Ejecutar los escenarios técnicos reproducibles de `specs/007-observabilidad-externa/quickstart.md` en entorno limpio con dependencias reales, lockfiles y stack técnico fijado; guardar comandos/versiones/cortes/resultados en `specs/007-observabilidad-externa/validation/quickstart.md`, registrar como pendientes SC-008 y los escenarios humanos de T061 si todavía faltan participantes/resultados, sin contarlos como ejecutados; identificar pruebas prolongadas/externas pendientes y no crear aprobaciones o resultados de personas ficticios. Prerrequisitos de007: T063.
- [ ] T065 Consolidar matriz FR-001–FR-024/SC-001–SC-009 con evidencia por historia, cobertura por productor, limitaciones y condiciones reales de aceptación en `specs/007-observabilidad-externa/validation/acceptance.md`; actualizar estado de implementación de007 en `docs/implementation-roadmap.md` únicamente según resultados obtenidos, sin ejecutar tareas de otras specs ni dar por aceptada VPS o SC-008 pendientes. Prerrequisitos de007: T061, T064.

**Checkpoint**: ejecutar las verificaciones aplicables y conservar pendientes todos los
casos sin evidencia; el comienzo de la siguiente fase no acredita esta aceptación.

---

## Dependencies & Execution Order

### Capacidades externas y propiedad

| Capacidad / propietario | Documento y ruta prevista | Tareas que la necesitan |
| --- | --- | --- |
| Base009: scaffold, configuración, reloj, lifespan, DB/UoW | [Plan009](../009-fundaciones-plataforma/plan.md); `pyproject.toml`, `compose.yaml`, `backend/src/ecs_ec/core/`, `backend/src/ecs_ec/main.py` | Setup/emisor; no crear esas capacidades desde007. |
| Evidencia/EventWriter009 | [Contrato009](../009-fundaciones-plataforma/contracts/integrations.md); `backend/src/ecs_ec/audit/` | Contrastar commits/eventos/retención, sin usar logs como historial durable. |
| Identidad006, sesiones/CSRF/permisos/historial | [Contrato006](../006-acceso-usuarios-rbac/contracts/integrations.md); `backend/src/ecs_ec/identity/` | Matriz funcional US1 y cobertura de identidad/administración US2; Programador sigue externo. |
| Fuente/SFTP/adaptación003 | [Contrato003](../003-simulador-pas600-sftp/contracts/sftp-reception.md); `backend/src/ecs_ec/acquisition/` | Recepción nativa, publicación/intentos y cobertura real US2. |
| Validación/configuración001; recepción/agregados/retirada002 | [Contrato001](../001-visualizar-consumo-categorias/contracts/integrations.md), [contrato002](../002-registro-retencion-consumo/contracts/integrations.md); `backend/src/ecs_ec/consumption/` | Casos reales de consultas/recepción US1–US4. |
| Costos/boletas/contraste004 y PDF005 | [Contrato004](../004-costos-tarifa-bt43/contracts/integrations.md), [contrato005](../005-generar-reportes-pdf/contracts/integrations.md); `backend/src/ecs_ec/costs/`, `backend/src/ecs_ec/reports/` | Permisos funcionales US1, cobertura US2 y aislamiento US4. |

Los propietarios incorporan sus llamadas de instrumentación al emisor real007 cuando
exista;007 verifica integración y ofrece el contrato, sin implementar su negocio.
Un prerrequisito ausente se registra por capacidad/documento/ruta. No ejecutar automáticamente
otras specs desde esta lista ni supeditar operación funcional a visores, SMTP o aceptación008.

### Grafo de fases e historias

```text
Plataforma009 base → Setup → Foundational (emisor + configuraciones privadas)
                                  ├─ US1 acceso/stack → MVP de consulta técnica
                                  └─ pruebas/puertos comunes de US2
US1 + productores001–006 reales e instrumentados → US2 cobertura y correlación completa
US1 + paneles de logs de US2 → US3 consultas y cobertura; aceptación final con US2 real
US1 + US2 → primeras pruebas US4
US3 validada → políticas/recursos y validación local técnica US4 → T060
T060 ─┬─ T061 (personas) ──────────────────────┐
      └─ T062 → T063 → T064 (documentación) ───┴─ T065 (aceptación integral)
```

Los tests aislados no requieren terminar los visores de otra historia. El acceso real a
tres señales sí necesita el stack técnico de US1; las pruebas finales de cobertura y
continuidad esperan sus proveedores reales. Las dependencias anteriores son explícitas,
no una afirmación de que todas las historias son implementables sin ninguna integración.

Dentro de cada historia: pruebas primero → tipos/puertos → configuración/servicios →
integración → ejecución y evidencia. Los archivos compartidos `events.py`, `context.py`,
`tracing.py`, `health.py`, `lifecycle.py`, `platform.json`, `nginx.conf`, `.env.example`,
`compose.yaml` y README se modifican secuencialmente según las dependencias de cada tarea.
Un `[P]` no permite saltar estas barreras ni ejecutar en paralelo dos escritores del mismo archivo.

### Oportunidades y ejemplos de ejecución paralela

- **Setup**: T003, T004. Después de T001/T002, fixtures y preparación de certificados trabajan en archivos distintos.
- **Fundaciones**: T005, T006, T007. Redacción de pruebas después de fixtures; sin escribir implementación común simultáneamente.
- **Configuración técnica**: T016, T017, T018. Tras versiones/certificados/esquema, cada configuración tiene archivo propio; Compose se integra después.
- **US1**: T020, T021, T022, T023. Redactar contratos/provisión/matriz/E2E después del checkpoint fundamental; implementaciones compartidas secuenciales.
- **US2**: T031, T032, T033, T034, T035. Redactar pruebas de contratos/productores en archivos separados; ejecutar las de dominio solo con capacidades reales.
- **US3**: T043, T044, T045, T046. Pruebas de catálogo, medidas, continuidad y presentación tras US1; un solo escritor posterior de platform.json.
- **US4**: T052, T053, T054. Pruebas de privacidad/aislamiento/retención tras US1/US2; configuración de políticas/cuotas/retención después de US3, en secuencia.

Ejemplos concretos por historia (son sugerencias de distribución, no invocaciones
automáticas de agentes):

- **US1**: T020, T021 pueden redactarse simultáneamente después de sus prerrequisitos; la implementación e integración conserva el orden de la fase.
- **US2**: T033, T034 pueden redactarse simultáneamente después de sus prerrequisitos; la implementación e integración conserva el orden de la fase.
- **US3**: T044, T045 pueden redactarse simultáneamente después de sus prerrequisitos; la implementación e integración conserva el orden de la fase.
- **US4**: T052, T054 pueden redactarse simultáneamente después de sus prerrequisitos; la implementación e integración conserva el orden de la fase.

## Trazabilidad del traslado

IDs anteriores son procedencia histórica local a cada spec. Ningún trabajo trasladado
se considera terminado por renumerarlo. Esta tabla conserva el alcance completo del borrador:

| Borrador007 / procedencia008 | Tareas integrales007 | Alcance conservado |
| --- | --- | --- |
| Anterior T001 de007 / T029 de008 | T008, T009, T010, T011, T012, T013, T014, T015, T019 | Loguru seguro, cola1024/16KiB, pérdidas/heartbeat15/45s, OTel2048/5s y referencias opacas. |
| Anterior T002 de007 / infraestructura de T102 de008 | T020, T024, T025, T026, T027, T028, T029, T030 | TLS/Basic por entorno, archivo reemplazable, Viewer/Jaeger consulta, credenciales separadas, fuentes privadas y loopback. |
| Anterior T003 de007 / T100–T101 de008 | T016, T017, T018, T039, T047, T048, T057, T059 | Alloy/Loki/Grafana/Jaeger con Badger persistente, etiquetas/checkpoints/pérdidas, spool y TTL168h/24h independiente de12meses. |
| Anterior T004 de007 / T100–T101 de008 | T028, T037, T042, T049, T062 | Perfil técnico opcional, catálogo/cobertura/muestreo/retención, terminal único y dimensiones acotadas sin implementar negocio. |
| Anterior T005 de007 / pruebas comunes de T103 de008 | T030, T044, T051, T053, T058 | Archivo test_observability_isolation.py,10/8/2→20%, cobertura distinta de cero, colas, protección, revocación y bypass directo. |

## Cobertura de requisitos y aceptación

Esta matriz asigna trabajo; no aprueba requisitos ni marca checklists.

| Requisitos / resultados | Historia/capacidad | Tareas007 |
| --- | --- | --- |
| FR-001, FR-002, FR-003, FR-004, FR-022; SC-001 | US1: acceso, roles y permisos independientes | T020, T022, T023, T024, T025, T026, T027, T030 |
| FR-005, FR-006, FR-007, FR-011, FR-012, FR-013; SC-002, SC-004 | Emisor/US2: todas las operaciones, resultados y correlación | T008, T009, T010, T013, T031, T032, T033, T034, T035, T037, T038, T040, T041 |
| FR-008, FR-009, FR-010; SC-003 | US3: conteos/unidades/ventanas/proporciones/cardinalidad | T043, T044, T047, T050, T051 |
| FR-014 | US2/US3: consulta y navegación entre señales | T036, T039, T049 |
| FR-015, FR-016; SC-005 | Fundaciones/US4: protección previa y errores saneados | T011, T052, T058 |
| FR-017, FR-021; SC-006 | Fundaciones/US4: monolito y no bloqueo | T012, T013, T015, T053, T056, T058 |
| FR-018; SC-007 | US3/US4: continuidad, pérdidas y cero observado | T014, T045, T048, T051, T059 |
| FR-019, FR-020; SC-007 | US4: conservación/muestreo independientes | T054, T055, T057, T059 |
| FR-023 | Documentación de catálogo, acceso y políticas | T029, T042, T051, T062, T063 |
| FR-024; SC-009 | US1/US4: tres señales locales y recolección sin sesión | T004, T030, T060 |
| SC-008 | US4: diagnóstico con personas,>=9/10 | T061 |
| FR-001–FR-024; SC-001–SC-009 | Cierre: solo evidencia real | T064, T065 |

## Implementation Strategy

1. **MVP de US1**: completar Setup/Foundational y acceso/stack local; consultar las tres
   señales con fixtures técnicas y emisor real, revocar acceso y verificar matriz con
   proveedores funcionales disponibles. No confundir ese MVP con SC-002 o métricas de negocio
   ya aceptadas. Sin006/funciones reales, su parte de matriz sigue pendiente.
2. **US2**: conectar el contrato común a puntos de instrumentación de productores ya
   implementados, verificar operaciones/resultados y correlación completa. Registrar
   faltantes externos en vez de recrear dominio en007.
3. **US3**: completar métricas y cobertura sobre ese stack; contrastar carga conocida,
   unidades/ventanas/denominadores y ausencia/replay/cardinalidad.
4. **US4**: demostrar protección/aislamiento bajo fallo y saturación, retención real,
   muestreo con aviso y ejecución local; completar diagnóstico con personas.
5. **Cierre**: tras T060, avanzar T062/T063/T064 sin esperar participantes de T061;
   documentar SC-008 pendiente sin acreditarlo. T065 espera tanto T061 como T064 para
   aceptación integral, con resultados observados y pendientes explícitos. No saltar
   una tarea marcada pendiente porque sea prolongada,
   requiera personas o dependa de capacidad externa.

La ejecución se inicia con `$speckit-implement` después de revisión de consistencia.
Generar estas tareas no instala infraestructura, no ejecuta pruebas funcionales y no
autoriza despliegue ni aprobación automática de checklists.
