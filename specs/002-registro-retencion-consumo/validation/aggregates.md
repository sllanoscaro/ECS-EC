# Consulta agrupada y proveedores reales

Fecha: 2026-11-02. [Aceptación vigente](acceptance.md).

La fachada 001 existente recibe `AggregateSelection` y consulta agregados persistidos
002 en REPEATABLE READ READ ONLY. El router único incorpora el GET autenticado; 006
aplica permisos y no-store antes de validar. Los límites HTTP conservan zona, offset y
microsegundos; energía, porcentaje y duraciones son cadenas. No se crean filas por GET.
El catálogo, configuración y detalle 001 permanecen integrados con el mismo proveedor.

| Tareas / requisitos | Evidencia ejecutada |
| --- | --- |
| T028/T033/T034, FR-007..012 | `backend/tests/integration/consumption/test_aggregates.py`: siete categorías/cuatro niveles, suma propia CAT-01 física, calculada20+30=50,3→4kWh/75→100%, cero frente a vacío, máximo individual+quantum=10^30 agregado, contención/cruces/extremos,25 horas repetidas y febrero bisiesto29 días. Primitivas/proyección comprueban coeficientes mayores que precisión50 sin simular billones de filas. |
| T029/T035/T036, FR-013 | `backend/tests/contract/consumption/test_aggregate_http.py`: sesión real,200/401/403/404/422/503, no-store, selección exacta, microsegundos, null explícito y errores saneados. |
| T031/T037..T040 | `frontend/tests/unit/consumption-history.test.tsx`: selector, cero/hueco, energía minúscula/grande, texto exacto por foco/tooltip y tabla, cobertura incompleta aunque redondee100. |
| T032/T044, SC-002 | `frontend/tests/e2e/consumption.spec.ts`: perfiles Administrador/Operador, siete categorías, Hora/Día/Mes/Año con datos, cada fila/símbolo contra API real. Navegador Asia/Tokyo; edificio America/Santiago; conserva selección. Build estático aprobado. |
| T030/T041..T043 | `backend/tests/contract/consumption/test_history_consumers.py`: ventana completa en otra zona sin escritura, cursor ligado a selección, revisión estable/nueva ventana tras dato tardío, general física frente a calculada limitada, resolución horaria insuficiente para demanda y reporte de siete categorías al mismo corte/UoW. |

Los puertos de consumidores están implementados en `consumption/queries.py`; no hay
costos, tarifas, PDF ni programación/correo implementados desde002. La integración conjunta
con004/005/008 sigue pendiente. Una fecha de corte sola no reproduce snapshots antiguos:
el consumidor conserva el snapshot copiado y sus referencias antes de liberar la UoW.

Los tipos002 de frontend son manuales y citan `contracts/http.md`; los tipos001 siguen
su generador. La ampliación `detail_withdrawn` del contrato compartido001 y sus tipos
regenerados conserva el aviso de retirada sin reconstruir el original.
