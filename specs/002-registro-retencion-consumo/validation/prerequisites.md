# Prerrequisitos observados de 002

## Disponibilidad vigente — 2026-11-03

Inspección de código y contraste con la [aceptación local](acceptance.md), sin nueva
validación funcional ni cambios de tareas.

| Capacidad / propietario | Disponibilidad actual y límite |
| --- | --- |
| Plataforma009 / identidad006 | DB/UoW/reloj/auditoría, sesiones y permisos disponibles e integrados localmente. |
| Fachada/UI001 y proveedores002 | `consumption/{queries,schemas,router,store}.py`, página `frontend/src/app/consumption/page.tsx` y componentes existentes. `Consumption.query_aggregates`, snapshots, `FunctionalSummary` y retirada protegida disponibles.002:T024/T025 y US2–US4 tienen evidencia local; no existe bloqueo por ausencia de fachada. |
| Adquisición003 | Falta `backend/src/ecs_ec/acquisition/`;002:T064 sigue pendiente de adaptador/publicación SFTP reales, recuperación del mismo intento y reenvío con ID nuevo. |
| Emisión007 | Existen `observability/{logging,tracing,lifecycle}.py` y emisor registrado en `main.py`.002:T065 sigue pendiente: faltan llamadas propias y semántica común de recepción/continuación durable (007:T037/T038). `Telemetry.complete` admite solo `operation.completed`, no `reception.completed`; no basta con conectar el emisor básico. |
| Consumidores004/005/008 | Costos004 implementado localmente con `Costs.read_snapshot`;005 tiene puertos y captura parcial en `reports/{ports,snapshots}.py`, sin generación/descarga;008 sigue sin módulo. Disponibilidad de productores002 no acredita aceptación conjunta de consumidores. |
| Personas / VPS |002:T068/SC-005 sigue pendiente de personas. La verificación externa no se acredita por pruebas locales. |

Propiedad del emisor y sus ampliaciones: [contrato007](../../007-observabilidad-externa/contracts/integrations.md)
y [tareas007](../../007-observabilidad-externa/tasks.md). No se implementan desde002.

## Registro histórico — 2026-11-02

La información siguiente corresponde a sus cortes originales; para disponibilidad actual
prevalece la actualización anterior. No se reejecutaron sus pruebas en esta revisión.

Fecha: 2026-11-02. Base: `cb5134494bd9032ab50bd47f085b052518e04bbb`;
árbol limpio al inicio. Checklist requirements: 16/16, sin modificar marcadores.
Selección explícita mediante `SPECIFY_FEATURE_DIRECTORY=specs/002-registro-retencion-consumo`.

| Capacidad / propietario | Ruta real / resultado |
| --- | --- |
| Plataforma [009](../../009-fundaciones-plataforma/contracts/integrations.md) | `backend/src/ecs_ec/core/{database,unit_of_work,clock,retention,lifecycle}.py`, `audit/`, composición `main.py` presentes. UoW sin commit oculto, READ COMMITTED para escritura; REPEATABLE READ para capturas. |
| Dominio [001](../../001-visualizar-consumo-categorias/contracts/integrations.md) | `consumption/{catalog_storage,configuration,validation,totals,models,ports}.py` reales. `lock_configuration`: contexto → categorías ordenadas, READ COMMITTED. Bounds debe incluir exactamente claves solicitadas, nunca confundir error con null. |
| Identidad [006](../../006-acceso-usuarios-rbac/contracts/http.md) | `identity/` y sesión/permisos frontend implementados. |
| Fachada/UI [001](../../001-visualizar-consumo-categorias/tasks.md) | Faltan `consumption/{queries,schemas,router}.py`, `ConsumptionView.tsx` y `frontend/src/app/consumption/page.tsx`. Gate de integración de proveedores T024/T025 y aceptación web US2. No se implementan tareas de 001 desde 002. Router único acordado: `backend/src/ecs_ec/consumption/router.py`. |
| Adquisición [003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md) | Sin adaptador `acquisition/` real. Pruebas internas llaman Reception; no acreditan SFTP. El contrato 003 conserva attempt_id/entrada antes de invocar 002; recuperación mismo ID, reenvío ID nuevo. |
| Emisión [007](../../007-observabilidad-externa/contracts/integrations.md) | Sin `observability/`: T065 pendiente. |
| Consumidores [004](../../004-costos-tarifa-bt43/contracts/integrations.md)/[005](../../005-generar-reportes-pdf/contracts/integrations.md)/[008](../../008-notificaciones-programables/contracts/integrations.md) | Sin módulos reales; no se crean desde 002 ni se acredita aceptación conjunta con dobles. |
| Personas/VPS | No provistos; SC-005 y verificación externa pendientes. |

PostgreSQL dedicado: contenedor `ecs-spec002-test`, imagen/digest fijado por Compose,
18.3, puerto loopback 55450, base desechable `ecs_history_test`, credencial sintética.
No usa la DB de aplicación. `btree_gist` creada exitosamente con el rol de migración.
Head inicial Alembic `cb63a76198be`; migración 002 se enlaza a ese head.
CPython 3.14.4, Node 24.22.0, npm 12.2.0. `tzdata==2026.6` y `decimal.js==10.6.0`
ya fijados en manifiestos/locks. No se actualizan versiones compartidas.

Los ignores existentes cubren Python/npm, build, caches, secretos y editores.
Sin ESLint/Prettier, publicación npm (private:true), Terraform ni Helm.

Coordinación: intento exclusivo en conexión dedicada antes de adquirir contexto/categorías;
locks PostgreSQL recuperables tras caída, sin locks Python. Escritura por categoría en
UoW independiente; resultados y eventos se confirman con sus registros/agregados.
Entrada canónica completa antes de resultados; publicación no es intento.

## Capacidades instaladas por este incremento

Migración real: `backend/migrations/versions/47457bdabdfa_consumption_002_initial.py`,
parent `cb63a76198be`; upgrade nuevo y con configuración001 previa verificados, junto
con `alembic check`. Son 12 entidades y una relación auxiliar de FK para referencias
calculadas. La extensión se habilita en la propia migración, sin eliminarla al revertir.

Proveedores: `store.MeasurementStore`, `reception.Reception`,
`pending_totals.PendingTotals`; `main.create_app` registra el módulo
`consumption-history`, expone `app.state.consumption_store`, `app.state.consumption_reception` y
`app.state.consumption_pending_totals` y recibe `consumption_bindings`.
Mapa por proceso→UUID de edificio; vacío por defecto. No concede permisos desde el payload.
El coordinador reutiliza la misma conexión con lock de sesión entre commits por
categoría, sin pedir una segunda conexión al pool; cancelación/fallo de unlock invalida
la conexión. El worker recupera solicitudes/candidatos en el lifespan común.

La fachada/UI001 siguen ausentes; existen contratos de salida agrupada/consumidores,
no implementaciones de esas consultas. T024/T025 y el gate US2 permanecen pendientes.

## Continuación 2026-11-02

La fachada/router/página001 ya existen y se reutilizaron. T024/T025 y US2–US4 se
integraron con `Consumption`, `MeasurementStore`, identidad006 y el registro009 reales.
El proveedor `FunctionalSummary`002 se compone como `app.state.consumption_summary`;
su `read` exige permisos actuales y UoW/corte del llamador. Cuenta actualizaciones de
categoría mediante eventos transaccionales ligados a su edificio; antes del registro o
después del corte informa huecos; contenido ajeno devuelve desconocida/null.

Siguen faltando adaptador de publicaciones/SFTP003 en `backend/src/ecs_ec/acquisition/`
([contrato003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md)) y emisor007 en
`backend/src/ecs_ec/observability/` ([plan007](../../007-observabilidad-externa/plan.md)).
No se implementaron como prerrequisitos. T064/T065 pendientes; SC-005/T068 sin personas.
Los contratos productores004/005/008 están probados; aceptación conjunta no ejecutada.
