# Implementation Plan: Análisis de costos eléctricos con tarifa BT4.3

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

**Contexto**: `004-costos-tarifa-bt43` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Spec-004 y decisión U1: construir el productor real de costos en su propia funcionalidad, antes de integrar eventos en 008. Este contexto no crea una rama ni cambia la funcionalidad activa.

## Summary

Implementar cálculo real BT4.3, desglose por ciclo, perfil versionado, boletas manuales, comparación e historial. Usar exclusivamente CAT-01 física asociada al suministro: el total calculado no sustituye esa base. Persistir resultados, limitaciones y evidencia suficiente para reproducirlos aunque caduque el detalle de origen.

`costs` pertenece al monolito y produce resultados y eventos durables `cost.failed`. El consumidor 008 se conecta después; no interviene en calcular o persistir. Reportes 005 recibe capturas por `Costs.read_snapshot`.

## Technical Context

**Language/Version**: CPython 3.14 convencional y TypeScript; mismos manifiestos/lockfiles del [arquitectura compartida](../../docs/architecture.md), sin proyectos separados.
**Primary Dependencies**: FastAPI 0.162.0, Pydantic 2, SQLAlchemy 2/Psycopg 3 asíncronos, Alembic; Decimal y zoneinfo de Python. React 19.x/Next.js 16.x con exportación estática. No requiere biblioteca financiera externa.
**Storage**: PostgreSQL 18, NUMERIC sin float, instantes UTC, zona IANA y JSONB tipado para capturas. Migración semántica `costs_004_initial`, enlazada al head existente al implementar, sin presuponer un número global libre.
**Testing**: pytest/HTTPX y PostgreSQL real para revisiones/transacciones; Vitest/Testing Library/Playwright para UI. Casos sintéticos conocidos y reloj interno controlable.
**Target Platform**: Aplicación Linux única con FastAPI y exportación Next; PostgreSQL dependiente, desarrollo Compose y VPS posterior.
**Project Type**: Módulo web interno del monolito, sin worker o servicio de costos independiente.
**Performance Goals**: No se inventa latencia ni volumen; registrar tamaños/duraciones de referencia. SC-006: nueve de diez tareas de interpretación sin ayuda en <=2 minutos.
**Constraints**: Solo BT4.3 y CLP inicial; fuentes, precios, impuestos, punta, vigencias y redondeo son parámetros versionados. Cada revisión del perfil contiene su calendario completo de segmentos; solo la última publicada visible al corte se selecciona para cálculos nuevos. Mes de demanda documentado y capturado por revisión de cálculo, sin inferencia por emisión/inicio/fin. Demanda de 15 minutos exactos, nunca reconstruida de medias horarias. Mínimo de 12 meses calendario. Ausencia impide declarar completo el cargo afectado.
**Scale/Scope**: Un edificio y suministro; al menos 12 meses de historia cuando exista. Operador/Administrador consultan; solo Administrador modifica tarifas/boletas o solicita recálculo con revisión, conforme a spec-006. Datos de prueba no son tarifas reales.

## Constitution Check

| Principio | Previo | Evidencia | Posterior |
| --- | --- | --- | --- |
| I. Propósito eléctrico | PASS | Costos del suministro y medición física de specs-001/002. | PASS |
| II. Monolito modular | PASS | Motor, servicios/repositorio internos; ningún requisito de SMTP ni consumidor 008. | PASS |
| III. Documentación integral | PASS | Documentar cada archivo y elemento propio, fórmulas, pruebas y scripts en el mismo cambio; guía reproducible. | PASS |
| IV. Integridad y trazabilidad | PASS | Decimal, origen medido, fechas, revisiones y capturas protegidas. | PASS |
| V. Visualización verificable | PASS | Gráfico/tabla usan la misma respuesta, unidades, bases tributarias y estados. | PASS |

Sin excepciones. Los PASS acreditan diseño, no ejecución.

## Project Structure

### Documentation

```text
specs/004-costos-tarifa-bt43/
  spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
  contracts/http.md, contracts/integrations.md, contracts/ui.md
```

### Source Code

```text
backend/src/ecs_ec/costs/
  models.py, schemas.py, money.py, demand.py, calendar.py, engine.py
  services.py, repository.py, comparison.py, snapshots.py, retention.py, api.py
backend/src/ecs_ec/audit/{models.py,events.py}
backend/migrations/versions/costs_004_initial.py
backend/tests/{unit,integration,contract}/costs/
frontend/src/app/costos/page.tsx
frontend/src/app/administracion/costos/page.tsx
frontend/src/components/costs/
frontend/src/lib/api/costs.ts
frontend/tests/{unit,e2e}/
```

**Structure Decision**: Reutilizar núcleo de configuración, identidad, unidad de trabajo, consumo y auditoría. Su ausencia es trabajo previo identificado; no equivale a aceptar una integración mediante dobles.

## Phase 0: Research

[research.md](research.md) resuelve aritmética, perfil tipado, aislamiento, demanda, retención y eventos. Las reglas financieras proceden de spec-004; no se asigna una distribuidora, precio o impuesto real. El perfil sintético tiene redondeo explícito. Las condiciones reales son entradas administrativas, no decisiones técnicas pendientes.

## Phase 1: Design & Contracts

### Flujo real y reproducción

1. Autorizar contra identidad actual. Consulta ordinaria no crea revisiones; recálculo explícito administrativo sí.
2. Capturar en REPEATABLE READ y corte único las revisiones de CAT-01 física, suministro, perfil/calendario completo con segmentos, bloques/máximos históricos y boleta cuando corresponda. Resolver y capturar mes de demanda, fuente y versión de política; sin resolución inequívoca limitar los cargos dependientes. Preservar valores y referencias necesarios, no únicamente enlaces a datos que caducan.
3. Evaluar motor puro Decimal. Catálogo de reglas cerrado y tipado: energía, fijo, potencia, impuestos/condiciones documentadas; no ejecutar expresiones de usuario.
4. Separar estado temporal (`en_curso`/`cerrado`), suficiencia (`completo`/`parcial`/`no_calculable`) y ejecución (`completado`/`fallido`). Cada cargo informa resultado o limitación; una suma parcial no es total BT4.3 completo.
5. Persistir revisión, componentes, captura y auditoría. Hash de entradas y versión del motor permiten reproducir; operación idempotente no duplica revisión, revisión administrativa explícita preserva anterior.
6. Fallo funcional inesperado: guardar resultado `fallido` saneado y `cost.failed` juntos en una transacción válida. Tras rollback del cálculo, usar nueva unidad de trabajo para ambos; nunca publicar desde una transacción revertida. Si la base falla, no afirmar durabilidad. Insuficiencia prevista produce parcial/no calculable, no fallo técnico.
7. Comparar solo suministro/ciclo/moneda/concepto/base tributaria alineados y revisiones seleccionadas explícitamente; exclusiones y créditos conservan sus signos. Nunca ajustar mediciones o tarifas para igualar boletas. Los formularios administrativos de cálculo/recálculo (US1) y comparación (US2) confirman sus POST, conservan entradas ante error y no duplican operaciones reintentadas; las consultas solo leen resultados persistidos.
8. `Costs.read_snapshot` entrega a 005 últimas revisiones a corte de ciclos cerrados cuyo fin efectivo cae en `[start,end)`: seleccionar cálculo y revisión de boleta primero, después comparación de ese par exacto. Sin ella, `missing_for_selected_revisions`, diferencias null y ciclo fuera del contraste agregado; mantener importes disponibles y comparación histórica, sin retroceder versiones ni generar comparaciones durante la lectura.

### Calendario de perfil, suministro y edición concurrente

El perfil tiene revisiones inmutables, cada una con todo su calendario de segmentos [inicio,fin), sin solapamientos internos. Cerrar una vigencia abierta o corregir el pasado crea otra revisión completa; la coincidencia de fechas entre revisiones históricas es válida. Elegir la última publicada visible al corte; no mezclar segmentos de revisiones distintas. Un borrador guardado no cambia esa selección y publicarlo requiere otra revisión. `expected_previous_version_id` (null inicial) se compara bajo bloqueo del suministro con la última revisión guardada, incluidos borradores; un conflicto devuelve 409. Registrar revisión/anterior/auditoría en una sola UoW. GET perfiles distingue última guardada y publicada seleccionada.

GET suministro, solo administrativo, devuelve configuración/id/revisión/ETag o 404. PUT inicial exige `If-None-Match: *` (201; existente 412); modificar exige `If-Match` vigente (200; antiguo 412); sin precondición 428. El editor conserva entradas ante conflicto y exige revisar el estado actual. La lectura mínima del suministro se incorpora en US1 para su formulario; US3 completa alta/edición y editor. Los cálculos capturan sus datos/revisión para que editarlo no altere evidencia previa.

La política mensual del perfil permite regla documentada soportada o evidencia explícita validada. El servidor valida formato, pertenencia de la referencia documental al suministro/ciclo/mes y compatibilidad con la política registrada; no interpreta automáticamente documentos. La captura conserva `billing_month_ref`, `billing_month_source_ref` y `billing_month_policy_version`. Corregirlos crea otra revisión del cálculo. El caso sintético de [quickstart.md](quickstart.md) fija ventana/mes/resultado sin asignar una política normativa al suministro real.

### Interfaces y dependencias

- [data-model.md](data-model.md): entidades, restricciones, estados, fórmulas y conservación.
- [contracts/http.md](contracts/http.md): operaciones, cuerpos, filtros y errores.
- [contracts/integrations.md](contracts/integrations.md): puertos y evento de fallo.
- [contracts/ui.md](contracts/ui.md): consulta y administración.
- [quickstart.md](quickstart.md): escenarios reproducibles por historia.

Prerequisitos: configuración/PostgreSQL/migraciones, identidad real de spec-006, fuentes físicas reales de specs-001/002 y auditoría durable. Reutilizar plataforma009 para core/auditoría y las capacidades propias de 001/002/006 sin requerir scheduler, evaluación de alertas ni SMTP: la dependencia va al núcleo, no a la aceptación de 008. `cost.failed` pertenece a `audit/models.py` y `audit/events.py`; costos no importa `notifications`.

### Entregables U1 y cobertura

| Entregable | Aceptación |
| --- | --- |
| Motor real | 1000×100=100000 CLP; 10 kWh/0,25 h=40 kW; bases 55/25 kW con datos conocidos. |
| Persistencia | Resultado legible tras reinicio, captura reproducible sin detalle original. |
| Fallo funcional | Resultado fallido y `cost.failed` atómicos; rollback de registro no deja ninguno. |
| Puerto 005 | Ciclos cerrados/revisiones a corte, comparación del par exacto o pendiente con diferencias null, sin prorrateo. |
| Conexión 008 | La tarea de integración de eventos de 008 conecta resultados ya existentes después; productor 004 funciona sin consumidor. |

FR-001..014: US1/fundamentos de perfil; FR-015..019: US2/US3; FR-020..023: US4 y conservación. SC-001..006 tienen validaciones asignadas en tareas.

## Complexity Tracking

Sin desviaciones constitucionales. Capturas inmutables y estados separados conservan reproducción y limitaciones. No se añade un lenguaje de fórmulas, pagos ni proveedor tarifario automático.
