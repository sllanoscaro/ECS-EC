# US3 — períodos, contención y zona del edificio

2026-11-03. Consulta001 sobre almacenamiento002 real, PostgreSQL18.3 desechable.
`test_detail_periods.py` verifica contención exacta, antes/después, cruces de cada límite,
cruce de ambos contado una vez para registros y diagnósticos, conservación sin cambios
por lectura y dos horas23:00 de Santiago con offsets-03:00/-04:00 (2025-04-05).
El proveedor002 ya expone diagnósticos cruzados;001 los proyecta incluso sin filas.
`test_detail_queries.py` verifica captura repetible y extensión inicial global.

Playwright `consumption.spec.ts` corre con navegador `Asia/Tokyo`, ambos perfiles y
fixtures físicos/calculados. Conserva selección al cambiar categoría, rechaza rango
invertido sin perder la consulta anterior, consulta períodos anteriores/posteriores sin
filas y acepta los límites de la hora repetida. Gráfico/tabla se comparan contra API real.
El fixture de navegador no contiene lecturas en esa hora repetida: las dos lecturas12/8
con offsets distintos se incorporan y verifican en PostgreSQL por la prueba de servidor.

Las primeras nuevas pruebas usaban límitesZ incompatibles con el contrato de selección
local: se corrigió el fixture a los offsets del edificio, sin relajar la validación.
Una espera de respuesta Playwright capturaba una solicitud anterior; ahora correlaciona
categoría y comienzo de selección. No se modificó producción para ocultar esos fallos.

Comandos y resultados del incremento en [aceptación](acceptance.md).
FR-011..013 y SC-002/004 verificados localmente; no acredita personas ni VPS.
