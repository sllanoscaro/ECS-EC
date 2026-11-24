# Ampliación común coordinada con PDF — 2026-11-24

**Capacidad usada por005 implementada y verificada;007 sin aceptación integral.**
Ver [entrega técnica005](../../005-generar-reportes-pdf/validation/acceptance.md).
Se completan007:T031/T032:28/65 tareas con evidencia. Las demás casillas conservan
sus prerrequisitos y alcance completo; no se aceptan por existir métodos del emisor.

En `backend/src/ecs_ec/observability/lifecycle.py` se implementaron admisión/terminal
PDF, terminal de ejecución/recepción, continuación confiable con nueva ejecución y
liberación de spans sin cerrar una operación lógica. Una ejecución exitosa puede
emitir su resumen y después el terminal lógico; una ejecución parcial fallida usa
counts=null y no cierra el intento. El productor conserva la responsabilidad de
informar la transición durable ganada; el emisor no hace commits ni deduplica negocio.
La liberación permite clasificar rechazo/fallo sin inventar una generación terminada.

| Tarea007 | Evidencia y estado |
| --- | --- |
| T031 | Contrato de instrumentación y suites fundamentales: terminal único, métodos/estados, admisión separada, lectura sin ejecución y fallo parcial sin conteos. Completa. |
| T032 | Contextos concurrentes, continuación serializada, traza nueva, links internos confiables y namespaces/HMAC. Completa. |
| T033 | Test de protocolo3commits+2pendientes con002 real. Preparación parcial: las llamadas al emisor desde el test no acreditan un adaptador002 instalado ni la matrizSFTP completa. |
| T034 | Pruebas reales005 y revisiones004; el archivo007 reexporta casos existentes. La cobertura propia de operaciones004 y todos sus resultados permanece pendiente. |
| T035 | Reutiliza pruebas reales006/001; no completa toda la administración004 ni su matriz007. Pendiente. |
| T037/T038 | La capacidad común de terminales/continuación usada por005 está probada; las tareas permanecen pendientes por su alcance transversal y prerrequisitos T033–T035. No confundir capacidad disponible con aceptación de todas sus integraciones. |

`test_observability.py` de005 observa admisión/terminal una vez, correlación de worker,
etapas, resultados y continuidad con cola saturada/adaptador caído. Resultado/functionalevent009
sigue siendo durable aunque la señal técnica se pierda. Contexto técnico y metadatos de
transporte no entran en el PDF ni en su hash funcional.

Actualización2026-11-24: recepción instalada002:T065 e instrumentación propia003:T072
completadas en el paso3 con contexto durable y emisor real. [Regresión](../../006-acceso-usuarios-rbac/validation/regression.md). La cobertura
integral007, visores, métricas, cuotas y retención real siguen en el paso4. La entrega
005 no depende de que esos visores o008/SMTP estén disponibles. No se modificaron
checklists de revisión ni se declara cerrado T065 de007.
