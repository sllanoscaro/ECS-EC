# US2 — recepción y transporte locales reales

2026-11-03. Python3.14.4, AsyncSSH2.24.1, PostgreSQL18.3. Entornos aislados `_test`,
host keys administradas y credenciales sintéticas temporales. No se usó VPS ni hardware.

Implementado el receptor en el lifespan común, persistencia003, bindings inmutables,
staging privado, cuota/exclusión, lectores independientes, correspondencias/deltas y
evaluaciones recuperables sobre `Reception.accept/read_attempt` reales002. La migración
`f68f086ee8a7` enlaza `costs_004_bills`; upgrade desde cero, downgrade vacío, nuevo
upgrade y `alembic check` pasan. El downgrade rechaza evidencia poblada.

Comandos desde raíz, con TEST_DATABASE_URL apuntando a PostgreSQL18 separado:

```sh
uv run --project tools/pas600_simulator --locked pytest tools/pas600_simulator/tests/unit/test_transport.py tools/pas600_simulator/tests/contract/test_transport_cli.py -q
uv run --locked pytest backend/tests/unit/acquisition backend/tests/contract/acquisition backend/tests/integration/acquisition -q
uv run --locked pytest backend/tests/integration/acquisition/test_real_time_publication.py -m real_time -q -s
```

El segundo comando excluye real_time/restore por defecto. El tercero tarda al menos
30 minutos al ejecutar ambos casos; no admite una variable para reducir los900s.

| Ensayo ejecutado | Resultado |
| --- | --- |
| Dos ciclos SSH/SFTP, reloj/transporte reales | Separación fin→inicio900,004936s;2 evaluaciones aceptadas;902,07s de prueba. |
| Primera conexión interrumpida después de escritura y demora real >=0,25s | Reintento tras900,015390s; primer intento uncertain, segundo clean;1 evaluación aceptada;902,52s de prueba. |
| Paquete aislado `--locked --no-dev` | Sin pytest ni ecs_ec importables; validate/generate/probe/publish pasan con password_env y private_key_file. Reenvío real devuelve duplicate002. |
| CLOSE sin EOF/conexión perdida; EOF con handle pendiente | Lotes abortados; ninguna publicación parcial. Probe/vacía no crea mediciones. |
| Fsync o commit de metadata fallidos | Bytes conservados; ninguna promoción por tamaño o parseo. |
| Recuperación tras perder respuesta002 después del commit | Mismo attempt_id/entrada/digest, resultado/fecha originales; dos recuperadores concurrentes no duplican incorporación. |
| Reenvío íntegro nuevo; conflicto | Nueva evaluación/intento para el mismo manifiesto; duplicate sin doble consumo. Otra entrada con el mismo ID es attempt_payload_conflict. Primera canónica válida no se sustituye. |
| too_early confirmado | Recuperación devuelve el original aun tras avanzar reloj interno; solo otra sesión sellada crea intento nuevo admisible. |
| Total opcional por SFTP multiarquivo real | CAT-03=4 y CAT-05=7 producen CAT-01 calculada11 por002. Con medidor CAT-01=20 conserva20. Archivo corrupto independiente no descarta los válidos. |
| Cuotas/aislamiento | Traversal, offset, secuencia, bytes/archivos, dos sesiones y una escritura por publicador; shell denegado; claves desconocidas rechazadas. |
| Presupuesto/cadencia unitarios | 899/900 monotónicos, reinicio conservador900, tres intentos transitorios totales, permanente uno, agotamiento conservado, journal serializado. No acreditan por sí solos tiempo real. |

Las pruebas de tiempos reales se ejecutaron antes de los últimos refuerzos de constraints,
locks de journal y metadatos de estado de archivo. Esos cambios pasaron las suites rápidas;
las dos esperas largas no se repitieron. No se certifica comportamiento del firmware físico
ni conformidad documental19. La aceptación integral sigue en [acceptance.md](acceptance.md).

Los manifiestos/hashes de los cuatro escenarios de anomalías y los datos saneados de
las mediciones largas se conservan en [local-evidence.json](local-evidence.json).
