# Research: Fundaciones compartidas

Registro trasladado del diseño de 008 del 2026-11-01; no constituye una nueva verificación
de versiones ni prueba de ejecución. Referencia central: [arquitectura](../../docs/architecture.md).

## R1. Versiones reproducibles

**Decision**: Python 3.14 convencional con GIL, `fastapi==0.162.0` y uv; `.python-version`,
`pyproject.toml` y `uv.lock`, verificados con `uv sync --locked`. React 19.x/Next.js 16.x
con TypeScript, Node >=20.9 y npm con lockfile. Fijar parches e imágenes en implementación.

**Rationale**: FastAPI 0.162.0 está publicado y declara Python 3.14; uv lo soporta. Next.js
16 requiere Node >=20.9 y TypeScript >=5.1. Python y JavaScript necesitan lockfiles propios.
Los mínimos 18+/19+/16+ no se convierten en upgrades mayores automáticos.

**Alternatives considered**: Cambiar FastAPI sin necesidad, rangos sin lock o intentar
administrar npm mediante uv. La resolución real y los wheels se comprobarán al implementar.

**Sources**: [FastAPI 0.162.0](https://pypi.org/project/fastapi/0.162.0/),
[uv/Python](https://docs.astral.sh/uv/reference/policies/python/),
[lock/sync](https://docs.astral.sh/uv/concepts/projects/sync/),
[Next.js 16](https://nextjs.org/docs/app/guides/upgrading/version-16).

## R2. Next.js dentro del monolito

**Decision**: Build multietapa; Next `output: 'export'` genera `out/`, incorporado a la
imagen Python y servido por FastAPI junto con `/api/v1`. Datos privados llegan por API
autenticada; identificadores de reglas/entregas se seleccionan en query/estado cliente.

**Rationale**: Preserva una unidad de aplicación. La exportación no admite Server Actions,
SSR por solicitud, cookies de Next ni rutas dinámicas desconocidas al construir. Sesiones
y autorización corresponden a FastAPI; el HTML exportado no contiene datos privados.

**Alternatives considered**: Next SSR separado incumple la unidad actual; dos runtimes
en un contenedor añaden supervisión innecesaria. Sustituir Next contradice la elección.

**Sources**: [Export estático](https://nextjs.org/docs/app/guides/static-exports),
[StaticFiles FastAPI](https://fastapi.tiangolo.com/tutorial/static-files/),
[Docker multietapa](https://docs.docker.com/build/building/multi-stage/).

## R3. Compose y persistencia local/VPS

**Decision**: Aplicación/PostgreSQL 18, volumen `/var/lib/postgresql`, PGDATA
`/var/lib/postgresql/18/docker`, salud/migraciones antes de disponibilidad, VPS con HTTPS,
URL pública y secretos externos. Correo y telemetría no condicionan disponibilidad.

**Rationale**: Compose necesita comprobaciones de salud, no solo orden de contenedores.
Los perfiles de correo y observabilidad se incorporan en sus propias funcionalidades.

**Alternatives considered**: Requerir servicios remotos o la VPS para validar localmente.

**Sources**: [Compose y salud](https://docs.docker.com/compose/how-tos/startup-order/),
[imagen PG18](https://github.com/docker-library/docs/blob/master/postgres/README.md).

## R4. Resolución y verificación en implementación (2026-11-02)

Manifiestos/lockfiles fijan las versiones resueltas: CPython 3.14.4 convencional, uv 0.11.8,
FastAPI 0.162.0, SQLAlchemy 2.0.55/Psycopg 3.3.6, tzdata 2026.6; Node 24.22.0,
Next 16.4.3, React 19.3.1 y PostgreSQL 18.3. Los digests de imágenes se obtuvieron mediante
descarga real y se fijaron en Dockerfile/Compose. `uv sync --locked` y `npm ci` fueron ejecutados.

El segundo build Docker con Turbopack terminó con señal de segmentación. Se seleccionó
`next build --webpack` (opción comprobada en `next build --help`) y se verificó el build
local y de contenedor. Se mantiene Next y la exportación estática del diseño.

El bundle instalado de Playwright 1.64.1 no pudo arrancar por un SyntaxError en
`lib/transform/babelBundle.js`; se fijó 1.64.0 y se descargó Chromium para la suite real.
No se modificaron archivos de dependencias manualmente.

Las reglas horarias se cargan desde el wheel `tzdata` bloqueado, sin depender de la
versión de la base IANA del anfitrión. PostgreSQL 18 real acredita transacciones y
deduplicación concurrente. Resultados y límites en [aceptación](validation/acceptance.md).
