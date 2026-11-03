# Simulador PAS600

Fuente externa opcional de spec-003, Python3.14, independiente del backend.
Los identificadores de ejemplo son **sintéticos**; no certifican una instalación física.
La revisión documental DOCA0172EN-19 queda diferida por instrucción del usuario.

Desde la raíz del repositorio:

```sh
uv sync --project tools/pas600_simulator --locked
uv run --directory tools/pas600_simulator --locked pas600-sim validate --scenario examples/seven-meters.json
uv run --directory tools/pas600_simulator --locked pas600-sim generate --scenario examples/seven-meters.json --output /tmp/pas600-csv --format csv
uv run --directory tools/pas600_simulator --locked pas600-sim generate --scenario examples/seven-meters.json --output /tmp/pas600-json --format json
uv run --directory tools/pas600_simulator --locked pytest -c pyproject.toml tests
```

Los directorios de salida deben ser nuevos o vacíos. Para ejecutar sin pytest usar
`uv sync --project tools/pas600_simulator --locked --no-dev` y añadir `--no-dev`
a los comandos `uv run`. Pydantic, AsyncSSH y simplejson son dependencias de ejecución;
pytest pertenece al grupo dev. validate/generate no abren conexiones; test-connection/publish/resend usan SFTP.

Comandos disponibles: validate, generate, test-connection, publish, resend, report y
compare. Salida JSON versionada en stdout; diagnósticos fijos en stderr. Códigos:
0 éxito,2 argumentos/configuración,3 identidad/permisos permanentes,4 transporte o
presupuesto agotado,5 evidencia ilegible/insuficiente y6 diferencias observadas.
SIGINT/SIGTERM producen130. Transferir no acredita aceptación002.

`data/<publication-key>/` contiene solo archivos nativos CSV/JSON.
`control/` conserva configuración, oráculo previo en `expected.jsonl`, asignaciones
por muestra en `anomalies.jsonl`, manifiestos/hashes finales y estado real en `run.json`.
La referencia acumulada inicial no cuenta como consumo ni como muestra de anomalía;
N intervalos producen N+1 lecturas en toda la ejecución. El estado `generated` se
persiste solo después de escribir y sincronizar evidencia/manifiesto. No reutilizar
una ejecución fallida para cambiar sus bytes: generar otra en un directorio nuevo.

Ejemplos: siete medidores independientes (CAT-01 conserva su medidor propio),
`partial-no-total.json` (solo CAT-03/CAT-05), `historical-12m.json` (extremos calendario
de2026 a2027) y `anomalies-100.json` (100 intervalos, CAT-03 con10% por clase).
Los rangos son de prueba; no describen bandas físicas de una instalación.

Cada categoría medida configura `rates.missing`, `rates.format`, `rates.out_of_range`;
cada conteo es floor(N×porcentaje/100), con posiciones disjuntas. `rates.positions`
admite índices explícitos desde0 por clase, de cantidad exacta. Selección automática:
SHA-256 versionado, semilla/categoría/índice y dominios por clase. Posiciones explícitas
se reservan antes de seleccionar las restantes. `format_mode` es `type` o `date`;
`out_of_range_direction` es `above` (max+quantum) o `below` (min−quantum).
Los incrementos alterados desplazan contadores siguientes conservando los demás deltas.
El oráculo se escribe antes de alteraciones; los efectos sobre intervalos vecinos se
identifican aparte y nunca aumentan la cantidad de defectos deliberados.

`structural_corruptions` acepta objetos `{ "filename": "nombre-nativo-exacto.csv",
"operation": "remove_header" }` o `truncate` para CSV/JSON. La selección se resuelve
antes de escribir; no admite archivos inexistentes ni selectores repetidos.
Estos defectos se registran con scope file y hashes antes/después en el manifiesto,
separados de las tasas por muestra. Cambiar formato exige otra generación.

Los archivos se dividen por duración UTC máxima de24h, y JSON además por256000 bytes
incluida la envoltura. Muestreo y tiempo simulado no son cadencia de publicación:
la transferencia respeta al menos900 segundos reales desde el fin del intento anterior.

Contratos completos y aceptación pendiente en
[spec-003](../../specs/003-simulador-pas600-sftp/contracts/cli.md).


## Transporte y recuperación

Copiar [transport.local.json](examples/transport.local.json) a un archivo externo y
ajustar host/puerto/directorio/usuario/alias y known_hosts previamente contrastado.
Auth admite exactamente password_env o private_key_file; una clave privada requiere
0600 y admite passphrase_env opcional. No se aceptan contraseñas inline ni hosts sin
verificar. El alias debe ser estable para un mismo destino; no rotarlo para eludir espera.

```sh
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim test-connection --transport /ruta/privada/transport.json
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim publish --run /tmp/pas600-json --transport /ruta/privada/transport.json
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim publish --resume --run /tmp/pas600-json --transport /ruta/privada/transport.json
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim resend --run /tmp/pas600-json --publication CLAVE_DEL_MANIFIESTO --transport /ruta/privada/transport.json
```

Probe escribe/retira solo .ecs-ec-probe. Una sesión entrega el conjunto nativo completo,
CLOSE por archivo y EOF explícito al completar todos. Ante fallo aborta sin EOF; conservar
los estados transferred y uncertain por separado. Tres intentos totales iniciales por
publicación; errores permanentes detienen. Resend abre presupuesto nuevo explícito y
conserva historial/cadencia. --resume continúa únicamente trabajo no confirmado.

Hay un flock por ejecución y otro por alias/publicador. PAS600_SIM_STATE_DIRECTORY
elige el directorio privado de coordinación (predeterminado ~/.local/state/ecs-ec-pas600).
Todos los procesos para ese destino deben compartirlo. Se persiste antes de conectar;
reiniciar exige900s nuevos conservadores. Esperar usa monotónico, sin atajos del relojUTC.
No borrar markers/locks para acelerar aceptación. Señales impiden iniciar otro ciclo;
el actual termina bajo timeout o aborta, conservando bytes, ordinales y journal.
transfers.pending.json es la captura atómica de recuperación y transfers.jsonl su copia
legible. El journal no confirma resultados funcionales.

## Informe y contraste offline

```sh
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim report --run /tmp/pas600-json --output /tmp/pas600-report.json
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim compare --run /tmp/pas600-json --reception /tmp/pas600-reception.json --output /tmp/pas600-comparison.json
```

El receptor exporta mediante proceso de mantenimiento autorizado, con selección explícita
--start/--end/--timezone/--categories/--view y una sola captura REPEATABLE READ de003 y
consumo001/002. Seguir el [quickstart](../../specs/003-simulador-pas600-sftp/quickstart.md).
No se envía el oráculo al backend. Compare verifica manifiesto/hashes, selección, tiempos,
energía, cobertura y extremos disponibles; conserva diferencias y limitaciones.
0 exige complete sin diferencias;5 indica partial/not_evaluable sin diferencias demostradas;
6 conserva hallazgos incluso con limitaciones y puede describir limpieza legítima.
Un proveedor unavailable, bloques excluidos o extremos retirados nunca acreditan éxito
vacío. La revisión documental19, reproducción por otra persona y aceptación integral
permanecen abiertas en la [evidencia003](../../specs/003-simulador-pas600-sftp/validation/acceptance.md).
