# Distribución estimada del cargo de energía

Extensión de consulta autorizada al aprobar [Costos versión2](../../../.impeccable/mocks/costs-v2.png). Implementa FR-024 de la [spec](../spec.md); no modifica la fórmula BT4.3 ni sus snapshots.

`GET /api/v1/costs/calculations/{calculation_id}/distribution`

- Sesión normal y permisos actuales `costs.read` y `consumption.read`. Respuesta `Cache-Control: no-store`; IDs ajenos al edificio y ausentes responden404; sesión ausente401, permiso insuficiente403, UUID inválido422 y evidencia inconsistente/dependencia no disponible503.
- Solo lectura en una captura PostgreSQL coherente. No crea cálculos, boletas, contrastes ni cambia conservación. Se consume el puerto existente de snapshot de consumo001/002; no se accede a sus tablas desde costos.
- Devuelve `calculation_id`, `cutoff_at` propio, `state` (`available`/`unavailable`), `reason_code`, `energy_amount`, `other_amount`, `categories`, `unassigned_amount` y `unassigned_percent`. Decimales como cadenas o ausencia como `null`.
- Cada categoría incluye `id`, `name`, `state` (`available`, `incomplete`, `no_meter`, `no_data`), `energy_kwh`, `percent` y `estimated_amount`. CAT-01 es la base física; nunca constituye otro sector.
- `energy_amount` suma solo cargos `energia` netos y disponibles de la revisión guardada. `other_amount` es costo completo menos esa base si ambos están disponibles; si no, es `null`. No presume impuestos ni aplica tasas nuevas.
- La base general capturada debe coincidir con las identidades/revisiones actuales del detalle general, ser medida y cubrir todo el ciclo. Categorías medidas requieren cobertura completa y ausencia de cruces, retirada o diagnósticos. El detalle histórico retirado no se reconstruye.
- Los pesos se obtienen respecto a la energía general, sin renormalizar las categorías presentes. Las ausencias de medidor conservan `null`; el remanente aparece en «Sin asignar». Un cero medido permanece cero. Las discrepancias superiores al general y las bases generales cero no se distribuyen.
- Redondeo por restos mayores: importes a la precisión decimal de la suma neta presentada, porcentajes a centésimas, empates por identificador de categoría y residuo al final. Se conservan exactamente la base monetaria y 100,00 %. No se calcula dinero en el navegador.
- Motivos de indisponibilidad: `energy_charge_unavailable`, `general_evidence_changed`, `category_coverage_incomplete`, `zero_energy_basis`, `categories_exceed_general`. En esos casos las categorías no tienen porcentajes ni importes estimados. Energía/otros cargos pueden seguir disponibles de forma independiente.
- Consulta transitoria a las categorías disponibles actualmente, del ciclo histórico elegido. El corte propio puede ser posterior al del cálculo. No es una revisión financiera persistida ni una garantía de reproducción futura de esta estimación.

Esquemas fuente en `backend/src/ecs_ec/costs/schemas.py`; cliente generado en `frontend/src/lib/api/costs-types.ts`. Validación: `backend/tests/unit/costs/test_distribution.py`, `backend/tests/contract/costs/test_distribution_api.py`, `frontend/tests/unit/cost-distribution.test.tsx` y `frontend/scripts/review-costs.mjs`.
