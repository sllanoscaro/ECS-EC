# Estado parcial de implementación007

Fecha local2026-11-02. **Sin aceptación integral ni cierre de T065.**

T001–T021 y T023–T027 completadas:26/65. Emisor seguro con recursos acotados,
configuración técnica validada, provisión externa y MVP Viewer/acceso implementados.
Compose y guías existen y se ejecutaron; T028/T029 quedan pendientes por T022/PDF005.
T030 no cumple toda la matriz de prerrequisitos. US2–US4 y cierre siguen pendientes.

[Evidencia fundamental](emitter.md), [acceso real](access.md),
[dependencias](dependencies.md) y [prerrequisitos por propietario](prerequisites.md).
No se modifican checklists de revisión ni tareas de otras funcionalidades.

## Verificación final ejecutada

- `uv sync --locked`:66 paquetes resueltos/64 verificados; Python3.14.4/FastAPI0.162.0.
- `uv run pytest backend/tests -q` con PostgreSQL18 real, dos stacks técnicos aislados,
  CA confiable y navegador: **476 passed,1 skipped**,198.27s. La omisión explícita es
  la matriz PDF005; no se acepta mediante una ruta inexistente. Incluye67 pruebas
  fundamentales, prueba PTY real, timeout/concurrencia reales y los proveedores existentes.
- El harness Playwright ejecutó **3 recorridos**: Viewer/logs/métrica/traza, navegación
  funcional/admin/historial frente a Operador y revocación con cookies/enlace conservado.
  Monolito real con export compilado, cuentas006 y DB separada; validación HTTPS activa.
- `npm --prefix frontend run typecheck`: correcto. Vitest: **53 tests/23 archivos** pasan.
- `docker build -t ecs007-validation-app:local .`: correcto; imagen final
  `sha256:714760fc4a89c601c2c6ccf300cda95e55dbaccdc6f5f4b9904fbfaa97a8c2ed`.
- Validadores de Alloy/Loki/Jaeger, `nginx -t` y Compose config pasaron en imágenes fijadas.
- `git diff --check`, enlaces locales nuevos y docstrings Python propios: correctos.
- `requirements.md`:16/16 revisados, sin cambios. `.specify/extensions.yml` ausente;
  no hay hooks before/after implement que ejecutar.

Se cerraron solo los proyectos técnicos `ecs007-validation` y `ecs007-other-validation`
tras la prueba. Los datos/posiciones/certificados privados permanecen fuera del repo;
no se borraron volúmenes funcionales ni se detuvo/recreó el contenedor PostgreSQL previo.
La DB exclusiva creada para pruebas es `ecs_observability_test`, distinta de las reales.


Limitaciones materiales: emisor básico termina operaciones ordinarias; las semánticas
especiales de recepción/PDF y links durables tienen tareas US2 pendientes. Ningún
productor001–006 se declara instrumentado por existir el emisor. Dashboard inicial
muestra observaciones/cobertura desconocida; no implementa todavía todo US3. T056
cuotas persistentes/corte90%, T059 retención24h/GC y T061 personas siguen pendientes.

Para continuar, completar los proveedores003/005 y llamadas de instrumentación en sus
propietarios; retomar T022 y la cadenaT028–T030 antes de las fases restantes conforme
al grafo, conservando las tareas pendientes y sin reemplazar dominio por fixtures.
