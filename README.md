# ECS-EC

Sistema de monitoreo eléctrico de un edificio, con arquitectura monolítica modular.
Estado actual: implementación de la plataforma compartida (spec-009); los módulos
funcionales permanecen pendientes según la hoja de ruta.

- [Arquitectura compartida](docs/architecture.md): stack, módulos, datos y entornos.
- [Hoja de ruta](docs/implementation-roadmap.md): propietarios, dependencias, estado y uso de Spec Kit.
- [Instrucciones del repositorio](AGENTS.md): carga de contexto común para trabajar con Spec Kit.
- [Plataforma compartida (spec-009)](specs/009-fundaciones-plataforma/spec.md): punto de partida técnico.
- [Especificaciones funcionales](specs/): cada funcionalidad conserva requisitos, diseño y tareas propios.

`docs/` contiene contexto común. Los archivos que procesa Spec Kit permanecen en
`specs/<identificador>/`, con nombres nativos (`spec.md`, `plan.md`, `tasks.md`, etc.).
Las plantillas de proyecto usan `.specify/templates/overrides/`, mecanismo soportado por
la instalación local. Los scripts y las skills generados siguen siendo infraestructura local.
## Ejecutar la plataforma

Requisitos: Docker/Compose, uv 0.11.8, CPython 3.14.4 convencional y Node 24.22.0
(mínimo 20.9). Las dependencias están fijadas en `uv.lock` y `frontend/package-lock.json`.

```sh
cp .env.example .env
uv sync --locked --group dev
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
docker compose build app
docker compose up -d --wait app
curl --fail http://localhost:8000/api/v1/health/ready
```

Compose espera PostgreSQL sano y ejecuta Alembic antes de iniciar el único proceso
Uvicorn. La aplicación sirve la exportación Next desde `/` y la API desde `/api/v1`.
No requiere cuentas, correo o visores. Las credenciales del ejemplo son sintéticas locales.

## Verificar

Crear una base independiente cuyo nombre termine en `_test` y configurar
`TEST_DATABASE_URL` con `postgresql+psycopg://.../ecs_test`. Las pruebas rechazan el
mismo destino de `DATABASE_URL` y no usan SQLite. Alembic se aplica al destino de prueba.

```sh
docker compose exec db createdb -U ecs_local ecs_test
export TEST_DATABASE_URL=postgresql+psycopg://ecs_local:synthetic-local-only@localhost:5432/ecs_test
uv run --locked pytest --cov=ecs_ec --cov-report=term-missing
npm --prefix frontend run typecheck
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```

Para ejecutar fuera de Docker, exportar `DATABASE_URL` y `WEB_DIRECTORY=frontend/out`,
aplicar `uv run --locked alembic -c backend/alembic.ini upgrade head` y arrancar con
`uv run --locked uvicorn ecs_ec.main:create_app --factory`. No hay servidor Node de producción.

La [guía de operación](deploy/README.md) y el [quickstart](specs/009-fundaciones-plataforma/quickstart.md)
describen restauración, configuración y límites de validación. La evidencia ejecutada
se registra en [validation](specs/009-fundaciones-plataforma/validation/).
