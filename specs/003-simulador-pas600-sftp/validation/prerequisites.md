# Prerrequisitos de implementación 003

Revisión de disponibilidad actualizada el2026-11-03 mediante inspección de código.
La existencia del proveedor no acredita integración ni aceptación003.

| Propietario | Disponibilidad y límite |
| --- | --- |
| 009 | `backend/src/ecs_ec/core/{unit_of_work,clock,retention,lifecycle}.py`, auditoría, composición y migraciones disponibles. Integración003 aún pendiente. |
| 001 | Catálogo/configuración/validación y fachada `Consumption` en `consumption/queries.py`; router y UI en `frontend/src/app/consumption/page.tsx` disponibles. |
| 002 | `Reception.accept/read_attempt` en `reception.py`, `MeasurementStore` en `store.py` y `Consumption.query_aggregates/read_report_snapshot` en `queries.py` implementados. Hay consultas/cobertura con UoW/corte; falta comprobar su integración con receptor/exportador003 reales. |
| 006 | Identidad y permisos implementados; vistas de consumo disponibles para comprobación. La identidad SFTP sigue siendo técnica y diferente de la sesión web. |
| 007 | Existen `observability/{logging,tracing,lifecycle}.py`, emisor básico y perfil técnico. Instrumentación003 pendiente; semántica especial y continuación durable siguen en007:T037/T038, con [contrato007](../../007-observabilidad-externa/contracts/integrations.md). |

El backend `backend/src/ecs_ec/acquisition/` sigue ausente. La referencia independiente
003:T003 permanece diferida por decisión del usuario; conformidad documental y aceptación
que dependan de ella siguen pendientes. No se cambian tareas ni sus prerrequisitos.
Ningún módulo ajeno se implementa desde 003. Generación local es independiente de estas
integraciones. Recepción SFTP, concurrencia PostgreSQL, cobertura integrada y UI requieren
sus verificaciones reales; no se declaran realizadas aquí.

## Registro histórico: verificación003:T022 (2026-11-02)

La ausencia de proveedores descrita abajo corresponde al corte original y está superada
por la tabla vigente. Sus pruebas no se reejecutaron en esta actualización.

`Reception.accept`/`read_attempt` tienen implementación en
`backend/src/ecs_ec/consumption/reception.py`; `MeasurementStore.read_detail` recibe
UoW/corte en `store.py`. `HistoryQueries.query_aggregates` solo aparece como Protocol
en `backend/src/ecs_ec/consumption/ports.py`, sin implementación en `backend/src`.
`aggregates.py` es escritor de agregados, no proveedor de consultas/snapshot.
La fachada/consulta001 también sigue pendiente según arquitectura/hoja de ruta.
No se considera disponible el proveedor integral de cobertura requerido por el
exportador/aceptación003. Esta revisión no sustituye pruebas E2E ni certifica contratos
mediante dobles. Instrumentación007 sigue sin proveedor. T022 es revisión realizada;
las tareas de integración/aceptación dependientes permanecen pendientes.
