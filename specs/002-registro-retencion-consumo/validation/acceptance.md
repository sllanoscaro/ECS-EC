# Aceptación parcial de spec-002

**Fecha:** 2026-11-02. **Base Git:** `cb5134494bd9032ab50bd47f085b052518e04bbb`;
árbol limpio al comenzar, cambios actuales sin commit. **Estado:** 25/71 tareas
completadas; fundaciones y recepción/recuperación internas verificadas. La spec y el
checkpoint integral US1 **no están completos**. No se modificaron checklists de revisión.

[Prerrequisitos y gates](prerequisites.md), [recepción](reception.md),
[revisión documental del incremento](documentation.md), [tareas](../tasks.md).

## Comandos y resultados observados

DB desechable `ecs_history_test`, contenedor `ecs-spec002-test`, loopback 55450,
PostgreSQL 18.3 con imagen/digest Compose. Otra DB `ecs_history_upgrade_test` comprobó
upgrade sobre contexto/fuentes/configuración 001 reales. Nunca se usó la DB de aplicación.
CPython 3.14.4, Node 24.22.0, npm 12.2.0, tzdata 2026.6 y decimal.js 10.6.0, sin actualizar locks.
Reloj FrozenClock y zonas sintéticas; no se alteró el reloj del host.
Al finalizar se retiró `ecs-spec002-test` con sus volúmenes y las dos DB desechables.

| Comando / comprobación | Resultado |
| --- | --- |
| Script oficial de prerrequisitos con selección explícita 002 | FEATURE_DIR absoluto correcto; requirements16/16; sin hooks registrados. |
| `uv run pytest backend/tests/unit/consumption backend/tests/contract/consumption backend/tests/integration/consumption --no-cov -q` | 115/115 antes de añadir cuatro regresiones finales de retención inicial/arranque/base vacía. Incluidas después en la regresión completa. |
| `uv run pytest backend/tests --cov=ecs_ec.consumption --cov-report=term-missing -q` | **261/261**, 44.87s; cobertura del módulo consumption **96%**, sin umbral inventado. |
| `npm --prefix frontend test -- --run --maxWorkers=1 --no-file-parallelism` | **30/30**,15 archivos, 13.65s. Regresión de componentes existentes; sin aceptación de UI agrupada. |
| `npm --prefix frontend run typecheck` | Aprobado. |
| `npm --prefix frontend run build` | Export estático aprobado. No existe aún ruta `/consumption/`; no se declara construida. |
| `alembic ... upgrade head` en DB nueva | Aprobado; head002 `47457bdabdfa`, parent `cb63a76198be`; 13 tablas propias contando relación auxiliar de referencias. |
| Upgrade desde parent con configuración 001 existente | Preserva revisión/fuentes; crea 7 estados vacíos, historia false y 0 mediciones; no fabrica aceptaciones. |
| `uv run alembic -c backend/alembic.ini check` en ambas DB | Sin nuevas operaciones; metadatos y migración coinciden. |
| Revisión documental AST y manual |26 archivos Python/231 símbolos/cero docstrings ausentes; límites descritos en revisión documental. |
| `git diff --check` | Aprobado. |

El primer lanzamiento Vitest con workers paralelos terminó con SIGSEGV de un worker
(28 pruebas observadas aprobadas, ejecución inválida). La repetición con un worker pasó.
La primera regresión backend, simultánea con ese lanzamiento, tuvo dos fallos de identidad
(preauth concurrente y prompts TTY). Ambos pasaron aislados (2/2,4.51s); la regresión
completa posterior pasó 261/261. No se modificó identidad para ocultar esos resultados.
Los tiempos son observaciones de este entorno, no SLO.

## Trazabilidad y alcance de aceptación

| Requisitos / criterio | Estado / evidencia |
| --- | --- |
| FR-001..006 / SC-001 | Núcleo interno verificado en PostgreSQL: siete categorías,899/900s, originales/duplicados/conflictos, independencia y concurrencia. Falta completar T024/T025 para checkpoint US1. |
| FR-007..010 | Escritura exacta de cuatro niveles y calendario verificada como fundación. Consulta/API/gráfico/tabla de US2 pendientes; no aceptación completa de estos FR. |
| FR-011..013 / SC-002/003 | Contratos de DTO y duraciones/calendario comprobados. Proyección/API/UI y recorridos completos pendientes. |
| FR-014 | Commit de parciales/solicitud recuperable/agregados, rollback del resultado y recuperación sin reenvío verificados. Presentación tras commit en ambas vistas pendiente. |
| FR-015..017 | Fechas iniciales/aniversario y extensión no decreciente de agregados verificadas como fundación. Consulta protegida completa/política US3 pendientes. |
| FR-018..019 / SC-004 | Ledger permanente y separación de detalle preparados; fixtures de91 lecturas/trece meses/siete categorías. Retirada real/protecciones completas/consulta web pendientes; el fixture no acredita SC-004. |
| SC-005 | Pendiente de personas representativas; no se sustituyó por pruebas automáticas. |
| SFTP003, emisor007, consumidores004/005/008 | No disponibles ni implementados desde002; aceptación conjunta pendiente. |
| VPS / fuentes / zona reales | No provistos ni acreditados por pruebas locales. |

## Estado de tareas y siguiente gate

Completadas **T001–T023, T026 y T027** de esta spec. Cada marca corresponde a código,
pruebas o comprobación real; sus detalles están en recepción/prerrequisitos.

T024: los cuatro métodos de almacenamiento están implementados; falta inyección en
fachada001 `backend/src/ecs_ec/consumption/queries.py`, aún ausente.
T025: eventos009 transaccionales implementados; falta el proveedor de resumen/cobertura
funcional y su composición. Ambas tareas permanecen sin marcar.

US2 requiere fachada/router/página integrada001 reales para aceptación web. Faltan
`consumption/{queries,schemas,router}.py`, `ConsumptionView.tsx` y
`frontend/src/app/consumption/page.tsx` de001. Según AGENTS y la hoja de ruta,002 no
implementa capacidades ajenas como prerrequisitos. US2–US4 y sus checkpoints siguen
pendientes según el orden de la planificación; no se añadieron páginas paralelas.

El cierre T064–T071 conserva gates propios:003/007/personas y validación integral.
La revisión documental y los comandos de este incremento aportan evidencia parcial,
sin marcar tareas de cierre como si toda la spec estuviese implementada.
