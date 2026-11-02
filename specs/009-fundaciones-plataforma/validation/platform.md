# Validación local de plataforma

Ejecutada el 2026-11-02 con configuración sintética. No acredita VPS ni módulos de negocio.

| Comprobación | Resultado |
| --- | --- |
| `uv sync --locked --group dev` | Correcto; CPython 3.14.4 convencional, uv 0.11.8, FastAPI 0.162.0, SQLAlchemy 2.0.55/Psycopg 3.3.6. |
| `npm --prefix frontend ci`, `test`, `build`, `run typecheck` | Correcto; Node 24.22.0, Next 16.4.3, React 19.3.1. |
| Pruebas core con PostgreSQL 18.3 | Primera fase: 9 pasan. Suite final completa: 40 pasan, 93% de cobertura Python. |
| `docker compose -p ecs-ec-spec009-validation build app` | Construcción multietapa correcta; imágenes de origen fijadas por digest. |
| `docker compose ... up -d --wait app` | Volumen nuevo, DB sana → migración exitosa → aplicación saludable. |
| Web y API | `/` responde 200 y `/api/v1/health/ready` devuelve `{"status":"ready"}` en el mismo proceso. |
| Reinicio de aplicación | Salud recuperada; salida Uvicorn registra cierre y arranque ordenados. |

El proyecto aislado usa `APP_PORT=58009`, `DB_PORT=55440`; las pruebas Python usan
otra base `ecs_test` en el puerto 55439. Ningún destino de producción se utiliza.
Las pruebas rechazan una base sin revisión de Alembic y verifican rollback/liberación
de conexiones. La primera validación US1 precede a las tablas de auditoría de US2;
la validación final repite migración y arranque con el head común instalado.

Validación final: imagen `sha256:9f5a7d46b8215f3726a2af5a071394e043ee8f663c61b1eaa861c5bf39c20901`,
build Webpack y migración `platform_009_initial` aplicados correctamente. Prueba real
de Chromium/Playwright 1.64.0: 1 pasa, verifica página y salud en el mismo origen.
Vitest: 1 pasa; TypeScript y exportación correctos tras `npm ci` final. Se comprobó
PID 1 Uvicorn con un worker, ausencia de Node en runtime y ausencia de marcadores de
credenciales/URL DB en el artefacto estático.

Con PostgreSQL de Compose detenido realmente, liveness devolvió 200 y readiness 503
con código fijo `platform_unavailable`, sin SQL ni excepciones crudas. Tras reiniciar
PostgreSQL, readiness recuperó `ready`; el evento sintético confirmado antes del reinicio
conservó UUID/carga y la revisión de Alembic. No se perdieron datos del volumen.

Los paquetes, hashes transitivos y digests exactos se conservan en los lockfiles,
`Dockerfile` y `compose.yaml`. No se requieren cuentas, correo o telemetría.

Al terminar se detuvieron los contenedores de validación, conservando volumen/bases y
respaldo sintético. No se eliminaron datos ni se dejó una aplicación publicada.
