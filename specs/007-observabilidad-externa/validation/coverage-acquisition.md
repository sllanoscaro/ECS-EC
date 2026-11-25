# Cobertura real001/002/003 — paso4

Corte2026-11-24. Pruebas en PostgreSQL18 y receptor/adaptadores instalados; no se
emiten resultados en nombre de los productores desde el test. Suite:
`backend/tests/integration/observability/test_acquisition.py` y casos de recepción de
`test_metrics.py`. [Regresión consolidada](step4.md).

| Operación / resultado | Evidencia comprobada |
| --- | --- |
| acquisition.receive success/rechazo | SFTP real asyncssh, EOF limpio frente a conexión abortada; sesión sellada y un terminal con spans authenticate/transfer/seal. No inventa recepción002 por aborto. |
| acquisition.process success/rechazo | Archivos nativos válidos/ilegibles y reenvío; resumen de archivos leído de resultados confirmados. Un archivo no equivale a una posición. |
| reception.accept success/rechazo | Cinco posiciones: tres aceptadas, una inválida y una duplicada; terminal lógico único y resúmenes iguales a002. Solo duplicados queda expected_rejection. |
| reception.accept inesperado/recuperación | Tres aceptadas, fallo con dos pendientes, dos incorporadas al recuperar: mismo attempt_ref, execution_ref nuevo, dos execution.completed y un reception.completed con cinco novedades. Relectura no emite otro cierre. |
| consumption.aggregate / retention | Casos reales de pendiente/cálculo, agregación, anticipo y retirada protegida reutilizados de su propietario. Logs/SDK contrastados con decisiones y commits. |
| consumption.query_detail / query_aggregates | HTTP real con autorización006, lectura y proyección; una operación objetivo por petición. Errores8/2 del caso conocido no duplican decisiones006. |

SFTP transmite bytes nativos sin campos007 añadidos. El contexto de recepción se
conserva en el sobre técnico de evaluación existente, enlaza publicación→adaptación→
incorporación y solo lleva UUID confiables; jamás CSV/JSON/medición, nombre o hash.
La consulta previa de contexto se hace antes de sellar, evitando autoflush prematuro
contra la invariancia SQL de sesión sellada. Una falla al leer contexto deja relación
no disponible y no cambia el negocio.

`test_live_acquisition_and_reception_traces` verifica entrega real y consulta Jaeger
por Programador además del SDK. Fallo de ejecución parcial conserva counts=null;
no existe terminal lógico hasta ganar el commit completed. El fallo técnico de
resumen/correlación no altera resultados. Un contexto perdido no fabrica padre.
