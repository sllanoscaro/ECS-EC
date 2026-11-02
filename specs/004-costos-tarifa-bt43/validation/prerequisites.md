# Prerrequisitos de implementación 004

## Continuación sobre base23c26d0 (2026-11-02)

El bloqueo registrado más abajo es histórico y está resuelto: `Consumption.read_general_snapshot`
y `read_demand_history` tienen implementación real en `backend/src/ecs_ec/consumption/queries.py`.
Se ejecutaron sus cuatro contratos reales002 con PostgreSQL18.3 sobre base desechable
`ecs_costs_test`, contenedor `ecs-spec004-test`, loopback55452. Calculada→limitación explícita;
horaria→resolución insuficiente para demanda. Identidad006, reloj y escritores009 disponibles.

T001–T009 incorporan paquete/páginas iniciales, fixtures reales, Decimal textual/quantum,
perfiles completos inmutables, selección publicada/idempotencia y esquema propio. Migración
`backend/migrations/versions/costs_004_initial.py`, parent real `47457bdabdfa`; no se duplicó
auditoría. Checklist16/16 sin modificar; sin hooks registrados. Se preservan los cambios
previos de estos documentos. No se actualizaron dependencias/locks ni capacidades ajenas.

El registro siguiente conserva la evaluación anterior, no la disponibilidad actual.

**Fecha:** 2026-11-02. **Base Git:** `0ef2f9bdfb45e8617f4b17b2ff521fa0a97ec679`.
**Resultado:** ejecución detenida en T001; T002–T067 no iniciadas.
La verificación documental se realizó, pero T001 permanece pendiente porque requiere
capacidades reales aún ausentes. No se acredita implementación ni aceptación de costos.

## Comprobaciones iniciales

- Script oficial ejecutado con `SPECIFY_FEATURE_DIRECTORY=specs/004-costos-tarifa-bt43`
  y `SPECIFY_FEATURE_NO_PERSIST=1`, argumentos `--json --require-tasks --include-tasks`.
  Devuelve el directorio absoluto correcto y research, modelo, contratos, quickstart y tareas.
- Checklist `requirements.md`: 16 criterios completos, 0 pendientes; sin modificar marcas.
- Leídas la arquitectura, hoja de ruta, constitución, planificación y contratos de integración.
- El árbol tenía una modificación previa en `docs/implementation-roadmap.md` relativa a
  spec-003; se preservó. No se cambió `.specify/feature.json`.
- No existe `.specify/extensions.yml`: no hay hooks previos o posteriores registrados.

## Matriz de disponibilidad

La revisión es estática del código disponible; no sustituye pruebas transaccionales de
integración ni una ejecución sobre PostgreSQL para spec-004.

| Capacidad y propietario | Evidencia real | Resultado para T001 |
| --- | --- | --- |
| DB/UoW y reloj — spec-009 | `backend/src/ecs_ec/core/database.py`, `unit_of_work.py` y `clock.py`: sesiones asíncronas, commit explícito, rollback y reloj inyectable. | Implementación disponible; integración de costos pendiente. |
| Autorización — spec-006 | `backend/src/ecs_ec/identity/services.py`: `Identity.authorize`; `permissions.py`: `costs.read`, configuración, boletas, cálculos y comparaciones; denegación por defecto. | Implementación disponible; integración de costos pendiente. |
| Auditoría/eventos — spec-009 | `backend/src/ecs_ec/audit/services.py`: `FunctionalAudit.append`; `events.py`: `EventWriter.append` en la UoW del productor; `models.py`: unicidad `uq_event_provenance`. Tablas comunes creadas por `backend/migrations/versions/platform_009_initial.py`. | Implementación disponible, sin dependencia de 008; esquemas propios y atomicidad de costos aún no implementados. |
| CAT-01 física a corte — spec-002, sobre configuración spec-001 | `backend/src/ecs_ec/consumption/ports.py` declara `HistoryQueries.read_general_snapshot` y `PhysicalHistorySnapshot`. La búsqueda en `backend/src/ecs_ec/consumption/` solo encuentra la declaración con cuerpo `...`; no existe `backend/src/ecs_ec/consumption/queries.py`. | **Bloqueo:** falta proveedor concreto con procedencia, revisión, cobertura y limitación ante CAT-01 calculada. |
| Historia para demanda — spec-002 | `HistoryQueries.read_demand_history` en el mismo `ports.py` es solo un protocolo con cuerpo `...`, sin implementación en `backend/src`. | **Bloqueo:** falta captura física que demuestre resolución exacta para bloques de 15 minutos y conserve evidencia/cobertura al corte. |
| Almacenamiento y composición de consumo — specs-001/002 | `backend/src/ecs_ec/consumption/store.py` implementa detalle, extensión, estado y límites de reconfiguración. `backend/src/ecs_ec/main.py` compone almacenamiento, recepción y recuperación, pero no los dos proveedores anteriores. | El almacenamiento disponible no acredita los contratos completos requeridos por costos. |

Head de migraciones inspeccionado: `47457bdabdfa`, padre `cb63a76198be`, precedido
por `identity_initial` y `platform_009_initial`. No se creó ni ejecutó migración de costos.

## Responsables y condiciones para reanudar

1. **Spec-002:** implementar `Consumption.read_general_snapshot` y
   `Consumption.read_demand_history` sobre el almacenamiento existente, con UoW/corte
   compartidos, configuración histórica, CAT-01 física, cobertura y resolución demostradas.
   Capacidad asignada expresamente a **T042 de spec-002**, en su
   [archivo de tareas](../../002-registro-retencion-consumo/tasks.md).
2. **Specs-001/002:** completar la fachada y su inyección real en
   `backend/src/ecs_ec/consumption/queries.py`. La consulta de detalle corresponde a
   **T026 de spec-001**, en sus [tareas](../../001-visualizar-consumo-categorias/tasks.md);
   la inyección del almacenamiento está pendiente en **T024 de spec-002**.
   No se exige aceptación completa de esas specs: sí los proveedores necesarios y sus
   pruebas reales. Sus estados parciales están documentados en
   [aceptación 001](../../001-visualizar-consumo-categorias/validation/acceptance.md) y
   [aceptación 002](../../002-registro-retencion-consumo/validation/acceptance.md).
3. **Spec-004:** repetir T001 contra los proveedores concretos antes de T002, verificando
   una captura física y el rechazo explícito de sustitución por CAT-01 calculada; continuar
   después con fixtures y pruebas PostgreSQL reales previstas en la planificación.

La detención sigue [T001 y su prerrequisito para T002](../tasks.md), el contrato de
[integraciones](../contracts/integrations.md) y [AGENTS.md](../../../AGENTS.md):
«No implementar una capacidad ajena como parte de los prerrequisitos de la funcionalidad activa».
No se implementaron capacidades de 001/002 dentro de costos ni se aceptaron dobles como
integración. No se requiere completar notificaciones, scheduler o SMTP para desbloquear T001.

## Validación de esta ejecución

Solo inspección de código, contratos, tareas y estado Git; no se ejecutaron suites
funcionales ni se produjeron cálculos BT4.3. Las 67 tareas permanecen sin completar.
La evidencia de prerrequisitos es parcial respecto de T001 y no cambia los checklists.
