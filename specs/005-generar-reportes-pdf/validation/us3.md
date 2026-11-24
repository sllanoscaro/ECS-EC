# US3 — conjuntos financieros y revisiones

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

El ejemplo real004 de tres ciclos10/20/30CLP conserva disponible60 y dos pares
calculado40/facturado38/diferencia2. El cierre en inicio se incluye y el cierre en
fin se excluye. Se presentan monedas/bases por separado y se conserva el signo de
importes y exclusiones; facturado comparable se distingue del total a pagar de boleta.
No se agregan tarifas ni nuevas fórmulas en005. Un cálculo004 real sobreCAT-01
calculada mantiene `complete_total=null` en la captura/PDF, conservando20kWh energéticos.

Se emitieron A=C1/B1/K1, B=C1/B2sin comparación, C=C1/B2/K2 y D=C2/B2sin comparación.
B/D muestran «Contraste pendiente para estas revisiones», diferencias nulas y conjunto
pareado vacío; A mantiene captura/hash/bytes y las lecturas no crean comparaciones.
Durante un render real se corrigió boleta, se recalculó004 y se incorporó nueva energía002:
A mantiene1000kWh/C1/B1; B refleja3000kWh/C2/B2. Ningún renderer recaptura datos.

Referencias: `test_costs_snapshot_contract.py`, `test_costs_pdf_end_to_end.py`,
`test_cutoff_concurrency.py` y `test_financial_summary.py`, bajo `backend/tests/`.
Las reglas tributarias y de comparación siguen perteneciendo a004, cuya suite se
incluye en la regresión general; no se acepta esa propiedad por un doble de005.
