# Prerrequisitos observados de spec-001

**Actualización2026-11-02:** recepción/almacenamiento002 y el shell006 ya están
integrados; la evaluación anterior se conserva como registro histórico.
[Capacidades actuales y pendientes](increment-2026-11-02.md). El nuevo gate de002
es la evidencia de diagnósticos cruzados y su retirada real;007/003/008/personas/VPS
siguen pendientes según sus capacidades, sin trasladar su implementación a001.

Fecha: 2026-11-02. Base Git: `c9f336c14372b6fe8f82a0a66038f55c0fb1122a`;
árbol limpio al comenzar. Selección explícita `specs/001-visualizar-consumo-categorias`
con el script oficial `check-prerequisites.sh --json --require-tasks --include-tasks`.
No se ejecutaron tareas de otras specs ni se modificaron checklists.

| Capacidad / contrato | Revisión y ruta comprobadas | Resultado observado / límite |
| --- | --- | --- |
| Plataforma [009](../../009-fundaciones-plataforma/contracts/integrations.md) | Base Git indicada; `backend/src/ecs_ec/core/`, `audit/`, Alembic, manifiestos | 18 pruebas previas de integración core/audit aprobadas con PostgreSQL 18.3; regresión completa posterior aprobada. DB/UoW/reloj/eventos usados, no recreados. |
| Identidad [006](../../006-acceso-usuarios-rbac/contracts/http.md) | Misma base; `identity/`, componentes SessionProvider/SessionGuard, `frontend/src/lib/api/session.ts` | Pruebas de identidad incluidas en regresión completa aprobada. El permiso `consumption.read` y los dos permisos de configuración existen. No se acreditan rutas de consumo que aún no se montan. |
| Shell administrativo 006 | Páginas reales `/administracion/usuarios/` y `/administracion/historial/`, protegidas por SessionGuard | No existe el layout previsto `frontend/src/app/administration/layout.tsx`. Coordinar el montaje/navegación de T035 con 006; el formulario 001 permanece aislado. No crear un layout general nuevo desde 001. |
| Almacenamiento [002](../../002-registro-retencion-consumo/contracts/integrations.md) | No existen `consumption/reception.py`, `store.py`, tablas ni proveedor de MeasurementStore | Gate ausente. No hay aceptación durable, incorporación calculada, máximos históricos reales ni pruebas de carrera recepción/configuración. BoundsStore de T006 es un doble explícito del puerto, solo para verificar 001. |
| Recepción física [003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md) | Sin `acquisition/` ni receptor/perfil SFTP implementados | T056 pendiente. JSON de fixtures no acredita archivos PAS600 ni SFTP. |
| Emisión [007](../../007-observabilidad-externa/contracts/integrations.md) | Sin módulo `observability/` ni perfiles técnicos | T054/T056 pendientes; no crear emisor/visores en 001. |
| Correo [008](../../008-notificaciones-programables/contracts/integrations.md) | Sin módulo `notifications/` ni perfil Mailpit | Integración transversal T056 pendiente; no bloquea reglas puras ni configuración propia. |
| Personas / VPS | Sin participantes ni entorno VPS provistos | T059/T060 pendientes. No provisionar ni sustituir estas verificaciones por pruebas sintéticas. |

La infraestructura de prueba fue un contenedor dedicado `ecs-consumption-spec 001-test`
con la imagen PostgreSQL 18 fijada en Compose, puerto loopback 55449 y bases desechables
`ecs_consumption_test` y `ecs_consumption_bootstrap_test`. Credencial exclusivamente
sintética; no se usó la base de la aplicación. El contenedor de esta ejecución se elimina
al terminar. Reproducción en [quickstart](../quickstart.md).

Herramientas observadas: CPython 3.14.4, Node 24.22.0, npm 12.2.0,
PostgreSQL 18.3, tzdata 2026.6 y decimal.js 10.6.0 (MIT). Python sigue
`>=3.14,<3.15`; no se actualizaron las dependencias de plataforma.

Head inicial de Alembic: `identity_initial`. Migración generada/revisada de 001:
`backend/migrations/versions/cb63a76198be_consumption_catalog.py`, parent
`identity_initial`. Solo añade cinco tablas de contexto/catálogo/fuentes/configuración,
catálogo fijo y FK RESTRICT; no incluye tablas de 002. Upgrade desde cero y
`alembic check` comprobados; downgrade destructivo rechazado expresamente.

Se verificaron `.gitignore`/`.dockerignore`: Python, npm, build, cachés, secretos y
artefactos ya cubiertos. No hay configuración ESLint/Prettier, publicación npm, Terraform
ni Helm que requieran nuevos ignores. Se añadió excepción para `frontend/src/lib/`:
el patrón Python `lib/` ocultaba tanto los clientes nuevos como `identity.ts` y `session.ts`
preexistentes. Estos dos archivos se preservan sin cambios de comportamiento y quedan
visibles para su inclusión en Git; eran una dependencia local ausente del índice.
