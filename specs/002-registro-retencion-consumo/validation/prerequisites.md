# Prerrequisitos observados de 002

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
