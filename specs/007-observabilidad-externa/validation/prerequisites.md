# Prerrequisitos verificados de 007

Disponibilidad revisada el2026-11-23 por inspección del checkout; no acredita nueva
aceptación funcional. Los comandos de2026-11-02 son evidencia histórica.

| Propietario/capacidad | Evidencia en raíz | Estado para 007 |
| --- | --- | --- |
| 009 scaffold/lifecycle/reloj | `backend/src/ecs_ec/{main.py,core/lifecycle.py,core/clock.py}`; `compose.yaml`, `pyproject.toml`, `uv.lock` | Disponible; habilita emisor. `uv sync --locked` ejecutado correctamente antes de cambios. |
| 009 DB/auditoría | `backend/src/ecs_ec/{core/database.py,core/unit_of_work.py,audit/}` | Disponible; aislamiento transaccional requiere pruebas reales. |
| 001/002 catálogo, consultas, recepción durable, agregación/retirada | `backend/src/ecs_ec/consumption/`; contratos de ambas specs | Disponible;001:T054 instrumentada y verificada.002:T065 completada con adaptador instalado y contexto durable; [evidencia002](../../002-registro-retencion-consumo/validation/telemetry.md). La cobertura transversal007 sigue pendiente. |
| 003 publicación/receptor SFTP | `backend/src/ecs_ec/acquisition/`, `tools/pas600_simulator/` y [evidencia003](../../003-simulador-pas600-sftp/validation/acceptance.md) | Disponibles con recepción001/002 real. 003:T072 completada con semántica/continuación durables; [evidencia003](../../003-simulador-pas600-sftp/validation/telemetry.md). Falta cobertura transversal007. No hay bloqueo por inexistencia del receptor. |
| 004 costos | `backend/src/ecs_ec/costs/` | Disponible; llamadas de instrumentación propias pendientes. |
| 005 PDF | `backend/src/ecs_ec/reports/{ports.py,snapshots.py}` | Contrato/snapshot parcial; falta generación durable/render/descarga. Bloquea cobertura PDF real. |
| 006 identidad | `backend/src/ecs_ec/identity/`, `identity/telemetry.py` y [evidencia006](../../006-acceso-usuarios-rbac/validation/observability.md) | Disponible;006:T082/T083 verificadas con emisor007. La matriz integral007 sigue pendiente. No ampliar roles funcionales con Programador. |
| Diagnóstico humano | No hay participantes/resultados | SC-008/T061 pendiente. |

Documentos propietarios: [009](../../009-fundaciones-plataforma/plan.md),
[001](../../001-visualizar-consumo-categorias/contracts/integrations.md),
[002](../../002-registro-retencion-consumo/contracts/integrations.md),
[003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md),
[004](../../004-costos-tarifa-bt43/contracts/integrations.md),
[005](../../005-generar-reportes-pdf/contracts/integrations.md),
[006](../../006-acceso-usuarios-rbac/contracts/integrations.md).

## Límite del emisor disponible

`backend/src/ecs_ec/observability/{logging,tracing,lifecycle}.py` existen y el módulo está
registrado desde `main.py`. `Telemetry.complete` admite únicamente `operation.completed`:
los terminales de recepción y admisión/resultado PDF aún requieren007:T037; continuación
durable requiere007:T038. Sus contratos/pruebas y prerrequisitos siguen en
[tareas007](../tasks.md) y [contrato de integración](../contracts/integrations.md).
Las tareas002:T065 y005:T062/T063 tienen evidencia en sus propietarios; no cierran automáticamente ninguna tarea007.

La matriz completa de acceso007 espera PDF005 real; el grafo permite preparar pruebas y
puertos comunes de US2 desde fundaciones sin declarar US1 aceptada. No se omiten los
prerrequisitos existentes de007:T037/T038; el incremento coordinado requiere concretarlos
antes de ejecutar esa ampliación.

No se modifican tareas de otros propietarios ni checklists de revisión.
