# Validación de la demostración por calendario

Fecha:2026-11-03. Solo entorno local y datos sintéticos; no declara aceptación de specs.

- Prueba de generación18:20: prefijo del día hasta18:15, sin muestras futuras.
- Prueba18:30: seis muestras18:15–18:30, con idéntica energía a la referencia diaria;
  CAT-01 se omite cuando el total es calculado.
- PostgreSQL aislado: admisión inicial18:20, rechazo18:29:59, aceptación18:30 en
  otra instancia del receptor y dos totales calculados exactos sin espera adicional.
- Política estricta: sus pruebas existentes mantienen900s e invariantes de persistencia.
- Transporte de calendario rechaza entornos diferentes de local.
- Respaldo completo antes de reiniciar consumo: pg_dump custom y pg_restore --list válidos.
  Cuentas y auditoría conservadas. No había configuración de costos.
- Arranque real a18:26: publicación inmediata de00:00–18:15 por SFTP;73 intervalos
  persistidos por cada categoría, incluyendo73 totales calculados. El último total
  de18,146kWh coincide con las seis contribuciones del mismo intervalo.

La configuración histórica no se reinterpreta durante reinicios ordinarios. Se autorizó
un reinicio explícito y único de consumo sintético con respaldo para repoblar el día.

Cierre real de18:30:

- SFTP terminó a18:30:00.134; el rango enviado fue únicamente18:15–18:30.
- La consulta del dashboard a18:30:13 mostró74 puntos y última lectura18:30.
- Total diario2099,932kWh = suma de parciales2099,932kWh; antes eran2073,653kWh.
- Las siete categorías tienen74 intervalos sin duplicados; CAT-01 es calculada.
- 121 pruebas PostgreSQL de consumo/contratos,74 unitarias de dominio,38 de interfaz,
  y suites del simulador incluyendo ventanas incrementales y restricciones de entorno.
- Alembic check: sin operaciones de actualización pendientes.

El respaldo anterior permanece en el almacén privado local del operador; no se versiona.
