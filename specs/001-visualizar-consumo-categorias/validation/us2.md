# US2: integración con recepción 002

2026-11-02: T015/T019/T020 completas; T018 parcial por conservación/retirada real 002.
[Comandos, herramientas y evidencia conjunta](increment-2026-11-02.md).

Los cinco escenarios antes omitidos pasan con `consumption_reception_environment` real.
La regresión de consumo incluye reenvío equivalente, conflicto/solapamiento/contigüidad,
concurrencia, cambio ajeno/propio, límites numéricos y originales/eventos conservados.
Las pruebas de 002 incluidas verifican ambas órdenes recepción/reconfiguración,899/900 s,
rollback de aceptación/eventos y recuperación tras pérdida de respuesta o trabajo pendiente.
`Consumption.source_status` usa `read_update_state` real: duplicados no simulan novedades.
Playwright físico se repitió tras reiniciar Uvicorn y PostgreSQL, conservando datos/cuentas.

No se acredita retirada elegible real ni el cierre integral de T018 por simular un payload
retirado en una prueba. Esa capacidad pertenece a US3 de spec-002, no se implementa aquí.
