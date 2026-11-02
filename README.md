# ECS-EC

Sistema de monitoreo eléctrico de un edificio, con arquitectura monolítica modular.
Estado actual: especificaciones y planificación; la aplicación aún no está implementada.

- [Arquitectura compartida](docs/architecture.md): stack, módulos, datos y entornos.
- [Hoja de ruta](docs/implementation-roadmap.md): propietarios, dependencias, estado y uso de Spec Kit.
- [Instrucciones del repositorio](AGENTS.md): carga de contexto común para trabajar con Spec Kit.
- [Plataforma compartida (spec-009)](specs/009-fundaciones-plataforma/spec.md): punto de partida técnico.
- [Especificaciones funcionales](specs/): cada funcionalidad conserva requisitos, diseño y tareas propios.

`docs/` contiene contexto común. Los archivos que procesa Spec Kit permanecen en
`specs/<identificador>/`, con nombres nativos (`spec.md`, `plan.md`, `tasks.md`, etc.).
Las plantillas de proyecto usan `.specify/templates/overrides/`, mecanismo soportado por
la instalación local. Los scripts y las skills generados siguen siendo infraestructura local.
Los comandos de ejecución de la aplicación se documentarán al implementarla.
