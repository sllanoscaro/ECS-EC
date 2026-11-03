# US1 — evidencia local parcial

**Registro histórico2026-11-02** (el incremento vigente está en [aceptación](acceptance.md)). Paquete independiente con lock propio; Python3.14.4.
El usuario autorizó diferir T003. No se acredita conformidad documental con
DOCA0172EN-19 ni hardware. T008/T009 conservan pendiente esa revisión aunque
sus pruebas locales de estructura ya existen.

Implementado: generador determinista por SHA-256/quantum entero; Decimal exacto;
siete canales independientes por defecto; ausencia sin medidor ficticio; CAT-01
medida no se suma desde otras categorías; referencias acumuladas N+1 para toda la
ejecución; CSV/JSON nativos; nombres/hashes y fragmentación; oráculo/control separado;
CLI validate/generate con selección de formato, rechazo de salida ocupada y errores
saneados. Los ciclos se generan de forma acotada, sin dormir ni abrir conexiones.

Validación final:40 pruebas pasan mediante:

```sh
uv run --directory tools/pas600_simulator --locked pytest -c pyproject.toml tests
```

Lectores independientes en tests usan csv/json/Decimal y no importan el parser backend.
Se comprueban100/104=4kWh, equivalencia temporal/energética, bytes reproducibles,
CSV CRLF/UTF8/comillas/preámbulo, estructura JSON/valores numéricos/t entero,
fraccionamiento de contadores de500 dígitos, categorías ausentes, cero medidores,
canal de intervalo evidenciado y orden de categorías. No sustituyen la revisión19.

Instalación y generación finales ejecutadas con:

```sh
uv sync --directory tools/pas600_simulator --locked --no-dev
uv run --directory tools/pas600_simulator --locked --no-dev pas600-sim validate --scenario examples/seven-meters.json
```

Desde ese entorno se comprobaron importlib.util.find_spec('pytest') y
find_spec('ecs_ec') ausentes, se cargaron los cuatro ejemplos mediante
SimulationScenario.model_validate_json y se generaron ambos formatos con generate_run
en directorios temporales nuevos. Resumen completo en
[generation-metrics.json](generation-metrics.json). Duraciones medidas, sin SLO:

| Ejemplo | Formato | Ciclos | Archivos | Bytes nativos | Segundos |
| --- | --- | ---: | ---: | ---: | ---: |
| seven-meters.json | csv | 1 | 7 | 30912 | 0.042 |
| seven-meters.json | json | 1 | 1 | 19033 | 0.038 |
| partial-no-total.json | csv | 1 | 2 | 8832 | 0.012 |
| partial-no-total.json | json | 1 | 1 | 5613 | 0.013 |
| historical-12m.json | csv | 365 | 2555 | 11769246 | 12.587 |
| historical-12m.json | json | 365 | 365 | 7469083 | 12.884 |
| anomalies-100.json | csv | 2 | 14 | 34804 | 0.047 |
| anomalies-100.json | json | 2 | 2 | 20387 | 0.047 |

El caso histórico tiene35040 intervalos por categoría y245280 esperados en total.
La prueba histórica prohíbe socket.socket y cuenta el oráculo completo. No acredita
retención ya transcurrida ni publicación acelerada. La referencia inicial se conserva
una sola vez y no se vuelve a emitir en cada ciclo.

T021 sigue parcial: falta referencia19 y CAT-01 calculada integrada de001/002.
En ese corte no se ejecutaron SFTP ni recepción real. El incremento2026-11-03 sí los comprueba, incluida CAT-01 calculada/medida; ver [US2](us2.md). La conformidad documental sigue pendiente.
