# Quickstart: Validación de plataforma común

Guía de la base009, cuya validación no requiere cuentas, SMTP ni visores. El proyecto
ya incorpora identidad006, consumo001/002, recepción003, costos004, PDF005,
observabilidad007 y notificaciones008. Sus procedimientos y aceptación pertenecen a
cada funcionalidad; los perfiles de correo y observabilidad son opcionales. [Plan](plan.md), [tareas](tasks.md),
[arquitectura](../../docs/architecture.md), [operación](../../deploy/README.md).

Desde la raíz, con Docker Compose, uv 0.11.8 y Node >=20.9 (probado: 24.22.0):

```sh
cp .env.example .env
uv sync --locked --group dev
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
docker compose build app
docker compose up -d --wait app
curl --fail http://localhost:8000/api/v1/health/ready
curl --fail http://localhost:8000/
```

Compose aplica Alembic antes de habilitar la aplicación. Migración explícita:

```sh
docker compose up -d --wait db
docker compose run --rm migrate
```

La configuración de `.env.example` es sintética local. Compose usa `db` como host interno;
fuera del contenedor usa `DATABASE_URL` del anfitrión. URL pública y zona son configuración
de runtime y no se incrustan en Next.

## Pruebas reproducibles

Crear una sola vez una base independiente cuyo nombre termine en `_test`:

```sh
docker compose exec db createdb -U ecs_local ecs_test
export TEST_DATABASE_URL=postgresql+psycopg://ecs_local:synthetic-local-only@localhost:5432/ecs_test
uv run --locked pytest backend/tests --cov=ecs_ec --cov-report=term-missing
npm --prefix frontend run typecheck
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```

Las pruebas exigen PostgreSQL real y nombre diferente del configurado para la aplicación
(incluido `.env`). Aplican la migración en esa base; no usan SQLite ni producción.
El workflow CI está configurado para instalación bloqueada, suites, build/Compose y
navegador; esto no acredita una ejecución remota de CI ni los perfiles optativos.

Se prueban transacciones/rollback/concurrencia, cobertura completa/incompleta/desconocida,
calendario bisiesto/DST y arranque/reinicio/cierre. El reloj se inyecta internamente;
las reglas IANA se leen de `tzdata` bloqueado, sin rutas públicas para alterar la hora.

Para desarrollo directo, establecer `WEB_DIRECTORY=frontend/out`, aplicar Alembic con
`uv run --locked alembic -c backend/alembic.ini upgrade head` y arrancar
`uv run --locked uvicorn ecs_ec.main:create_app --factory`. FastAPI sirve la exportación
web actual; las vistas privadas usan sesión y API006. Completar antes las claves de
identidad y el contexto/fuentes de la instalación según las guías006/001, sin semillas
de prueba sobre la base de aplicación. Correo/visores no condicionan readiness.

## Respaldo y evidencia

Los argumentos y condiciones de `deploy/backup.sh` y `deploy/restore.sh` están en
[operación](../../deploy/README.md#respaldo-y-restauración). Restaurar en una base vacía
separada `_restore` y comparar filas completas, restricciones y versión de Alembic.

Consultar [plataforma](validation/platform.md), [auditoría](validation/audit.md),
[restauración](validation/restore.md) y [aceptación](validation/acceptance.md) para resultados
locales. [VPS](validation/vps.md) permanece pendiente hasta disponer de un entorno real.
