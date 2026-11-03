# US3 — generación y recepción local real

**Registro histórico2026-11-02**. Suite final de ese corte:40 pruebas locales pasan; comandos/resultados en
[US1](us1.md). T049–T058 implementadas. T059 pendiente: no hay recepción SFTP
real ni contraste integrado de cobertura ejecutados en este cambio.

Anomalías seleccionadas con SHA-256 y dominios separados por clase; floor exacto
sobre N original, sin contar referencia inicial. Posiciones explícitas se reservan
antes del ranking y se validan por cantidad/rango/unicidad/no solapamiento.
Ejemplo anomalies-100: CAT-03 tiene10 omisiones,10 formatos incorrectos,
10 incrementos fuera de rango y70 normales; las otras categorías no se alteran.
Se comprueban tasas fraccionarias,0/100% y suma mayor que100 rechazada.

Omisión elimina la lectura; tipo/date alteran solo la posición elegida.
Outliers max+quantum/min−quantum modifican el incremento y desplazan contadores
siguientes sin inducir otros incrementos defectuosos. Un contador negativo o outlier
no representable se rechaza antes de reservar output. ExpectedSample permanece
intacto; anomalies.jsonl conserva asignación y consecuencias sobre intervalos vecinos.

La corrupción estructural selecciona exactamente un nombre nativo y se aplica después
de serialización/fragmentación. Manifest registra scope file, operación y hashes
antes/después; el manifiesto de publicación registra bytes finales. Casos CSV sin
cabecera y JSON truncado; archivos no seleccionados conservan bytes/hashes.
Selectors inexistentes/repetidos o incompatibles se rechazan antes de escritura.
Los defectos por archivo no incrementan las tasas por muestra.

No se presupone que001 deba rechazar un positivo superior al rango de pruebas.
No se declara SC-002 ni limpieza integrada aceptadas sin resultados reales de002.


## Incremento2026-11-03: T059 comprobada

SFTP local real y002 real en test_anomalous_sftp.py: CSV yJSON, format_mode type/date.
Escenario anomalies-100, semilla ecs-ec-example, descriptores sintéticos adaptados al
binding confiable y offsets America/Santiago explícitos. Se publican únicamente archivos
nativos de cada manifiesto; expected/anomalies permanecen fuera del receptor.

Cada caso conserva10 omisiones,10 formatos y10 outliers positivos en CAT-03. La unión
de intervalos afectados por extremos missing/format tiene38 índices: quedan62 intervalos
incorporados en CAT-03 y100 en cada una de las otras seis categorías. Hay exactamente10
lecturas inválidas, sin valor numérico. Tipos/fechas no bloquean los registros válidos.
Los positivos superiores a la banda del escenario siguen las reglas001 reales y no se
rechazan por una regla privada del simulador. Se preservan hashes/nombres de los manifiestos en [local-evidence.json](local-evidence.json)
y posiciones en los runs temporales; la semilla y configuración permiten regenerarlos.

Archivos rotos mezclados con válidos se comprobaron tanto por staging como por SFTP
multiarquivo real en test_totals.py: file_unreadable es diagnóstico de archivo y los válidos
producen4/7kWh, con total11 calculado o20 medido. Corrección tardía de una inválida solo
crea pares adyacentes; no se generó un delta8 sobre el hueco. Pruebas internas de estos
casos avanzan reloj002 entre lotes; las esperas reales se acreditan solo en [US2](us2.md).
