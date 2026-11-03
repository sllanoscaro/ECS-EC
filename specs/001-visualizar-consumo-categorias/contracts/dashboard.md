# Consulta del dashboard diario

Integración de las referencias aprobadas de dashboard y consumo. Pertenece a consumo001 y utiliza el puerto de lectura002 y la autorización006 existentes; no incorpora mediciones ni modifica almacenamiento.

## HTTP

`GET /api/v1/consumption/dashboard`

Requiere sesión normal con `consumption.read`; errores de identidad siguen el contrato006. Respuesta `Cache-Control: no-store`. No recibe zona, edificio o datos de medición del navegador. La zona proviene de la instalación y el instante de corte del reloj del servidor. `X-Session-Activity: background` no renueva la actividad de usuario; el refresco manual es `interactive`.

Respuesta tipada por `DashboardView` en `backend/src/ecs_ec/consumption/schemas.py`, publicada también en el OpenAPI de la aplicación:

- `timezone`, `cutoff_at`, `period: {start,end,timezone}`: día local real, con límites y offsets explícitos; el corte puede estar dentro del día. El día puede durar 23 o 25 horas.
- `categories`: siete proyecciones, cada una con `id`, `name`, `source_mode` (measured/calculated/mixed/unavailable), `base_categories`, `energy_kwh` (cadena exacta o null), `coverage_percent` (cadena), `covered_duration_us`, `elapsed_duration_us`, `last_reading_at` (instante o null) y `state` (available/incomplete/no_data/no_meter).
- `series`: bloques completos de quince minutos desde el inicio real del día hasta el corte. Cada bloque contiene `start`, `end`, `energy_kwh` y `coverage_percent`. No se generan lecturas futuras. Un bloque sin aportes tiene energía null; un cero medido conserva la cadena cero.
- `chart_excluded_count`: lecturas del total diario que no caben completamente en un bloque terminado de quince minutos. La vista advierte esa diferencia sin prorratearlas.

Las categorías y su serie se capturan en una sola transacción `REPEATABLE READ READ ONLY` y con el mismo corte. Los errores de evidencia se traducen a `consumption_unavailable`/503, sin exponer excepciones internas ni convertir un fallo en ausencia de datos. La consulta no modifica mediciones, agregados, revisiones o plazos de retención.

## Fórmulas y límites

La energía diaria suma solamente lecturas completamente contenidas entre inicio del día y corte. Se suman cuantos enteros de 10^-15 kWh y se convierte el resultado a cadena exacta, sin depender de la precisión ambiental de Decimal. La ausencia de lecturas produce null. Se rechaza evidencia solapada para evitar doble conteo. CAT-01 proviene de su propio almacenamiento: nunca se vuelve a sumar el consumo de las seis categorías parciales para sustituirla.

Cobertura = duración de lecturas disjuntas contenidas / tiempo real transcurrido del día. No incluye como vacíos las horas futuras. La presentación trunca a dos decimales para que un hueco pequeño no redondee a 100 %. A medianoche, con duración cero, la interfaz muestra un guion en vez de un porcentaje con denominador cero.

La serie de quince minutos utiliza las mismas lecturas, pero únicamente cuando están completamente contenidas en su bloque. Se pueden sumar lecturas menores completamente contenidas; no se fracciona una lectura horaria en cuatro valores supuestos. La energía parcial disponible y la cobertura de cada bloque permanecen explícitas. Esta es una proyección de lectura, no un nuevo nivel de agregados persistidos ni una nueva regla de recepción.

El navegador intenta refrescar a los 60 segundos de terminar cada consulta. La hora anunciada corresponde al siguiente intento de consulta, no a un compromiso de adquisición ni a `next_admissible_at` de recepción002. La demora real depende de red, navegador y disponibilidad; la respuesta siguiente vuelve a calcular el día desde el reloj del servidor.

## Evidencia local

Pruebas puras: `backend/tests/unit/consumption/test_dashboard.py`. Prueba HTTP con identidad y PostgreSQL reales: `backend/tests/integration/consumption/test_dashboard.py`. La aceptación integral de consumo001/002 no se altera por esta integración de interfaz.
