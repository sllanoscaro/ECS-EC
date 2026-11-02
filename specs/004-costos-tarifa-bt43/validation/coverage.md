# Trazabilidad004

2026-11-02. Cobertura funcional local con proveedores reales; resultados consolidados
 en [aceptación](acceptance.md). No equivale a evaluación con personas ni a un pliego real.

| Requisito | Implementación y evidencia |
| --- | --- |
| FR-001 | CostHistory/CostChart/CostTable, páginas de consulta/administración; [US1](us1.md), [US4](us4.md). |
| FR-002 | snapshots.capture consume CAT-01 física001/002; test_foundations/test_engine rechazan calculada y fuente distinta. |
| FR-003 | SupplyEditor/ProfileEditor, PUT suministro y calendarios documentados; [US3](us3.md). |
| FR-004 | profiles/engine, publicación única al corte, fuentes/precios ausentes limitados, test_profile_vigencies. |
| FR-005 | ComponentDetail, CostTable y captura de cantidad/unidad/regla/precios/tributación/redondeo. |
| FR-006 | engine.complete_coverage y segmentación exacta;1000×100=100000 y500×100+500×110=105000. |
| FR-007 | demand.block_power:10kWh/0.25h=40kW; test_demand y navegador rechazan resolución horaria. |
| FR-008 | demand.bases/top_two, meses distintos60/50→55; evidencia mensual explícita y ventana documentada. |
| FR-009 | calendar/is_peak/month_bounds, UTC/IANA y hora repetida; test_demand/test_profile_vigencies. |
| FR-010 | engine agrupa cargos aplicables/impuestos; precio ausente no es cero, bases incluidas no reciben doble impuesto. |
| FR-011 | CalculateRequest/BillInput preservan límites efectivos/declarados/criterio/zona; MonthEvidence valida identidad/ciclo/mes. |
| FR-012 | Segmentos por revisión y precios por intervalos físicos, fijo/demanda sin prorrateo inventado. |
| FR-013 | Cadena monetaria autoritativa común a gráfico/tabla; cost-breakdown.test y ocho recorridos web. |
| FR-014 | Tres estados independientes, provisional explícito, total nullable y causas funcionales; [US4](us4.md). |
| FR-015 | BillEditor/API, cantidades leídas/facturadas/documento y líneas firmadas independientes; [US2](us2.md). |
| FR-016 | comparison/selected_pair: alineación y cálculo−facturado, denominador absoluto, cero→null; captura sin retroceso. |
| FR-017 | ExcludedLine y ComparisonTable mantienen deuda/abonos no equivalentes fuera del subtotal. |
| FR-018 | Escrituras de boleta solo en tablas004; capturas/mediciones/perfil no se actualizan para ajustar importes. |
| FR-019 | Revisiones/ETags/antecesor esperado/idempotencia; carreras PostgreSQL y respuesta perdida en navegador. |
| FR-020 | reproduce verifica hash/versión y evalúa entradas capturadas; manipulación/versiones desconocidas rechazadas. |
| FR-021 | retention.protect recorre padres/evidencia con máximo no decreciente; aniversario009, retirada002 real. |
| FR-022 | Doce ciclos/páginas5/5/2 con corte firmado, filtros y consulta estable; test_history_pagination. |
| FR-023 | InputEvidence preserva tablero/suministro/perfil/mediciones/histórico/políticas/máximos; ReproductionDetail. |
| SC-001 | Referencias exactas de test_engine/test_demand; perfil de todos los cargos:neto1625+impuesto309=1934CLP. Casos sintéticos completos aprobados. No generaliza a precios reales ausentes. |
| SC-002 | test_comparison/API y navegador:105/100, cero, signos, impuestos, exclusiones y correcciones. |
| SC-003 | Casos de cobertura/histórico/resolución/precio/estrategia/vigencia; ningún importe desconocido sustituido por cero. |
| SC-004 | Reproducción y retención verificadas con reloj controlado/retirada real; no afirma observación transcurrida durante un año. |
| SC-005 | Mismos recursos/corte, igualdad exacta accesible gráfico/tabla y estados; pruebas unitarias/web aprobadas. |
| SC-006 | **Pendiente**: T064 y [protocolo humano](usability.md); sin participantes ni tiempos inventados. |

Integraciones futuras: contrato productor005 y cost.failed009 para consumidor008 en
[entrega](producer-handoff.md). No implementan ni acreditan las funcionalidades consumidoras.
