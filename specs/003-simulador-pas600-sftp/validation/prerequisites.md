# Prerrequisitos de implementación 003

Revisión de código local 2026-11-02. La existencia de interfaces no acredita aceptación.

| Propietario | Disponibilidad y límite |
| --- | --- |
| 009 | Existen `backend/src/ecs_ec/core/{unit_of_work,clock,retention,lifecycle}.py`, auditoría en `backend/src/ecs_ec/audit/`, composición y migraciones. La integración 003 todavía no se ha ejecutado. |
| 001 | Existen `backend/src/ecs_ec/consumption/{catalog_storage,configuration,validation}.py`; catálogo y validación reales. Fachada/UI de consulta integrada siguen pendientes según hoja de ruta. |
| 002 | `backend/src/ecs_ec/consumption/ports.py` define accept/read_attempt; `reception.py` implementa ID/entrada fija y consulta de resultados. `store.py` implementa lecturas de detalle. Consultas agregadas/cobertura compartiendo captura requieren proveedor completo; no se sustituyen por dobles para aceptación. |
| 006 | Identidad y permisos implementados; la comprobación de vistas espera fachada de consumo. No son necesarios para generación local. |
| 007 | No existe `backend/src/ecs_ec/observability/`; instrumentación propia pendiente de su proveedor. |

Ningún módulo ajeno se implementa desde 003. Generación local es independiente de estas
integraciones. Recepción SFTP, concurrencia PostgreSQL, cobertura integrada y UI requieren
sus verificaciones reales; no se declaran realizadas aquí.

## Verificación T022 (2026-11-02)

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
