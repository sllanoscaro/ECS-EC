# Feature Specification: Fundaciones compartidas de la plataforma

**Created**: 2026-11-01
**Status**: Draft
**Contexto**: `009-fundaciones-plataforma`; funcionalidad técnica de soporte.
**Input**: Separar la infraestructura común de la spec-008 conservando los requisitos
y decisiones existentes. Referencias: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md).

## User Scenarios & Testing

### User Story 1 - Preparar el monolito local (Priority: P1)

Como responsable de desarrollo, quiero construir y ejecutar el monolito con dependencias
reproducibles y PostgreSQL local antes de incorporar funcionalidades.

**Independent Test**: Instalar desde lockfiles, construir exportación estática e imagen,
aplicar migraciones en base vacía y consultar salud; no requiere SMTP, cuentas ni VPS.

**Acceptance Scenarios**:
1. Con herramientas instaladas y configuración sintética, una construcción produce una
   imagen FastAPI que sirve exportación Next y API sin runtime Node en ejecución.
2. Sin PostgreSQL sano o migraciones aplicadas, no se declara disponibilidad funcional.
3. Reiniciar el contenedor conserva los datos confirmados y cierra recursos ordenadamente.

### User Story 2 - Compartir persistencia y auditoría durable (Priority: P1)

Como módulo del monolito, quiero unidad de trabajo, reloj y eventos funcionales comunes
para confirmar cambios y evidencia sin depender de notificaciones o telemetría.

**Independent Test**: Un productor sintético confirma resultado/evento juntos; rollback
no deja evento, repetir identidad no duplica y faltas de cobertura no se convierten en cero.

**Acceptance Scenarios**:
1. Cambios y eventos usan una transacción PostgreSQL; un rollback revierte ambos.
2. La misma identidad de procedencia no genera otro evento y sus datos son tipados/saneados.
3. Historia incompleta o fuente no consultable informa alcance limitado o desconocido.
4. El aniversario de conservación respeta meses calendario, año bisiesto y horas ambiguas.

### User Story 3 - Operar la base común local/VPS (Priority: P2)

Como responsable de operación, quiero procedimientos de configuración, HTTPS y respaldo
para preparar la VPS y verificar restauración sin incorporar lógica de negocio.

**Independent Test**: Restaurar un respaldo sintético en una base local independiente;
la comprobación pública se realiza cuando exista la VPS y configuración reales.

**Acceptance Scenarios**:
1. El respaldo restaurado conserva filas, restricciones y versión de migración.
2. Secretos y datos personales no se incluyen en imágenes, exportación estática o evidencia.
3. La guía distingue resultados locales de una validación pública aún no realizada.

### Edge Cases

Base inaccesible, migración fallida, cierre durante una transacción, evento repetido,
historia anterior al inicio del registro, aniversario del 29 de febrero y restauración
en destino separado; ninguna prueba debe usar una base de producción.

## Requirements

- **FR-001**: Mantener una unidad monolítica modular y herramientas/manifiestos compartidos.
- **FR-002**: Proveer construcción multietapa, exportación estática y Compose/PostgreSQL local.
- **FR-003**: Proveer configuración validada, reloj inyectable, sesiones DB y unidad de trabajo.
- **FR-004**: Proveer Alembic y composición/ciclo de vida ampliables sin módulos de negocio obligatorios.
- **FR-005**: Proveer auditoría, eventos y cobertura funcional durables e independientes de SMTP/telemetría.
- **FR-006**: Conservar meses calendario, integridad de referencias y ausencia explícita según cada productor.
- **FR-007**: Proveer pruebas y CI reproducibles con PostgreSQL real y entorno de prueba separado.
- **FR-008**: Documentar configuración local/VPS, HTTPS, secretos externos y respaldo/restauración.

### Key Entities

Evento funcional, evidencia de cobertura y entrada de auditoría, descritos en
[data-model.md](data-model.md). Cuentas, mediciones, costos, PDF y entregas pertenecen a sus specs.

## Success Criteria

- **SC-001**: Construcción y arranque local reproducibles con manifiestos bloqueados y base vacía.
- **SC-002**: Pruebas de transacción, deduplicación, cobertura y aniversario producen resultados conocidos.
- **SC-003**: Respaldo sintético restaurado conserva datos y revisión de esquema verificables.
- **SC-004**: Los módulos comunes se importan y prueban sin importar módulos de notificaciones.

## Assumptions

Se trasladan decisiones existentes; no se añade una funcionalidad de negocio ni un servicio
desplegable propio. Identidad es de 006, consumo de 001/002, observabilidad de 007 y SMTP
de 008. Las credenciales, dominio y zona real del edificio se configuran al desplegar.
