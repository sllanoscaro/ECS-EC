# Prerrequisitos verificados de 007

Fecha: 2026-11-02. Inspección del checkout real; no acredita aceptación funcional.

| Propietario/capacidad | Evidencia en raíz | Estado para 007 |
| --- | --- | --- |
| 009 scaffold/lifecycle/reloj | `backend/src/ecs_ec/{main.py,core/lifecycle.py,core/clock.py}`; `compose.yaml`, `pyproject.toml`, `uv.lock` | Disponible; habilita emisor. `uv sync --locked` ejecutado correctamente antes de cambios. |
| 009 DB/auditoría | `backend/src/ecs_ec/{core/database.py,core/unit_of_work.py,audit/}` | Disponible; aislamiento transaccional requiere pruebas reales. |
| 001/002 catálogo, consultas, recepción durable, agregación/retirada | `backend/src/ecs_ec/consumption/`; contratos de ambas specs | Disponible; llamadas de instrumentación propias aún pendientes. |
| 003 publicación/receptor SFTP | contrato `../003-simulador-pas600-sftp/contracts/sftp-reception.md`; no existe `backend/src/ecs_ec/acquisition/` | Bloquea aceptación SFTP/correlación real, no emisor. No crear receptor desde007. |
| 004 costos | `backend/src/ecs_ec/costs/` | Disponible; llamadas de instrumentación propias pendientes. |
| 005 PDF | `backend/src/ecs_ec/reports/{ports.py,snapshots.py}` | Contrato/snapshot parcial; falta generación durable/render/descarga. Bloquea cobertura PDF real. |
| 006 identidad | `backend/src/ecs_ec/identity/` | Disponible; instrumentación propia pendiente. No ampliar roles funcionales con Programador. |
| Diagnóstico humano | No hay participantes/resultados | SC-008/T061 pendiente. |

Documentos propietarios: [009](../../009-fundaciones-plataforma/plan.md),
[001](../../001-visualizar-consumo-categorias/contracts/integrations.md),
[002](../../002-registro-retencion-consumo/contracts/integrations.md),
[003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md),
[004](../../004-costos-tarifa-bt43/contracts/integrations.md),
[005](../../005-generar-reportes-pdf/contracts/integrations.md),
[006](../../006-acceso-usuarios-rbac/contracts/integrations.md).

No se modifican tareas de otros propietarios ni checklists de revisión.
