# Implementation Plan: Fundaciones compartidas de la plataforma

**Contexto**: `009-fundaciones-plataforma` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Reorganización del diseño común previamente concentrado en spec-008.
**Contexto compartido**: [arquitectura](../../docs/architecture.md), [hoja de ruta](../../docs/implementation-roadmap.md).

## Summary

Construir únicamente la base común del monolito: herramientas, PostgreSQL/UoW, utilidades
temporales, almacenamiento funcional de auditoría/eventos y operación. No construir cuentas,
mediciones, cálculos, PDF, notificaciones ni observabilidad técnica como prerrequisitos ocultos.

## Technical Context

**Language/Version**: CPython 3.14 convencional y TypeScript; versiones de la arquitectura común.
**Primary Dependencies**: FastAPI 0.162.0, uv, Pydantic 2, Uvicorn, SQLAlchemy 2/Psycopg 3,
Alembic; React 19.x/Next.js 16.x export estático, npm/Node >=20.9 para build.
**Storage**: PostgreSQL 18 real; UUID, UTC, JSONB tipado y transacciones explícitas.
**Testing**: pytest/HTTPX, PostgreSQL 18, Vitest/Playwright; suites se habilitan al incorporar código.
**Target Platform**: Docker Compose local y VPS posterior con HTTPS.
**Project Type**: Base técnica del monolito modular.
**Performance Goals**: Sin nuevo SLO; medir construcción/restauración y documentar recursos reales.
**Constraints**: Una imagen/proceso inicial; secretos externos, sin datos privados en export Next.
**Scale/Scope**: Un edificio; no depende de completar ninguna funcionalidad de negocio.

## Constitution Check

| Principio | Diseño |
| --- | --- |
| I. Propósito eléctrico | Soporte al monitoreo existente, sin nuevo alcance de negocio. |
| II. Monolito modular | DB y adaptadores externos; código propio en una unidad. |
| III. Documentación integral | Documentar archivos, funciones, clases, pruebas y scripts en su cambio. |
| IV. Integridad/trazabilidad | UTC, contratos tipados, transacciones, cobertura y conservación explícitas. |
| V. Visualización verificable | El scaffold no inventa datos; los módulos incorporan sus vistas después. |

Cumplimiento de diseño previo/posterior sin excepciones; no acredita ejecución.

## Project Structure

### Documentation (this feature)

`specs/009-fundaciones-plataforma/`: spec, plan, research, data-model, quickstart,
contratos y tareas. La arquitectura general reside en `docs/architecture.md`.

### Source Code (repository root, estructura propuesta)

`pyproject.toml`, `uv.lock`, `.python-version`, `.env.example`, `Dockerfile`, `compose.yaml`,
`.github/workflows/ci.yml`, `backend/src/ecs_ec/{main.py,core/,audit/}`, Alembic/migraciones,
scaffold `frontend/`, pruebas comunes y `deploy/{README.md,backup.sh,restore.sh}`.
Los módulos de negocio extienden el registro de rutas y servicios internos sin duplicarlo.

## Phase 0: Research

[research.md](research.md) conserva investigación previa de versiones, export estático y
Compose. No se eligieron nuevas tecnologías durante el traslado.

## Phase 1: Design & Contracts

[data-model.md](data-model.md) y [contrato común](contracts/integrations.md) poseen la
auditoría/eventos/cobertura. Los actores se guardan como referencias opacas de cuenta o
proceso, sin exigir tablas de identidad para aplicar la migración base. La integridad de
cuentas la valida su módulo al escribir, conservando referencias históricas.

Los productores utilizan EventWriter en su unidad de trabajo; no hay broker ni dependencia
del consumidor008. El ciclo de vida admite registrar adaptadores internos por funcionalidad,
sin importar módulos todavía ausentes. El helper de retención no decide cuándo borrar ni
reinicia plazos por lecturas; cada productor aplica su política.

## Dependencies & Delivery

Fundaciones prepara DB/UoW, reloj y aplicación base; US1 valida contenedores/salud;
US2 incorpora auditoría y prueba atomicidad/cobertura;
US3 verifica restauración y documenta VPS. Identidad y datos consumen esa base después.
La infraestructura de correo y los visores se agregan en 008/007, respectivamente.
Validación prevista en [quickstart.md](quickstart.md), trabajo en [tasks.md](tasks.md).

## Complexity Tracking

Sin excepciones constitucionales. No hay nuevos servicios propios ni dependencia circular.
