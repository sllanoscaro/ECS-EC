# Contratos internos: Costos BT4.3

Las interfaces viven dentro del monolito; no son servicios desplegables ni endpoints públicos. Sus implementaciones reales son prerrequisitos de aceptación. Los dobles sirven únicamente a pruebas aisladas.

## Puertos requeridos

| Puerto | Entrada | Salida/garantía |
| --- | --- | --- |
| `Identity.authorize` | Principal actual, acción, edificio | Lectura Operador/Administrador; escritura de perfil/boleta/recálculo solo Administrador; denegar Programador. |
| `Consumption.read_general_snapshot` | Edificio, ciclo, corte, unidad de trabajo | CAT-01 física asociada al suministro, intervalos/energía normalizada, procedencia/revisión y cobertura. CAT-01 calculada se devuelve como limitación, nunca como sustitución. |
| `Consumption.read_demand_history` | Suministro, meses/ventanas de punta, corte | Bloques exactos de 15 minutos o potencia integrada válida, máximos y cobertura por mes; sin reconstrucción desde datos horarios. |
| `FunctionalAudit.append` | Actor/proceso, acción, entidad/revisión, resultado | Auditoría durable con causas funcionales saneadas. |
| `EventWriter.append` | Sobre de evento, misma unidad de trabajo válida | Evento único en `audit/models.py`; no depende de consumo por 008 ni de SMTP. |
| `Clock` | — | Instantes UTC y reloj controlable solo internamente en pruebas. |

El núcleo común procede de [plataforma009](../../009-fundaciones-plataforma/plan.md) y la [arquitectura](../../../docs/architecture.md); no depende de completar 008 ni de sus tareas de correo. Faltantes de las specs-001/002/006 quedan como dependencias explícitas de implementación.

## Costs.read_snapshot — productor para spec-005

`Costs.read_snapshot(building_id, start, end, cutoff_at, principal, *, unit_of_work=None)` se implementa en `backend/src/ecs_ec/costs/snapshots.py`. Puede recibir la unidad de trabajo de lectura REPEATABLE READ del llamador para compartir captura con consumo.

Precondiciones: principal autorizado actual, edificio único, fechas con offset, `start < end`, corte único y acceso normal de spec-006. No crea cálculos ni revisiones. No requiere alertas ni correo.

Salida inmutable `CostsSnapshot`:

- Identidad del suministro, ventana solicitada, zona, corte, versión del esquema y referencias de captura.
- Ciclos cerrados con fin efectivo en `[start,end)`; cada ciclo una sola vez. Seleccionar primero el último cálculo y la última revisión de boleta visibles al corte; después la última comparación visible cuyo `calculation_id` y `bill_revision_id` coincidan exactamente con ambos. No retroceder a revisiones anteriores para encontrar una comparación. El inicio de un ciclo puede ser anterior al período del reporte y queda indicado.
- Por ciclo: límites efectivos/declarados, estado temporal/suficiencia/ejecución, cantidades, componentes, moneda/base tributaria, importes disponibles y total completo nullable, versiones y evidencia.
- Totales disponibles por moneda/base/concepto compatibles y conteos de ciclos completos/parciales/no calculables; no presentar una suma de parciales como costo completo.
- Contraste agregado únicamente sobre el mismo conjunto de pares calculado/facturado alineados. Sus dos subtotales y diferencia usan exactamente esos pares; deuda/ajustes no equivalentes figuran aparte. Si el subtotal facturado es cero, porcentaje null.
- Por ciclo, `comparison_status=available` si existe comparación del par exacto; `missing_for_selected_revisions` si están ambos recursos pero falta esa comparación, con referencias/valores disponibles y diferencias null. En este último caso el ciclo no integra el contraste agregado. `no_calculation`/`no_bill` distinguen recursos ausentes (si faltan ambos, `no_calculation`). El porcentaje null por facturado cero no cambia un estado `available`.
- `no_closed_cycles`, `no_bills` y `no_comparable_pairs` como razones distintas cuando corresponda; no sustituir por cero una cantidad ausente.

El consumidor PDF no recalcula BT4.3, no prorratea ciclos ni vuelve a sumar categorías. La captura se compone con datos de consumo al mismo corte y preserva referencias/versiones; cambios posteriores quedan fuera del reporte existente.

Ejemplo de selección: C1/B1/K1 se compara a corte A; corregir B1 a B2 antes del corte B, sin otra comparación, devuelve C1/B2 con `missing_for_selected_revisions`, diferencias null y K1 solo en su consulta histórica. Crear K2 para C1/B2 lo habilita a cortes posteriores; recalcular C2 vuelve a dejar el par C2/B2 pendiente hasta su propia comparación. Repetir el corte A conserva C1/B1/K1. Ninguna lectura crea K2 ni modifica K1.

## cost.failed — productor durable para spec-008

Sobre compatible con [integraciones 008](../../008-notificaciones-programables/contracts/integrations.md):

| Campo | Regla |
| --- | --- |
| `event_id` | UUID estable generado por productor confiable |
| `type` | `cost.failed` |
| `source_module`, `source_entity_id`, `source_revision` | `costs`, id de cálculo fallido, revisión; identidad única junto al tipo |
| `occurred_at`, `recorded_at` | UTC; separar fallo y registro del período de medición |
| `category_id`, `measurement_window` | CAT-01 y ventana de cálculo cuando sean conocidas; no inferir de fecha del error |
| `accepted_new_data` | `false` |
| `functional_result`, `safe_payload` | Estado fallido, código funcional aprobado, edificio/ciclo y referencias opacas; sin importes individuales innecesarios, secretos o excepciones |
| `correlation_ref` | Referencia opaca confiable |

Persistir resultado fallido y evento en la misma transacción válida. Si falla el cálculo y su transacción aborta, registrar el resultado/evento juntos en otra; si falla su registro, no afirmar que el evento existe. Un fallo de configuración/dato insuficiente esperado conserva el estado limitado sin emitir un evento técnico por cada consulta. Repetición de una misma operación devuelve la misma identidad; un recálculo explícito distinto puede producir otra revisión/evento.

La ausencia o caída del consumidor 008 no afecta cálculos, persistencia ni consulta. No existe importación de `notifications` desde `costs` o `audit`. El consumidor decide reglas/destinatarios y respeta permisos actuales sin modificar el resultado productor.

## Implementación verificada localmente

La fachada compuesta vive en `backend/src/ecs_ec/costs/services.py`. Los dos proveedores
físicos001/002 reciben edificio, intervalo, corte y UoW real; devuelven bloques originales
normalizados/revisiones/causas.004 calcula sus máximos únicamente desde bloques reales de
quince minutos con cobertura demostrada; datos horarios no se reconstruyen.

`CostsSnapshot` v1 es un DTO Pydantic inmutable, serializable con `model_dump(mode="json")`.
La captura suministrada debe usar REPEATABLE READ o serializable; otra aislación devuelve
`snapshot_isolation_required`. Su llamador resuelve un principal006 actual antes de leer.
Motor `bt43-v1`; hash canónico incluye versión e InputEvidence. Una reproducción no consulta
precios ni mediciones actuales. Ver [entrega](../validation/producer-handoff.md) y
[validación concurrente](../validation/us4.md). La integración PDF005/consumidor008 sigue
siendo trabajo de sus propietarios.
