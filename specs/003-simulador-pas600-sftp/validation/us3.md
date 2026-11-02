# US3 — generación de anomalías local, recepción pendiente

2026-11-02. Suite final:40 pruebas locales pasan; comandos/resultados en
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
