# Aceptación local de spec-002, pendiente de integraciones y personas

**Actualización:** 2026-11-02. **Base Git:** `b30afe6408f6178b89b0d5483229e284c741d023`. **Estado:**68/71 tareas completas;43 tareas adicionales
respecto del incremento inicial. T001–T063/T066–T067/T069–T071 completas;
T064/T065/T068 pendientes. No se modificaron checklists de revisión ni tareas001/004.
Se preservaron los cambios previos de004. No hay commit ni despliegue VPS en esta sesión.

## Resultado vigente

Se reutilizó001 para catálogo/configuración/detalle, router, página y componentes;
009 para UoW/reloj/aniversarios/auditoría y006 para sesiones/permisos/CSRF.
002 añade consulta agrupada, proveedores de consumidores, resumen funcional, protección/
retirada de detalle y presentación de estados/tardíos. No crea módulos ajenos.

| Verificación final | Resultado |
| --- | --- |
| `uv run pytest backend/tests --cov=ecs_ec.consumption --cov-report=term-missing -q` |319 aprobadas,47.83s;96% de cobertura de consumo. Ninguna xfail pendiente. |
| `npm --prefix frontend test -- --run --maxWorkers=1 --no-file-parallelism` |47 aprobadas,20 archivos,15.60s. |
| TypeScript / build estático |Ambos aprobados; páginas de consumo exportadas, datos privados solo por API. |
| Playwright físico, ambos perfiles |2/2; siete categorías/cuatro agrupaciones con datos, API/gráfico/tabla; después de reiniciar Uvicorn/PostgreSQL vuelve a pasar2/2 en9.6s. |
| Playwright calculado, ambos perfiles |2/2 en11.1s; base12+8=20 y ausencias, cero/quantum, consulta y permisos. |
| Playwright estados/retirada |1/1 en6.8s; dato tardío, cobertura, respuesta A demorada/error/reintento, fronteras exactas, sesión expirada y retirada por servicio real. |
| Alembic check |Sin nuevas operaciones; no se necesitó migración ni cambio de dependencias/locks. |
| Documentación / `git diff --check` |Docstrings de código Python propio revisados; TSDoc de componentes/cliente/harness. Comprobación de espacios/enlaces realizada. |

PostgreSQL18.3 del digest Compose, contenedor desechable `ecs-spec002-continuation`,
loopback55450. Bases separadas `ecs_history_test`, `ecs_history_browser_test`,
`ecs_history_physical2_test` y `ecs_history_calculated_test`, nunca la de aplicación.
CPython3.14.4, Node24.22.0, npm12.2.0, tzdata2026.6; locks conservados.
Relojes FrozenClock y harness ISO0600 privados; no se cambió la hora del host.
Al finalizar se retiraron contenedor/volumen y archivos temporales de prueba.

## Trazabilidad y límites

| Requisitos | Evidencia / estado |
| --- | --- |
| FR-001..006, SC-001 |[Recepción](reception.md): núcleo previo más T024/T025, proveedores/fachada/resumen y diagnóstico cruzado reales. |
| FR-007..013, SC-002 |[Agregaciones](aggregates.md): cuatro niveles exactos y consulta/UI con identidad real. |
| FR-014/FR-010..014/019, SC-003 |[Estados/tardíos](incomplete-history.md): actualización sincrónica, selección/captura común, cero/hueco/error y fronteras. |
| FR-015..019, SC-004 |[Conservación](retention.md):13 meses/siete categorías, aniversarios, dependientes y retirada real preservando agregados/reenvíos. |
| SC-005 |Pendiente de participantes reales: T068. No se acredita con Playwright. |
| Integraciones nativas |T064 espera adaptador003 real y T065 emisor007. Proveedores para004/005/008 probados; aceptación conjunta pendiente de consumidores. |
| Instalación |Zona/fuentes reales y VPS sin verificar; America/Santiago es fixture. |

Las pruebas nuevas de resumen, consulta, HTTP, consumidores, selector y retirada se
observaron fallar por capacidades ausentes antes de añadirlas. Otras regresiones se
ampliaron después del montaje: no se afirma TDD integral de todos los escenarios.
Primeros intentos E2E fallaron por invocación desde cwd incorrecto y localizador de
etiqueta; se corrigió el harness. El reloj servidor congelado inicialmente no coincidía
con Date del navegador y provocó revalidaciones repetidas: el harness alinea ambos,
sin cambiar identidad para ocultarlo. Las ejecuciones finales arriba pasaron.

Selección persistida activa: `specs/002-registro-retencion-consumo`.
No existe `.specify/extensions.yml`: comprobados hooks previos y posteriores, sin hooks
que ejecutar. Checklist requirements16/16 se mantuvo intacto. Esta evidencia sustituye
los gates obsoletos del registro inicial conservado a continuación como historia.

---

# Registro histórico del incremento inicial

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
