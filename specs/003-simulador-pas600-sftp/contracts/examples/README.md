# Ejemplo de energía con identidades sintéticas

[Perfil](../pas600-profile.md). Ejemplo documental diseñado, no captura de hardware ni
fixture de conformidad ejecutada. CSV y JSON son alternativas del mismo caso:

- [CSV nativo ilustrativo](csv/1_mb_iEM3150%20CAT03_20260101003000000_1.csv).
- [JSON nativo ilustrativo](json/20260101003000000_1.json).

Identidades del publicador, medidor y tópicos, incluidos `modbus:1_mb_EaImport`, son
**sintéticas**. No se afirma que ese tópico ni Device Type ID sean los asignados por un
PAS600/iEM3150 físico. El descriptor de instalación debe sustituirlos por sus valores
contrastados, manteniendo estructura, semántica y correspondencias. La configuración
real no se deduce del nombre de este ejemplo.

Correspondencia externa al archivo: publicador CSV `SIMULATED-PAS600-001` y remoteId JSON
`urn:dev:cer:1111111111111111111111111111111111111111` representan el mismo concentrador;
medidor local `modbus:1_mb_1`, ReducedID `1_mb`, canal CSV/JSON
`modbus:1_mb_EaImport` → CAT-03, energía activa acumulada en kWh, muestreo 15 minutos,
zona `Etc/UTC`, referencia de instante de lectura. Las otras categorías no tienen
medidor en este ejemplo. No se añade esa correspondencia a los bytes del fabricante.

Oráculo aritmético independiente: lecturas 100 kWh a 00:00 UTC y 104 kWh a 00:15 UTC
producen exactamente un intervalo `[2026-01-01T00:00:00Z,2026-01-01T00:15:00Z)` de
4 kWh; la primera lectura establece referencia. El nombre y mensaje sitúan la publicación
simulada a las 00:30 UTC, distinta de ambos instantes medidos. CSV declara dos filas;
JSON representa esos mismos instantes mediante base UTC y offsets 0/900000 ms.

Contraste documental efectuado en planificación: envoltura/campos y convenciones
contrastados con DOCA0172EN-19 pp. 126–127 y apéndice D; el ejemplo energético adapta
los valores/identidades configurables y no reproduce el caso documental de IO/tensión.
Se aplican tres celdas vacías antes de tópico en filas 4/5 CSV, siguiendo la nota de las
tres comas iniciales del apéndice; al preparar la referencia independiente se debe
revisar visualmente el original, porque la extracción textual del PDF introduce una
celda vacía adicional respecto a esa nota. El lector debe aceptar esas variantes de
presentación y enlazar tópicos por orden, conservando evidencia, sin desplazar las
columnas de medición de la fila 7.

No se ha enviado ninguno de los archivos ni ejecutado su lector. Los fixtures originales
revisados y un lector de pruebas independiente siguen siendo necesarios para SC-001;
estos ejemplos no reemplazan esa evidencia ni certifican los IDs físicos.
