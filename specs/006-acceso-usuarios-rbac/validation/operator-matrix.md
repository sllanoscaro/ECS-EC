# Matriz local de lectura — 2026-11-03

006:T042 completada con proveedores reales001/002/004 y sesiones006 sobre PostgreSQL18.
Ambos perfiles consultan catálogo de siete categorías, detalle y agrupaciones, ciclos,
boletas, historial y la referencia de cálculo persistido. El caso físico1000kWh produce
el cálculo004 real y boleta manual antes de consultar. Todas las consultas son no-store.
Las filas completas de tablas de negocio se conservan exactamente: filtros/lecturas no
modifican mediciones, tarifas, boletas, configuración ni conservación.

Adicionalmente se verifican consultas reales al minuto29→vencimiento59, sondeos e
introspección interactive sin renovación→vence30 y límite absoluto8h que ninguna
actividad revive. El reloj es una inyección interna de prueba; no hay API de avance.

006:T049 sigue pendiente de PDF005 real y de las integraciones completas T046/T048:
no se declara aquí SC-002/SC-003 íntegro ni acceso/replay/descarga de un PDF inexistente.
Los clientes/vistas disponibles conservan su integración previa; la clasificación de
actividad de todas las acciones y retorno seguro a PDF siguen en el alcance pendiente
T048/T050. El recorrido de navegador propio006 sí se repitió; ver [regresión](regression.md).
