# Revisión de documentación003

2026-11-03. Inspección de contratos/docstrings en simulador, acquisition, pruebas y
migración; revisión AST final:67 archivos Python/278 funciones, métodos y clases sin
docstrings ausentes. La migración también identifica su generación y revisión manual.
Los docstrings describen responsabilidad, entradas/resultado, fallos y efectos aplicables;
las fórmulas de deltas y conversión exacta, tiempoUTC/monotónico, calendario de retención
y uso de adaptadores internos AsyncSSH están junto al código.

La migración identifica generación Alembic y revisión manual de constraints/triggers;
regenerar con revision --autogenerate y revisar, nunca reemplazar una migración aplicada.
No se generó ni cambió el core compartido desde003. README del paquete, quickstart,
despliegue, prerrequisitos, tareas y aceptación distinguen código ejecutable, evidencia
histórica, nuevas pruebas y gates externos. No se alteran checklists de requisitos.
