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
pytest pertenece al grupo dev. Ningún comando implementado abre conexiones.

Comandos disponibles: `validate` y `generate`. Salida JSON versionada en stdout;
diagnósticos saneados en stderr. Códigos0 éxito,2 configuración inválida,
5 archivo ilegible, salida ocupada o error de evidencia. Publicación SFTP, exportación
integrada, `report` y `compare` siguen pendientes; la generación no acredita recepción.

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
la futura transferencia debe respetar900 segundos reales desde el fin anterior.

Contratos completos y aceptación pendiente en
[spec-003](../../specs/003-simulador-pas600-sftp/contracts/cli.md).
