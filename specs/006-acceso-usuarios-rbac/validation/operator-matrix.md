# Matriz HTTP con proveedores reales — 2026-11-24

Evidencia006:T043/T046/T049: `test_read_integrations.py`, `test_report_access.py`,
`test_system_administration.py` y contratos006/005, ejecutados con PostgreSQL18.3.
Los fixtures componen001/002/004/005/006 reales; el worker genera los bytes PDF.

| Operación | Sin sesión | Operador | Administrador técnico |
| --- | --- | --- | --- |
| Siete categorías, detalle y agregaciones001/002 |401|200|200|
| Ciclos, boletas, historial y cálculo persistido004 |401|200|200|
| POST PDF005 con CSRF/origen válidos |401|202|202|
| Estado y descarga PDF005 |401|200|200|
| GET configuración001/suministro/perfiles004 |401|403|200|
| PUT configuración/suministro; POST perfiles/boletas/recálculo |401|403|Permitido con entrada/precondición válidas|

PDF es permiso de lectura aunque su admisión use POST; no concede mantenimiento.
Sin CSRF/origen válido la admisión devuelve403. Replay conserva respuesta/identidad;
cierre, desactivación o nueva versión de autorización deniegan estado, descarga y replay
con401/no-store, sin bytes ni metadatos. Una transacción REPEATABLE READ vuelve a
consultar cuenta/sesión antes de admitir o reproducir una respuesta antigua.

La captura completa de tablas001/002/004 antes/después comprueba que consultas y
rechazos conservan filas, versiones, boletas, perfiles y conservación. La generación005
sí persiste su propia captura y extiende protección de evidencia según su contrato.
[UI/actividad](operator-ui.md), [administración](system-administration.md),
[regresión y límites](regression.md). SC-002/SC-003 y descarga vigente SC-004 comprobados
localmente; esto no acredita VPS ni evaluación humana.
