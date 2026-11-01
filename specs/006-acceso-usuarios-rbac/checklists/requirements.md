# Specification Quality Checklist: Autenticación y permisos por perfil

**Purpose**: Validar la calidad y completitud de la especificación antes de planificar.
**Created**: 2026-11-01
**Feature**: [spec.md](../spec.md)

**Marker Semantics**: Una marca `[x]` confirma calidad de los requisitos revisados;
no indica implementación terminada ni controles de acceso ejecutados.

## Content Quality

- [x] No contiene detalles de implementación elegidos, lenguajes ni frameworks.
- [x] Se centra en el valor para las personas usuarias y las necesidades del edificio.
- [x] Está escrita para personas interesadas sin conocimientos técnicos.
- [x] Todas las secciones obligatorias están completas.

## Requirement Completeness

- [x] No quedan marcadores de aclaración pendientes.
- [x] Los requisitos son verificables y no ambiguos.
- [x] Los criterios de éxito son medibles.
- [x] Los criterios de éxito son independientes de la tecnología de implementación.
- [x] Están definidos los escenarios de aceptación.
- [x] Se identifican los casos límite.
- [x] El alcance está claramente delimitado.
- [x] Se identifican dependencias y supuestos.

## Feature Readiness

- [x] Todos los requisitos funcionales tienen criterios de aceptación claros.
- [x] Las historias cubren los flujos principales.
- [x] Los resultados medibles cubren el comportamiento especificado.
- [x] La especificación no prescribe decisiones de implementación.

## Notes

- Revisión completada el 2026-11-01: 16 de 16 criterios satisfechos; sin aclaraciones pendientes.
- Se revisaron cuatro historias, 29 escenarios, 23 requisitos y siete criterios de éxito.
  La revisión valida la especificación; no ejecuta autenticación ni pruebas de autorización.
- La persona solicitante confirmó que el Operador puede generar y descargar PDF como lectura.
  El Administrador técnico hereda esas operaciones y las demás consultas.
- Se distinguen referencias de negocio visibles en costos de la configuración administrativa;
  registrar boletas, guardar tarifas y crear revisiones queda reservado al Administrador técnico.
- Se exige comprobar permisos en cada solicitud protegida y denegar acciones no autorizadas
  por la matriz; no se confía en un perfil declarado por la persona solicitante.
- Se precisó el historial para solicitudes sin sesión: "condición no autenticada sin confiar
  en una identidad declarada", sin inventar un actor identificado.
- La matriz describe acceso normal; la renovación de contraseña inicial mantiene una sesión
  restringida y no permite usar anticipadamente los permisos del perfil.
- Se verificaron invalidación de sesiones, unicidad de correo y protección del último
  administrador activo ante cambios concurrentes.
- Se documentaron como valores iniciales de producto la longitud de contraseña, expiración
  de sesión y espera tras intentos fallidos; no se prescriben algoritmos, bibliotecas o frameworks.
- Las cuentas humanas no sustituyen las identidades SFTP. El escenario 4.7 evita exigir una
  sesión web para envíos técnicos ya autorizados por la spec-003.
- Dependencias para planificación: aplicar la matriz a las funciones de las specs-001 a 005,
  documentar preparación y recuperación inicial, sesiones y trazabilidad administrativa.
- Lista para `$speckit-plan`; la constitución y las specs-001 a 005 no se modificaron.

Cobertura revisada de requisitos mediante escenarios (historia.escenario):

| Requisito | Escenarios de aceptación y evidencia |
| --- | --- |
| FR-001 | 3.1 y caso límite de perfil vacío o desconocido. |
| FR-002 | 1.1, 1.2 y 1.7. |
| FR-003 | 3.2 y reglas explícitas de identidad y conservación de caracteres. |
| FR-004 | 1.2 y 1.6. |
| FR-005 | 2.4 y 2.6. |
| FR-006 | 1.3 y 2.7. |
| FR-007 | 2.1 y 2.2. |
| FR-008 | 2.4 y 2.5. |
| FR-009 | 4.1, 4.2 y 4.3. |
| FR-010 | 2.3 y 2.4. |
| FR-011 | 3.1, 3.2 y 3.3. |
| FR-012 | 3.4 y preservación de identidad de cuentas desactivadas. |
| FR-013 | 3.6, 3.7 y preparación inicial definida. |
| FR-014 | 3.5 y 3.8. |
| FR-015 | 1.7, 3.1 y 3.5. |
| FR-016 | 1.4 y 1.5. |
| FR-017 | 3.3, 3.4, 3.8 y 4.6. |
| FR-018 | 3.5, 4.5 y restricciones explícitas de exposición. |
| FR-019 | 4.2 y 4.4. |
| FR-020 | 2.5 y 4.3. |
| FR-021 | 4.5. |
| FR-022 | 2.4, 2.5 y 4.4. |
| FR-023 | 4.7. |
