# Trabajo con Spec Kit en ECS-EC

Antes de especificar, planificar, generar tareas, analizar o implementar, leer
[la arquitectura común](docs/architecture.md) y
[la hoja de ruta](docs/implementation-roadmap.md), además de la constitución en
`.specify/memory/constitution.md` cuando esté disponible. Estos documentos son contexto
compartido; `spec.md`, `plan.md`, `tasks.md` y los contratos de cada funcionalidad
permanecen en `specs/<identificador>/`.

- La spec-009 posee infraestructura, `core` y el mecanismo común de auditoría/eventos.
  La spec-006 posee cuentas, sesiones y autorización; specs-001/002, consumo;
  spec-007, observabilidad. La spec-008 posee notificaciones y sus adaptadores.
- Consultar la matriz de propiedad y los prerrequisitos de la hoja de ruta. No implementar
  una capacidad ajena como parte de los prerrequisitos de la funcionalidad activa.
  Una integración puede ampliar el registro común de rutas/ciclo de vida después de que
  exista su propietario; eso no transfiere la propiedad del módulo compartido.
- Al planificar una funcionalidad, leer su `tasks.md` existente si lo hay. Los archivos
  marcados **Borrador de traslado** conservan trabajo de la antigua spec-008: son entradas
  parciales para `$speckit-plan` y `$speckit-tasks`, no planes completos ni autorización
  para omitir historias de `spec.md`. Completar el diseño y regenerar las tareas antes
  de `$speckit-implement`, preservando el alcance trasladado y su trazabilidad.
- Las dependencias entre funcionalidades se identifican por capacidad, documento y ruta,
  nunca mediante un número `TNNN` sin indicar su spec. Los identificadores son locales.
- Mantener enlaces Markdown relativos al archivo que los contiene y rutas de código
  relativas a la raíz. Una ruta futura en una tarea no prueba que exista implementación.
- Mantener las plantillas de proyecto en `.specify/templates/overrides/`; no modificar
  scripts o skills distribuidos por Spec Kit para cambiar la estructura del proyecto.
- Respetar la selección explícita de funcionalidad. Para inspeccionar otra sin cambiar
  `.specify/feature.json`, usar `SPECIFY_FEATURE_DIRECTORY=specs/<identificador>` y
  `SPECIFY_FEATURE_NO_PERSIST=1` con los scripts oficiales.
- Toda tarea trasladada sigue pendiente. No marcar checklists de revisión ni declarar
  implementación o validación funcional a partir de una reorganización documental.
