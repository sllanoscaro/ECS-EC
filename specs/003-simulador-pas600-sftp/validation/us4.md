# US4 — contraste y reproducción automatizada

2026-11-03. Implementados report/compare, exportador técnico, parada/reanudación y
journal durable. T060–T069 tienen implementación y evidencia local; T070 permanece
abierta por reproducción independiente por otra persona.

Pruebas: `tools/pas600_simulator/tests/contract/test_reproducibility.py`,
`test_evaluation_cli.py`, `test_transport_cli.py`, unit/test_compare.py y los contratos/
integraciones003 del backend. Igual escenario/semilla/categorías reordenadas reproduce
el100% de bytes, expected.jsonl, anomalías y manifiesto; UUID/tiempos reales son distintos.
CSV/JSON comparten identidad lógica y difieren en identidad completa de formato.

La exportación usa una UoW REPEATABLE READ, snapshot_id/cutoff_at y selección obligatoria.
Una incorporación002 concurrente entre lectura003 y lectura001 no aparece parcialmente:
la captura anterior conserva no_data y la siguiente muestra4kWh. No se llama a detail
en otra transacción ni se usa igualdad de fechas como prueba de consistencia.

| Contraste ejecutado sobre exportación real | Resultado CLI |
| --- | --- |
| Intervalo100→104, resultado002 y detalle4kWh | complete,0. |
| Evidencia de consumo alterada a5kWh | Diferencia observada,6. |
| Proveedor marcado unavailable | not_evaluable,5, sin éxito vacío. |
| Tres intervalos15min dentro de una hora |2700s/75%, partial,5. |
| Esa captura alterada para declarar3600s/100% | coverage_difference,6. |
| Categoría agrupada faltante o lista de bloques vacía | Limitación explícita; nunca complete sin evidencia. |
| Manifiesto ajeno/hash cambiado | Evidencia rechazada;5. |

SIGTERM durante espera real900 retorna130 y conserva bytes/marker. SIGTERM durante
WRITE y SIGINT después de CLOSE terminan solo el intento actual bajo sus timeouts,
conservan journal y no empiezan el segundo ciclo. La recuperación reutiliza hechos
confirmados; un intento iniciado no se considera entregado.

Los informes preservan manifiesto/extremos/causas y resultados por evaluación; los campos
de secreto ajenos al journal no se copian. Los errores de CLI no reflejan argumentos
arbitrarios. Endpoints de publicaciones anteriores ausentes del export se declaran
limitación, sin reconstruir evidencia inventada. No se han aceptado SC-003/SC-005 por
otra persona ni se ha comprobado visualmente cada escenario de UI durante este cambio.
