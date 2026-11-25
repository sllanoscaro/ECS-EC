# Integración consumidora002 con PAS600/SFTP003

2026-11-23. Alcance:002:T064 y su contrato de publicación/intento/recuperación.
Se reutilizan001,002,003 y009 reales; no se implementan formatos ni transporte en002.

Este informe conserva el corte del23 de noviembre.002:T065, pendiente al final de
ese corte, se completó después en el paso3: [evidencia vigente](telemetry.md).
El único pendiente actual de002 esT068/personas; no se reejecutó esta suite al actualizar
la documentación el2026-11-25.

## Entorno y reproducción

PostgreSQL18.3 desechable `ecs-step1-test`, loopback55461, base `ecs_step1_test`
distinta de la aplicación y comprobada por `checked_test_url`. Alembic aplica el head
real `demo_calendar_admission`, posterior a la migración inicial003. CPython3.14.4,
pytest9.2.0, FastAPI0.162.0, SQLAlchemy2.0.55, Psycopg3.3.6, AsyncSSH2.24.1 y
tzdata2026.6; manifiestos/locks sin modificaciones.

Desde la raíz, configurar `TEST_DATABASE_URL` con la URL de la base desechable:

```sh
.venv/bin/pytest backend/tests/integration/consumption/test_source_reception.py -q
```

Resultado: los seis casos nuevos pasan dentro de la focal de15 pruebas (10,13s).
La regresión final de integración/contratos de consumo, identidad y adquisición pasa
con253 aprobadas y3 casos largos deseleccionados (133,66s); comando y ajustes del
harness en [evidencia006](../../006-acceso-usuarios-rbac/validation/technical-separation.md).

El simulador independiente debe estar instalado mediante su lock, incluyendo su CLI
`tools/pas600_simulator/.venv/bin/pas600-sim`. El helper de pruebas
`backend/tests/support/source_sftp.py` ejecuta ese CLI y el listener SSH real; no importa
el código del simulador dentro del backend ni sustituye recepción por dobles.
Host key, clave de cliente y verificadores efímeros quedan en el directorio temporal
privado de pytest. La demo existente sigue funcionando en sus contenedores separados.

## Casos comprobados

| Caso de prueba | Resultado requerido y observado |
| --- | --- |
| Generación/publicación real CSV y JSON | Dos intervalos de fuente3/CAT-03,4kWh cada uno, un único update002. Instantes locales21:00–21:30 de Santiago corresponden a00:00–00:30UTC del1enero2026. Se conservan source_id, categoría, referencias de evidencia e identidades de medición. |
| Fragmentos nativos y frontera de sesión | Dos archivos JSON aportan los extremos100/104/109:4 y5kWh. Ni un último archivo abierto ni todos los CLOSE sin EOF generan recepción; el lote completo se incorpora en una actualización de categoría. |
| Caída antes de002 | Antes de llamar al puerto real ya existen en PostgreSQL el attempt_id, entrada ordenada y digest003; la recuperación consulta read_attempt y continúa el mismo ID/entrada. |
| Respuesta perdida tras commit002 | La recuperación obtiene el resultado original mediante read_attempt sin volver a llamar accept. Conserva ID, fecha de incorporación y retención; otra recuperación no crea registros. |
| Rechazo899s y reenvío900s | Novedad5kWh rechazada too_early, duplicado4kWh conservado y próxima admisible exacta. A900s recuperar no reabre el rechazo; una nueva sesión con el mismo manifiesto conserva publication_id y crea attempt_id nuevo, que incorpora la novedad. |

Los seis casos parametrizados se incluyeron en la ejecución conjunta de15 pruebas
con separación006 y dos regresiones de harness003: **15 aprobadas en10,13s**.
Los resultados de regresión amplia se consolidan en la [evidencia006](../../006-acceso-usuarios-rbac/validation/technical-separation.md).

## Límites

Datos, descriptores y credenciales son sintéticos. El cotejo independiente
DOCA0172EN-19 permanece pendiente en003; esta prueba no certifica firmware físico.
Las fronteras899/900s usan el reloj funcional inyectado de002, no un avance del reloj
del host ni una medición nueva de cadencia real del emisor. El ensayo adversarial
usa SSH directo para alcanzar too_early; las pruebas CSV/JSON usan el publicador003.
No se reejecutaron aquí las pruebas largas900s ni restore.

002:T065/emisor ampliado007 y T068/personas siguen pendientes. La comprobación
consumidora002 no cierra tareas ni aceptación integral de003/007.
