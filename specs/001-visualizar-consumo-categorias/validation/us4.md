# US4 — estados y evidencia numérica

2026-11-03. `test_detail_states.py` usa recepción002 real: sin medidor, instalada sin
lecturas, cero físico/calculado, contribución faltante que después completa20, intervalos
desalineados, huecos, quantum10^-15 y diagnóstico por cambio de base con revisión nula,
segmentos conservados y sin faltantes o fecha próxima inventados. Se conserva el total
exacto6*M y sus seis contribuciones, superior al dominio individual.

Las pruebas compartidas de002 ejercitan pendientes temporales, recuperación/reinicio,
ventanas de899/900s y carreras de recepción/configuración en ambas órdenes. Las pruebas
001 de disponibilidad comprueban503 distinto de ausencia y rollback de evidencia.
Las consultas no incorporan datos ni renuevan conservación.

`consumption.spec.ts` contrasta los estados/API, cero y positivo mínimo y siete categorías
con gráfico/tabla en ambos modos. `consumption-detail-states.spec.ts` añade recepción
parcial→CAT-01 incompleta→llegada tardía→20kWh, seis máximos individuales y su total exacto,
cambio de base diagnosticado con parciales visibles y cambio propio que rechaza la fuente
anterior. Retrasa una respuesta real A mientras se selecciona B y comprueba error/reintento
por teclado sin cifras antiguas. Los controles privados usan ConfigurationService y
Reception reales desde `backend/tests/control_consumption_browser.py`; no hay endpoints
públicos ni escritura directa de mediciones. El reloj privado del harness002 se alinea con
Date del navegador, conservando temporizadores reales.

El ensayo ampliado exige fuente física inicial de siete medidores y cuentas ya renovadas
por `consumption.spec.ts`. Se ejecuta después, en la misma base desechable. Cada transición
avanza901 segundos del reloj privado; las ventanas nuevas no se solapan. Los casos de
rechazo conservan la selección vacía sin inventar energía. No equivale a personas reales,
recepción SFTP, Mailpit ni VPS.

Comandos/resultados en [aceptación](acceptance.md). FR-014..016/SC-004 y casos I1/U1/A1
verificados en el alcance local descrito, con valores de referencia sintéticos.
