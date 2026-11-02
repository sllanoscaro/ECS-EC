# Quickstart: Validación de plataforma común

Guía prevista, no comandos de aplicación ya disponibles. [Plan](plan.md),
[tareas](tasks.md), [arquitectura](../../docs/architecture.md).

Después de implementar la base, desde la raíz:

```sh
cp .env.example .env
uv sync --locked --group dev
npm --prefix frontend ci
npm --prefix frontend run build
docker compose build app
docker compose up -d db
docker compose run --rm app uv run --locked alembic -c backend/alembic.ini upgrade head
docker compose up -d app
uv run --locked pytest backend/tests/unit/core backend/tests/integration/core backend/tests/integration/audit
```

Configurar `.env` local antes de arrancar. Usar PostgreSQL 18 real y `TEST_DATABASE_URL`
separada para pruebas; nunca la base de producción. Esperado: imagen única, frontend
estático sin datos privados, migraciones correctas, salud funcional y cierre ordenado.
No requiere bootstrap de identidad, SMTP ni visores técnicos.

Validar transacción/rollback/deduplicación, cobertura completa/incompleta/desconocida y
aniversarios con reloj inyectable; repetir reinicio sin pérdida de datos confirmados.
Los scripts de backup/restore documentarán argumentos concretos durante implementación:
restaurar en destino local separado y comparar filas/revisión de Alembic.

Registrar comandos, versiones y resultados en `validation/acceptance.md` y
`validation/restore.md` cuando se ejecuten. La validación VPS espera dominio, HTTPS y
configuración reales; un build local no la acredita. Las guías de cada módulo agregan
sus propios perfiles y escenarios sin volver a crear la plataforma.
