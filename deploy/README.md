# Operación común

La plataforma es una imagen con un proceso Uvicorn y PostgreSQL 18 externo.
Identidad, SMTP y observabilidad se incorporan desde sus funcionalidades propietarias.

## Configuración local y construcción

Seguir el [README](../README.md) y el [quickstart](../specs/009-fundaciones-plataforma/quickstart.md).
`cp .env.example .env` crea solo valores sintéticos locales; configurar secretos reales
fuera del repositorio. Compose espera PostgreSQL sano y finalización de `migrate`.
La imagen ejecuta Uvicorn como usuario 10001, sin Node en runtime. `PUBLIC_URL`,
`BUILDING_TIMEZONE` y `ENVIRONMENT` se inyectan al arrancar. No usar `NEXT_PUBLIC_*` para
datos privados. La zona de ejemplo no confirma la del edificio. El build usa Webpack
explícitamente tras observar un fallo nativo de Turbopack.

Los servicios `db`, `migrate` y `app` representan infraestructura/migración y una aplicación.
PostgreSQL 18 monta `/var/lib/postgresql`, con `PGDATA=/var/lib/postgresql/18/docker`.
No aplicar upgrades mayores automáticos.

```sh
docker compose build app
docker compose up -d --wait app
docker compose logs app migrate
docker compose restart app
docker compose stop
```

`stop` y `down` sin `--volumes` conservan datos. La aplicación comprueba el head de Alembic
incluso cuando arranca directamente. `/api/v1/health/live` indica proceso vivo;
`/api/v1/health/ready` comprueba DB, esquema y exportación, con 503 seguro ante fallo.

Cada propietario registra rutas y context managers mediante
`create_app(modules=(Module(...),))` y detiene/espera sus tareas al salir. El cierre ocurre
en orden inverso, seguido del pool DB. Las migraciones enlazan el head real sin recrear
tablas compartidas. Los contratos de escritores están en [plataforma](../docs/platform.md).

## Respaldo y restauración

Se requieren clientes PostgreSQL 18. `PG_CONTAINER` permite usar los clientes del
contenedor PostgreSQL existente. Usar variables libpq o `PGPASSFILE` con permisos 0600
(ruta dentro del contenedor si corresponde), sin URLs con claves como argumentos.
`PGHOST`/`PGPORT` corresponden al espacio donde ejecuta el cliente; omitirlos para usar
el socket local del contenedor. No guardar respaldos en Git ni en la imagen.

```sh
# Consultar primero el nombre exacto con docker compose ps.
export PG_CONTAINER=ecs-ec-db-1
export PGUSER=ecs_local
export PGDATABASE=ecs_local
./deploy/backup.sh /tmp/ecs-ec-local.dump
docker compose exec db createdb -U ecs_local ecs_restore
export SOURCE_DATABASE=ecs_local
export PGDATABASE=ecs_restore
./deploy/restore.sh /tmp/ecs-ec-local.dump
```

El respaldo usa snapshot consistente de `pg_dump`, formato custom, permisos 0600 y
publicación atómica sin sobrescribir. Un fallo no publica archivos incompletos.
La restauración exige destino vacío distinto terminado en `_restore`, host local y nombre
sin connection strings. No usa `--clean`, aplica todo en una transacción y rechaza una
segunda restauración. La aplicación de origen no debe apuntar al destino de verificación.

Comparar filas completas, restricciones, fechas de conservación y `alembic_version`;
contar filas no basta. Ejecutar suites en otra base `_test`, nunca en respaldos reales.
La [evidencia local](../specs/009-fundaciones-plataforma/validation/restore.md) usa datos
sintéticos. Cifrar respaldos fuera del host, restringir acceso y comprobar restauración
periódicamente. Roles/ACL se provisionan externamente: `--no-owner --no-acl` conserva
filas/restricciones, no privilegios. No hay borrado automático ni downgrade destructivo.

## Preparación VPS

Configurar dominio/DNS reales, URL pública HTTPS, zona IANA real, credenciales externas y
volumen persistente. `ENVIRONMENT=production` valida HTTPS y rechaza la contraseña sintética.
Si la contraseña contiene caracteres reservados de URL, codificarlos en `DATABASE_URL`;
en Compose, adaptar explícitamente ese valor manteniendo la contraseña original de DB.
No exponer PostgreSQL a Internet.

Un proxy TLS de infraestructura del operador termina HTTPS y reenvía a `127.0.0.1:8000`.
Configurar certificado/renovación, redirección HTTP→HTTPS y firewall 80/443. Aceptar
cabeceras proxy solo desde el proxy confiable, con límites/timeouts. El acceso a la red
técnica de spec-007 no otorga acceso funcional; SMTP se verifica en spec-008.

Registrar CPU, RAM, disco libre, tamaño de volumen/respaldo y duración de construcción y
restauración en el entorno real antes de dimensionar; no hay SLO ni mínimo de recursos
aprobado. Reservar disco para DB, imagen y respaldo separados. Antes de publicar, comprobar
salud desde HTTPS, puertos internos cerrados, persistencia tras reinicio, secretos externos,
permisos del volumen y restauración independiente. No registrar claves ni filas personales.

La [validación VPS](../specs/009-fundaciones-plataforma/validation/vps.md) permanece pendiente
por falta de entorno real, según la decisión del usuario. La ejecución local no la acredita.
