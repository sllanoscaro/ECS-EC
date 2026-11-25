# Matriz transversal SC-002/004 — paso4

Corte2026-11-24. Todas las filas iniciales de
[contrato](../contracts/integrations.md) tienen productor instalado y pruebas sobre
sus resultados reales. No se toma la existencia de rutas como evidencia.

| Filas del catálogo | Evidencia |
| --- | --- |
|003 receive/process;001/002 accept/aggregate/retention/detail/aggregates | [Recepción y consumo](coverage-acquisition.md) |
|004 calculate/compare/query;005 generate/query/download | [Negocio](coverage-business.md) |
|006 authenticate/authorize/session;001/004/006 administration.change/query | [Negocio](coverage-business.md) |
|Concurrencia, reinicio, intento vs ejecución, contexto perdido, nueva publicación | `test_correlation.py`, `test_acquisition.py`, `test_costs_reports.py`; relaciones explícitas, nunca nombres iguales |
|Navegación entre señales, límites, referencias | `observability-diagnosis.spec.ts`, [métricas](metrics.md) |

SC-002/004 verificados en el alcance técnico local. Rechazo esperado conserva su
semántica, fallos usan código seguro/ERROR, etapas no cuentan como operaciones y
continuación durable no modifica fuentes.008 no pertenece al catálogo inicial.
Los conteos y cortes reproducibles están en [paso4](step4.md); no acreditan personas,
VPS, TTL/GC ni aceptación007 integral. [Aislamiento](isolation.md).
