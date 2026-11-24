# Navegación, actividad y limpieza — 2026-11-24

`frontend/tests/e2e/identity.spec.ts`: recorrido real de ambos perfiles sobre la
exportación estática y el monolito; base separada `*_test`, reloj privado0600 mediante
`backend/tests/run_identity_browser.py`. No existe endpoint público de avance.

Se consultan1000kWh incorporados por002, filtros/Actualizar, costos persistidos y PDF
anual generado/descargado por005. Operador recibe403 en accesos directos de configuración,
suministro, perfiles, boletas y recálculo; los formularios privados no aparecen.
La red observable comprueba interactive en acciones de consumo/costos y background
en sondeos de reportes e introspección automática. Los clientes de navegación de costos
y catálogo/configuración001 ahora declaran interactive; `/auth/session` nunca renueva.

| Escenario con reloj interno | Resultado |
| --- | --- |
| Actualizar al minuto29 |Idle pasa de30 a59; absoluto no cambia|
| Llegar a59 sin nueva actividad |401; una petición interactive posterior no revive sesión|
| Solo background al29 e introspección con interactive |Idle permanece30; al30 devuelve401|
| Consultas periódicas cada29min |No superan el límite absoluto8h|
| pageshow después de vencer |Desmonta vistas y filtros privados, muestra ingreso; no reaparecen respuestas anteriores|
| Cierre entre pestañas |Invalida las dos vistas y la sesión del servidor|

El retorno a PDF y la lectura de Blob comparten validación/generación de respuestas006;
las pruebas005 de descarga/retorno y unitarias frontend complementan este recorrido.
[Administración](administration-ui.md), [matriz HTTP](operator-matrix.md).
HTTP loopback de pruebas no sustituye006:T086 sobre VPS/HTTPS real.
