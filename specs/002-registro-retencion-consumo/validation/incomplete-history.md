# Estados, datos tardíos y correspondencia

Fecha: 2026-11-02. [Aceptación](acceptance.md); T054–T063, FR-010..014/019 y SC-003.

- `test_aggregates.py`:3→4kWh y75→100% después de commit permitido; la variante con
  cuarto cero conserva3kWh y completa cobertura. Vacío devuelve null. Duplicados/rechazos
  no modifican aportes; un cruce horario puede aportar al día sin prorrateo.
- `test_aggregate_states.py`: antes de inicio/not_started, exactamente en inicio/ongoing,
  exactamente en fin/finished; filtro y cobertura independientes. Un microsegundo faltante
  conserva incomplete aunque el porcentaje mostrado redondee100; energía mayor que
  precisión50 sigue exacta.
- `test_history_late_data.py`: agregado previo preservado tras retirada y actualización
  tardía única visible en la primera consulta posterior al commit.
- `consumption-history-states.test.tsx` y regresiones001: carga/error/no fuente/sin datos,
  generación por categoría/período/zona/granularidad, error de B tras respuesta antigua A,
  reintento y limpieza privada de sesión. Misma respuesta/formateador en ambas vistas.
- `consumption-history-states.spec.ts`: API/DB/identidad reales,3kWh/75%→3kWh/100% con
  cero tardío, A demorada frente a B sin datos, fallo de transporte y reintento. Fronteras
  exactas del reloj privado mantienen bloque/filtro y muestran Aún no iniciado/En curso/
  Terminado. Tras retirada mantiene agregado y distingue detalle retirado. Navegador Tokio.
- `test_detail_periods.py`: el diagnóstico CAT-01 cruzado ya informa su identidad mediante
  `DetailRead.crossing_diagnostic_ids`; se retiró su xfail estricta y ambos casos pasan.
  GET no publica candidatos ni adelanta su próxima incorporación.

Los avisos incluyen cruce, extremos, base parcial, ausencia de base/configuración,
inicio de registro, cobertura y detalle retirado según evidencia. Sin datos, cero y
fallos de infraestructura no se confunden. SC-005 sigue esperando personas reales.
