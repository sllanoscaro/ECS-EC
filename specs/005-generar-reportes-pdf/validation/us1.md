# US1 — generación y descarga

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

Se verificaron las tres escalas contra002/004 reales, selección actual provisional,
pasado vacío, errores por campo y futuro rechazado. Admisiones repetidas con la misma
clave conservan identidad; cuerpos distintos producen409 y nuevas claves producen
otra captura. Leer/descargar conserva bytes, hash y plazos, sin incorporar mediciones.

`test_real_pdf_pipeline.py` reabre PDFs con1000kWh y100000CLP de fuentes reales.
`test_report_requests.py`, contratos HTTP y fundaciones verifican PostgreSQL y acceso.
El E2E `frontend/tests/e2e/reports.spec.ts` pasó: día/mes/año, descarga con nombre,
progreso, fallo de composición durable, campos conservados, respuesta de red incierta
con clave reutilizada, sesión ausente e ingreso normal al mismo reporte.

La inyección de composición vive solo en `backend/tests/run_reports_browser.py`,
protegida por entorno/base `_test` y archivo0600. No hay endpoint ni parámetro público
de inyección. La aplicación sigue usando sus productores, worker y transacciones reales.
