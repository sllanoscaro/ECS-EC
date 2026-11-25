# Métricas, continuidad y replay — paso4

Corte2026-11-24. Catálogo cerrado en `observability/queries.py`; panel nativo Grafana
`ecsec-coverage-panel` con conciliador puro `reconcile.mjs`. Fuente manual, sin build
ni dependencias remotas; React/@grafana/data vienen de la imagen fijada. Trece pruebas
Node cubren cortes nanosegundo, N/D, duraciones, pérdidas y señales independientes.
[Comandos/resultados consolidados](step4.md).

| Caso real | Esperado / comprobado |
| --- | --- |
|Diez lecturas001 HTTP | Ocho200, dos503; operations_total10 y unexpected_error_percent20. Se excluyen etapas y authorize006. |
|Recepción002 de cinco posiciones | Tres aceptadas, una inválida, una duplicada; cinco evaluadas/tres novedades; un resumen lógico. |
|Tres aceptadas/fallo/dos recuperadas | Dos ejecuciones, un intento completo, cinco novedades; error por ejecución50%, lógico0%. |
|Duraciones100/200/300ms | Media200/p50200/p95290; eventos sin duración excluidos y denominador ausente permanece nullable. |
|Ventanas adyacentes | Loki consultado en extremos a1ns: `[inicio,fin)` entrega2+1, sin duplicar frontera. Evaluación LogQL en fin−1ns. |
|Ventana cerrada/browser | Heartbeats reales encuadran diez consultas, espera real>45s, Loki y Jaeger consultables; panel muestra ambas coberturas y10/20%; error de consulta muestra unknown/N/D. |
|1000 referencias | Dos streams técnicos por severidad/resultado, solo cinco dimensiones; ninguna referencia/filename/detected_level se convierte en etiqueta. |
|Replay idéntico | Logs recuperan1000 terminales únicos, agregado nativo llegó a1001. Panel contrasta y declara partial/replay_en_agregado; proporciones N/D. |
|Pérdida de posiciones/reinicioAlloy | Nueva entrega después de reiniciar comprobada y collector_restarts_total incrementado. Reread puede repetir entregas o perderlas por rate-limit; no se declara reparación histórica. |
|Jaeger/OTLP caído / logs disponibles | Logs conservan evidencia; traza ausente incluso tras recuperar no prueba inexistencia. |
|Alloy/Loki caído / trazas disponibles | Jaeger consultable conserva evidencia propia; logs no heredan salud de trazas. |

No cambiar etiquetas ni ajustar timestamps para ocultar inflación por replay. El
panel nativo de agregados se titula «Entregas brutas de terminales — no usar como total
lógico». Valores exactos solo en cortes conciliados; >=10000 filas, receptor fallido,
política incompatible o continuidad no verificable limitan el resultado. No hay
promedio de percentiles ni denominadores clamp_min. Filtros/referencias son campos,
no dimensiones. Consulta de trazas bajo Basic actual verifica persistencia independiente.

El panel conserva shell/tema de Grafana; cobertura primero, UTC/corte/política/unidades,
reintento y seis terminales diagnósticos. Capturas y revisión responsive en
[documentación](documentation.md). El modo0.1 informa limitación solo de trazas;
logs terminales/control siguen sin muestreo.
