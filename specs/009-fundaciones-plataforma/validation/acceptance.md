# Aceptación local de plataforma009

2026-11-02. Implementación común completada y comprobada localmente, con T022 pendiente
de VPS real por decisión explícita del usuario. Las checklists de otras specs no cambian.

| Requisito | Evidencia y resultado |
| --- | --- |
| FR-001 | Paquete `core`/`audit`, composición y scaffold Next en un monolito; manifiestos/lockfiles comunes. |
| FR-002 | Docker multietapa y Compose/PostgreSQL 18 con digests fijados; export estático servido por Uvicorn, sin Node runtime. [Plataforma](platform.md). |
| FR-003 | Settings validados, reloj inyectable, AsyncSession y UoW explícita. Pruebas PostgreSQL de commit/rollback/cierre y configuración. |
| FR-004 | Alembic real y lifecycle extensible por registro; startup/readiness bloquean esquema/DB ausentes. Sin módulos de negocio obligatorios. |
| FR-005 | Tres tablas comunes, cargas por esquema aprobado, deduplicación concurrente y cobertura funcional independiente. [Auditoría](audit.md). |
| FR-006 | Aniversario calendario con UTC, bisiesto, DST y fecha inexistente; períodos/conteos validados, ausencia como NULL y sin cascadas/purga destructiva. |
| FR-007 | PostgreSQL 18 real en base separada, guardia de nombre/URL/.env; pytest, Vitest, Playwright y workflow configurado. Instalaciones bloqueadas ejecutadas. |
| FR-008 | [README](../../../README.md), [operación](../../../deploy/README.md), [quickstart](../quickstart.md), respaldo/restauración comprobados; guía HTTPS/secretos/zona documentada, [validación VPS pendiente](vps.md). |
| SC-001 | Instalación desde locks, build/Compose desde volumen nuevo, web y salud, migración y reinicio correctos. |
| SC-002 | Suite final: 40 pruebas backend pasan, cobertura 93%; concurrencia/rollback/calendario/cobertura con resultados conocidos. |
| SC-003 | Snapshot sintético restaurado con igualdad de filas completas, retención, 52 restricciones y head. [Restauración](restore.md). |
| SC-004 | `core`, `audit` y composición se importan y prueban sin importar notificaciones ni otros dominios. Revisión de importaciones realizada. |

Comandos ejecutados: `uv sync --locked --group dev`, `pytest --cov=ecs_ec`,
`alembic check`, `npm ci`, Vitest, `next build --webpack`, `tsc --noEmit`,
Compose build/up, navegador Chromium, reinicio de aplicación/DB y scripts de respaldo/restauración.
El workflow de CI quedó configurado; no se ha ejecutado un job remoto ni se ha publicado código.
No existe umbral de cobertura adicional especificado; calendario y UoW alcanzan 100%.

Se revisó documentación de todos los módulos/clases/funciones Python mediante AST,
componentes/configuraciones/pruebas frontend y scripts. Las interfaces y límites están
en [contratos implementados](../../../docs/platform.md). Los logs/SMTP no se usan como
evidencia funcional; no hay importaciones inversas a consumidores ni tablas ajenas.
Los fallos observados de herramientas y sus correcciones figuran en [investigación](../research.md).

Limitaciones: no se validaron VPS/HTTPS públicos, dominio, zona real, usabilidad con
personas, cuentas, mediciones, costos, PDF, correo ni observabilidad técnica. Esas capacidades
se incorporan por sus propietarios y no se acreditan con el scaffold. No se aplicó ningún
cambio constitucional ni se marcaron checklists de revisión por la implementación.

Hooks: `.specify/extensions.yml` ausente antes y después de implementar; no hay hooks que
despachar. El seguimiento permanece en [tasks.md](../tasks.md), con T022 sin completar.
