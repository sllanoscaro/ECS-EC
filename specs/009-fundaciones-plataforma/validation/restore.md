# Restauración local comprobada

Ejecutada el 2026-11-02 con los scripts reales y clientes PostgreSQL 18.3 dentro del
contenedor aislado `ecs-ec-platform-validation`. Solo datos sintéticos.

```sh
PG_CONTAINER=ecs-ec-platform-validation PGDATABASE=ecs_test PGUSER=ecs_local \
  deploy/backup.sh /tmp/ecs-ec-spec009-validation.dump
docker exec ecs-ec-platform-validation createdb -U ecs_local ecs_restore
SOURCE_DATABASE=ecs_test PG_CONTAINER=ecs-ec-platform-validation \
  PGDATABASE=ecs_restore PGUSER=ecs_local deploy/restore.sh /tmp/ecs-ec-spec009-validation.dump
```

| Evidencia del snapshot | Origen `ecs_test` | Destino `ecs_restore` |
| --- | --- | --- |
| Revisión Alembic | `platform_009_initial` | `platform_009_initial` |
| Eventos, filas | 2 | 2 |
| Auditoría, filas | 4 | 4 |
| Cobertura, filas | 6 | 6 |
| Restricciones del esquema público | 52 | 52 |
| MD5 filas completas eventos, orden UUID | `9cc900fb165421e938bacc4be8a83b2f` | igual |
| MD5 filas completas auditoría, orden UUID | `1ccc35d3fac139449ad2c92678b6e243` | igual |
| MD5 filas completas cobertura, orden UUID | `808a511caacc3d48f42b8cd73c8327fe` | igual |

Los hashes comparan `row_to_json` de todas las columnas ordenadas por `id`, incluyendo
UUID, JSONB, fechas y `retain_until`. Comprueban igualdad del snapshot, no autenticidad.
Las pruebas posteriores pueden añadir filas al origen. No se afirma conservar roles/ACL.

Controles negativos ejecutados: segunda restauración rechazada con código 2 al detectar
relaciones existentes y respaldo con el mismo nombre rechazado con código 2 sin sobrescribir.
Restauración transaccional, sin `--clean`, en destino independiente. Los clientes del
anfitrión eran PostgreSQL 17; se usaron clientes 18 del contenedor. El archivo está fuera
del repositorio y no contiene datos reales.
