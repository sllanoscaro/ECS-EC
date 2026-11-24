# Auditoría de cobertura005 — 2026-11-24

Esta matriz distingue implementación/verificación local de aceptación externa.
Ver [aceptación](acceptance.md), [US1](us1.md), [US2](us2.md), [US3](us3.md),
[US4](us4.md), [instrumentación](observability.md), [offline](offline.md) y
[protocolo humano](usability.md). Los nombres de pruebas se refieren a
`backend/tests/{unit,integration,contract}/reports/` salvo cuando se indica frontend.

| Requisito | Comportamiento | Evidencia | Estado/límite |
| --- | --- | --- | --- |
| FR-001/002 | Selección y descarga de tres escalas | E2E reports.spec.ts; contratos HTTP; test_real_pdf_pipeline.py | Verificado localmente |
| FR-003 | Selección inválida/futura y campos conservados | Contratos/calendario; E2E; report-download.test.tsx | Verificado |
| FR-004 | Una página y publicación íntegra | test_one_page_layout.py; preflight; integridad PostgreSQL | Verificado |
| FR-005 | A4 y texto>=10pt | Bytes/manifiesto/glifos y revisión digital en us2.md | Impresión física pendiente |
| FR-006 | Siete categorías y origen/base | test_annual_layout.py; test_real_pdf_pipeline.py | Verificado |
| FR-007 | Hora/día/mes y vacíos, DST | test_chart_blocks.py:25bloques/rectángulos y ambos offsets; pipeline24/31/12 | Verificado |
| FR-008/009 | Agregados, ausencia/ceros/retirada | test_retained_total.py; test_quality_provenance.py; suites001/002 | Verificado |
| FR-010 | Ciclos por cierre en[inicio,fin) | test_costs_snapshot_contract.py y productor004 | Verificado |
| FR-011/012 | Importes/bases/estados de004 | test_financial_summary.py; doce ciclos reales; regresión004 | Verificado en referencias sintéticas |
| FR-013/014 | Pares iguales y contraste pendiente | test_costs_pdf_end_to_end.py; ejemplo60/40/38/2 | Verificado |
| FR-015 | Revisiones seleccionadas al corte | SecuenciaC1/B1/K1→B2→K2→C2; lecturas sin mutación | Verificado |
| FR-016 | Edificio/período/zona/corte/emisión/provisional | Renderer; test_report_requests.py; PDF descargado | Verificado |
| FR-017 | Captura coherente y render sin recaptura | test_cutoff_concurrency.py; test_source_capture.py; REPEATABLE READ | Verificado |
| FR-018 | Valores y positivos pequeños | Referencias reales1000/100000 y30mixto; extremos geométricos | Verificado en fixtures |
| FR-019 | Origen identificado y privacidad | test_quality_sources.py; calidad; test_observability.py | Verificación propia incluida en la suite final005 |
| FR-020 | Progreso/fallo/reintento | E2E con fallo admitido real controlado y fallo de transporte; T053 | Verificado |
| FR-021 | Archivo sin red y nombre estable | Docker --network none; offline.json; E2E | Apertura verificada; revisión física pendiente |
| FR-022 | Equivalencia al mismo corte | test_reproducibility.py:retención extendida sin cambiar hash funcional | Verificado |
| SC-001 | Legibilidad A4 | Preflight, extremos y revisión digital | Componente físico pendiente |
| SC-002/003/004 | Energía, finanzas y calidad | Referencias de us1.md–us4.md y sus pruebas | Verificado para casos automatizados; no generalizar a datos reales |
| SC-005 | Descargas íntegramente abiertas | Tres muestras offline, hash y una página | Verificado |
| SC-006 | 9/10 tareas con personas<=2min | Protocolo usability.md | Pendiente:sin participantes |

## Auditoría de documentación y propiedad

Los módulos005 documentan propósito, funciones/clases, fallos, retención, captura,
preflight e idempotencia. T011 usa la migración real `reports_005_initial`, enlazada
al head de003; T015 registra su módulo desde `main.py`, sin apropiarse del ciclo de
vida009. Los scripts de fixtures/harness solo sirven pruebas y no se copian al runtime.

La plantilla conserva las fuentes/licencia empaquetadas. Ningún secret o informe
privado del simulador se incorpora a las muestras sintéticas. No se alteró la selección
persistida003 ni checklists de revisión. La reanudación respeta las salidas históricas
del [registro de interrupción](implementation-checkpoint-2026-11-23.md), sin usarlas
como evidencia de nuevas ediciones. El bloque técnico de005 no requiere008/SMTP.

La cobertura integral007 y sus prerrequisitos por productor siguen en su propietario;
una prueba de protocolo no acredita automáticamente002:T065/003:T072.
