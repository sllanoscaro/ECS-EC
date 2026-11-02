---
description: "Tareas de la infraestructura común trasladadas de spec-008"
---

# Tasks: Fundaciones compartidas de la plataforma

**Input**: [spec](spec.md), [plan](plan.md), [modelo](data-model.md), [contrato](contracts/integrations.md), [quickstart](quickstart.md).
**Contexto**: [arquitectura](../../docs/architecture.md), [hoja de ruta](../../docs/implementation-roadmap.md).
**Estado**: Todas pendientes. Documentar cada archivo y elemento propio según constitución.
**Tests**: Pruebas con resultados conocidos para integridad, datos y calendario.
**Rutas**: Relativas a la raíz del repositorio. IDs locales; no ejecutar otras specs automáticamente.

## Phase 1: Setup — herramientas comunes

- [ ] T001 Crear la estructura de paquetes documentados en `backend/src/ecs_ec/__init__.py`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx` y `deploy/README.md`, siguiendo los módulos y responsabilidades del plan y dejando una página inicial estática para la construcción.
- [ ] T002 Inicializar `.python-version`, `pyproject.toml` y `uv.lock` con CPython 3.14 convencional, `requires-python = ">=3.14,<3.15"`, `fastapi==0.162.0`, Pydantic 2, Uvicorn, SQLAlchemy 2/Psycopg 3 asíncronos, Alembic, Loguru, OpenTelemetry, tzdata fijado, pytest, HTTPX y jsonschema; resolver versiones compatibles y comprobar `uv sync --locked`.
- [ ] T003 [P] Inicializar `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json` y `frontend/next.config.ts` con React 19.x, Next.js 16.x, TypeScript y Node >=20.9; fijar versiones y `output: 'export'`, sin servidor Node en ejecución. Prerrequisito: T001.
- [ ] T004 Configurar `pytest.ini`, `backend/tests/conftest.py`, `frontend/vitest.config.ts` y `frontend/playwright.config.ts` con PostgreSQL 18 real, base de prueba independiente, reloj/transporte controlables y protección contra uso de una base de producción; añadir Vitest, Testing Library y Playwright al manifiesto/lock de T003. Prerrequisitos: T002–T003.
- [ ] T005 [P] Crear `.env.example`, `.dockerignore` y actualizar `.gitignore` con las variables del quickstart, secretos externos y valores locales explícitamente sintéticos; separar transporte local, URL pública, zona del edificio y perfiles técnicos. Prerrequisito: T001.

## Phase 2: Foundational — núcleo técnico bloqueante

- [ ] T006 [P] Escribir y ejecutar `backend/tests/unit/core/test_retention.py` y `backend/tests/integration/core/test_unit_of_work.py` para aniversario de 12 meses, bisiesto/DST, UTC, rollback y cierre de recursos; usar PostgreSQL real para transacciones.
- [ ] T007 Implementar configuración validada, reloj UTC/monotónico inyectable internamente y función de aniversario en `backend/src/ecs_ec/core/settings.py`, `backend/src/ecs_ec/core/clock.py` y `backend/src/ecs_ec/core/retention.py`; aplicar «Identidades UUID generadas por la aplicación; revisiones enteras positivas», «siempre inicio < fin», 12 meses calendario, primer instante válido ante hora inexistente y segunda ocurrencia ante hora repetida para conservación.
- [ ] T008 Crear motor Psycopg asíncrono, `AsyncSession`, unidad de trabajo y entorno Alembic en `backend/src/ecs_ec/core/database.py`, `backend/src/ecs_ec/core/unit_of_work.py`, `backend/alembic.ini` y `backend/migrations/env.py`; conservar «Instantes UTC en `timestamptz`» y «`created_at`, `recorded_by` (cuenta o proceso interno), `retain_until` en registros históricos»; aplicar «No usar borrado en cascada que destruya evidencia protegida» y «JSONB tiene esquema explícito de aplicación; no es un contenedor de archivos, excepciones o cuerpos SMTP».
- [ ] T009 Implementar errores comunes tipados en `backend/src/ecs_ec/core/errors.py` sin secretos, SQL ni excepciones crudas; la autenticación/CSRF y sus adaptadores HTTP pertenecen a spec-006.
- [ ] T010 Componer aplicación base, salud, exportación web y ciclo de vida ampliable en `backend/src/ecs_ec/main.py` y `backend/src/ecs_ec/core/lifecycle.py`; comprobar migraciones antes de disponibilidad y permitir módulos aún ausentes; los bucles de notificaciones se registran desde spec-008.

**Checkpoint**: Núcleo DB/UoW, reloj y aplicación base disponibles; aún no hay auditoría ni módulos de negocio.

## Phase 3: User Story 1 — monolito local (P1)

- [ ] T011 [P] [US1] Escribir `backend/tests/integration/core/test_platform_bootstrap.py` para salud, revisión de esquema, exportación web, reinicio y cierre ordenado; usar la aplicación base de fundaciones y preparar escenarios de Compose antes de ejecutar su validación.
- [ ] T012 [US1] Construir `Dockerfile` multietapa que copie la exportación Next a `backend/src/ecs_ec/web/` e inicie un único proceso Uvicorn con paquetes fijados; comprobar que el artefacto estático no contiene datos privados. Prerrequisitos: T002–T005 y T010.
- [ ] T013 [US1] Crear `compose.yaml` con aplicación y PostgreSQL 18, versiones/digests fijados, volumen `/var/lib/postgresql`, PGDATA `/var/lib/postgresql/18/docker` y salud/migraciones previas a la aplicación; Mailpit se incorpora en spec-008 y correo/telemetría no condicionan la disponibilidad funcional. Prerrequisito: T012.
- [ ] T014 [US1] Configurar `.github/workflows/ci.yml` para instalación bloqueada, PostgreSQL real, pruebas backend/frontend y exportación estática; habilitar las suites conforme se incorporen y documentar comandos reproducibles en `README.md`. Prerrequisitos: T004 y T013.
- [ ] T015 [US1] Ejecutar pruebas T011 y construir/arrancar la aplicación base con PostgreSQL local según `specs/009-fundaciones-plataforma/quickstart.md`; registrar versiones, salud, migración desde cero, reinicio/cierre y exportación estática en `specs/009-fundaciones-plataforma/validation/platform.md` sin cuentas, SMTP o visores obligatorios.

**Checkpoint**: US1 construye/arranca la aplicación base y verifica salud/persistencia sin identidad, SMTP o visores.

## Phase 4: User Story 2 — auditoría durable (P1)

- [ ] T016 [US2] Escribir `backend/tests/integration/audit/test_event_writer.py` y `backend/tests/integration/audit/test_summary_coverage.py` para resultado/evento atómicos, rollback, deduplicación, auditoría con actor opaco y acciones repetibles, y cobertura completa/incompleta/desconocida con conteos y ventanas válidos; preparar pruebas antes del comportamiento nuevo y no importar notificaciones para las pruebas comunes.
- [ ] T017 [US2] Definir modelos de eventos, auditoría y cobertura en `backend/src/ecs_ec/audit/models.py` y su migración base `backend/migrations/versions/platform_009_initial.py` según `data-model.md`, incluyendo claves, tipos, índices y restricciones de ventana/conteo/integridad: UUID, `timestamptz`, cargas tipadas, «UNIQUE identidad del módulo/emisor + entidad/revisión/tipo» solo para eventos, actor/proceso opaco y sin tablas de negocio ni FK obligatoria a identidad ausente.
- [ ] T018 [US2] Implementar auditoría funcional, evidencia de cobertura y EventWriter compartido en `backend/src/ecs_ec/audit/models.py`, `backend/src/ecs_ec/audit/services.py` y `backend/src/ecs_ec/audit/events.py`; validar cargas JSONB por esquema de acción y saneamiento antes de persistir auditoría, aplicar la clave de deduplicación de eventos y escribir en la misma transacción que el resultado funcional, con semántica de acciones/denegaciones administrativas producida por spec-006. Conservar alcance temporal del registro/retención, períodos íntegros, huecos conocidos, origen/revisión/corte; los productores no importan notificaciones y la cobertura no depende de telemetría técnica.
- [ ] T019 [US2] Ejecutar `backend/tests/integration/audit/test_event_writer.py` y `backend/tests/integration/audit/test_summary_coverage.py` con productores sintéticos y PostgreSQL real; verificar transacción/deduplicación/alcance de cobertura y registrar resultados en `specs/009-fundaciones-plataforma/validation/audit.md`. Aplicar la migración común antes de habilitar productores de negocio.

**Checkpoint**: Auditoría/eventos y evidencia de cobertura disponibles para productores, con pruebas reales de transacción.

## Phase 5: User Story 3 — operación común (P2)

- [ ] T020 [US3] Documentar construcción, pruebas y arranque común en `README.md`, `deploy/README.md` y `specs/009-fundaciones-plataforma/quickstart.md`, con configuración local sintética y requisitos por funcionalidad.
- [ ] T021 [US3] Implementar y documentar respaldo/restauración PostgreSQL en `deploy/backup.sh`, `deploy/restore.sh` y `deploy/README.md`; verificar restauración en base local separada, conservar revisión de esquema y registrar evidencia protegida en `specs/009-fundaciones-plataforma/validation/restore.md`.
- [ ] T022 [US3] Documentar HTTPS, URL pública, secretos externos, recursos y zona real en `deploy/README.md`; validar entorno VPS solo con configuración real y registrar resultados en `specs/009-fundaciones-plataforma/validation/vps.md`; SMTP se verifica en 008 y acceso técnico en 007.

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T023 Revisar documentación, aislamiento de importaciones y evidencia de FR-001..FR-008/SC-001..SC-004 en `specs/009-fundaciones-plataforma/validation/acceptance.md`, distinguiendo comprobaciones locales y resultados aún pendientes.

## Dependencies & Execution Order

Setup prepara herramientas; fundaciones escribe primero T006 y después implementa
T007–T010; ejecutar las pruebas de T006 antes de ese checkpoint. US1 prepara T011,
construye imagen/Compose/CI y comprueba el conjunto con T015. US2 escribe primero T016,
define tablas/migración T017 e implementa escritor/cobertura T018 antes de T019.
US3 documenta y verifica operación tras US1+US2; T022 requiere entorno VPS real.
T023 cierra evidencia manteniendo pendientes los resultados externos no realizados.

Los cambios en manifiestos, Compose, modelos y migraciones son secuenciales. T003/T005
pueden prepararse tras T001; sus modificaciones de manifiestos no coinciden con T002/T004.
T006/T011 son pruebas en archivos distintos, una vez disponibles sus diseños/prerrequisitos.
Cada elemento de código, pruebas y scripts incorpora documentación en el mismo cambio.

## Independent Tests & MVP

US1: build/export/Compose con salud, revisión y reinicio; US2: transacciones/eventos/cobertura
sin módulos de negocio; US3: respaldo y restauración local con resultados VPS separados.
El MVP técnico para los módulos de negocio necesita US1+US2.

## Coverage

FR-001/002/007 y SC-001: T001–T005/T010–T015; FR-003/004/006 y SC-002/004:
T006–T010/T017–T019; FR-005: T016–T019; FR-008 y SC-003: T020–T023.
23 tareas: setup 5, fundaciones 5, US1 5, US2 4, US3 3, cierre 1.
