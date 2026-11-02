# Checklist de requisitos: Notificaciones programables y alertas por correo

**Purpose**: Evaluar la completitud, claridad, consistencia y mensurabilidad de los requisitos de programación y recuperación, y de autorización y privacidad de destinatarios.
**Created**: 2026-11-01
**Feature**: [spec.md](../spec.md)
**Focus**: Programación y recuperación; autorización y privacidad de destinatarios, según el foco predeterminado aceptado por la persona solicitante.
**Depth**: Estándar.
**Audience / Timing**: Revisión por pares antes de implementar, según la opción predeterminada aceptada.
**Additional must-haves**: No se solicitaron criterios adicionales.

**Note**: Checklist generado mediante `$speckit-checklist` a partir de la especificación, el plan, los contratos pertinentes y la constitución del proyecto. No existe `tasks.md` en esta fase.
**Review Ownership**: Este checklist pertenece a quien revisa la calidad de los requisitos. Solo esa persona determina cuándo corresponde marcar un criterio como satisfecho.
**Marker Semantics**: `[x]` significa que el criterio de calidad de requisitos fue revisado y satisfecho; no significa que la implementación esté completa. Todos los ítems se generan pendientes de evaluación.

## Completitud de los requisitos

- [ ] CHK001 ¿Están especificados los permisos de cada perfil para consultar información propia o ajena, administrar reglas y autorizar reenvíos, incluidos los accesos directos y las identidades sin autorización funcional? [Completitud, Spec §FR-001, Spec §FR-023]
- [ ] CHK002 ¿Están definidos los campos obligatorios y las combinaciones válidas de programación, condición, contenido y destinatarios para cada modalidad, incluidos los criterios de activación? [Completitud, Spec §FR-002, Spec §FR-004, Spec §FR-005, Spec §FR-006]
- [ ] CHK003 ¿Se especifica qué sucesos y contenidos del catálogo corresponden a cada modalidad y qué permisos requiere cada contenido, especialmente los cambios administrativos? [Completitud, Spec §FR-003, Spec §FR-005, Spec §FR-022]
- [ ] CHK004 ¿Están definidos todos los estados de entrega y la evidencia necesaria para diferenciarlos, separando la aceptación por el servicio de correo de la recepción en bandeja o lectura? [Completitud, Spec §FR-018, Spec §FR-019, Spec §FR-020]
- [ ] CHK005 ¿Están documentados los datos de procedencia, unidad, período, corte y calidad exigidos para sustentar cada alerta o resumen, incluida la base y el alcance de un total calculado? [Completitud, Spec §FR-004, Spec §FR-009, Spec §FR-010, Spec §FR-021]

## Claridad de los requisitos

- [ ] CHK006 ¿Se distinguen sin ambigüedad la hora programada, la detección válida, la recepción de datos, el período medido y el inicio del primer intento para interpretar el plazo de 60 segundos? [Claridad, Spec §FR-008, Spec §FR-009, Spec §FR-013]
- [ ] CHK007 ¿Queda clara la diferencia entre intervalos de tiempo transcurrido y recurrencias de calendario, incluida la zona conservada por regla y la definición de la siguiente ocurrencia admisible? [Claridad, Spec §FR-006, Spec §FR-007, Spec §Assumptions — Tiempo y ventanas, Integraciones §Calendario]
- [ ] CHK008 ¿Se define el inicio de la primera ventana de resumen cuando no existe una ocurrencia anterior admisible y se explicita si su corte permanece fijo durante los reintentos? [Claridad, Spec §FR-009, Integraciones §Calendario]
- [ ] CHK009 ¿Están definidos con criterios objetivos los términos «ventana completa», «cobertura válida» y «ventana más reciente admisible», con referencias a las reglas de calidad de las fuentes? [Claridad, Spec §FR-010, Spec §FR-013, Spec §Assumptions — Reglas de consumo]
- [ ] CHK010 ¿Se precisan el significado de no aceptación confirmada y resultado incierto, el máximo de tres intentos totales y el instante desde el que se cuentan las esperas de uno y cinco minutos? [Claridad, Spec §FR-019, Spec §FR-020, Integraciones §Contrato SMTP]

## Consistencia de los requisitos

- [ ] CHK011 ¿Son consistentes los permisos sobre auditoría administrativa y datos de otros destinatarios entre la especificación, el contenido del correo y las vistas de historial? [Consistencia, Spec §FR-003, Spec §FR-015, Spec §FR-023, Interfaz §Historial y detalle, Interfaz §Correo]
- [ ] CHK012 ¿Es consistente la política de guardar una revisión pausada y exigir activación explícita con los requisitos de versionado y sustitución de reglas, sin dejar implícita la continuidad de una versión activa? [Consistencia, Ambigüedad, Spec §FR-002, Spec §FR-016, Plan §Phase 1: Design & Contracts — Flujo durable, Interfaz §Formulario de regla]
- [ ] CHK013 ¿Se usa el mismo límite conceptual de «intento iniciado» al definir los efectos de una pausa, sustitución o revocación concurrente, diferenciándolo de las entregas todavía pendientes? [Consistencia, Spec §FR-015, Spec §FR-016, Spec §FR-017, Modelo §Concurrencia e índices]
- [ ] CHK014 ¿Son compatibles las identidades de versión, episodio, ocurrencia y destinatario con la supresión de repeticiones, los reintentos y la consolidación de atrasos? [Consistencia, Spec §FR-011, Spec §FR-014, Spec §FR-017]

## Calidad de los criterios de aceptación

- [ ] CHK015 ¿Está delimitado el conjunto de entregas de referencia y las condiciones de elegibilidad, disponibilidad y demanda para medir objetivamente el objetivo de 60 segundos? [Mensurabilidad, Gap, Spec §FR-008, Spec §SC-003, Plan §Technical Context — Performance Goals, Plan §Technical Context — Scale/Scope]
- [ ] CHK016 ¿Quedan definidos el alcance y los resultados esperados de los «100 %» y «todos los casos» de los criterios de éxito, con trazabilidad a permisos, calendario, episodios, estados y contenidos? [Criterios de aceptación, Spec §SC-001, Spec §SC-002, Spec §SC-004, Spec §SC-005, Spec §SC-006]
- [ ] CHK017 ¿Es objetivamente determinable el mínimo de 12 meses calendario para registros, revisiones, intentos y evidencia relacionada, incluidos aniversarios inexistentes o repetidos y dependencias con plazos distintos? [Mensurabilidad, Spec §FR-024, Spec §SC-007, Modelo §Conservación]
- [ ] CHK018 ¿Se definen qué constituye una tarea satisfactoria, qué administradores son representativos y los límites del tiempo medido para el objetivo de nueve de diez tareas en tres minutos? [Criterios de aceptación, Gap, Spec §SC-008]

## Cobertura de escenarios

- [ ] CHK019 ¿Están diferenciados los requisitos de resumen con novedades, sin novedades con cobertura válida y con información insuficiente, sin equiparar ninguno de esos estados a consumo cero? [Cobertura, Spec §FR-009, Spec §FR-010, Spec §FR-021]
- [ ] CHK020 ¿Se documenta el ciclo completo del episodio urgente, desde su primera evidencia válida hasta persistencia, normalización y nueva activación, incluida la continuidad ante información insuficiente? [Cobertura, Spec §FR-010, Spec §FR-011, Spec §User Story 3]
- [ ] CHK021 ¿Son completos los requisitos de excepción para rechazo transitorio confirmado, fallo definitivo, fallo de configuración y aceptación desconocida, incluida la decisión administrativa y su advertencia de posible repetición? [Cobertura, Spec §FR-018, Spec §FR-019, Spec §FR-020, Spec §User Story 4]
- [ ] CHK022 ¿Se especifican los criterios de inclusión y exclusión del resumen de recuperación por regla y destinatario, conservando los períodos y huecos sin incorporar entregas aceptadas, indeterminadas o ya intentadas? [Cobertura, Spec §FR-017, Integraciones §Recuperación e idempotencia]

## Cobertura de casos límite

- [ ] CHK023 ¿Están definidas las políticas para horas inexistentes o repetidas, días mensuales inexistentes y años bisiestos, incluida la conservación de la fecha nominal en las recurrencias siguientes? [Cobertura de límites, Spec §FR-007, Spec §SC-002, Integraciones §Calendario]
- [ ] CHK024 ¿Se especifican los límites de admisibilidad de datos tardíos, lotes históricos, correcciones y sucesos repetidos respecto de la activación y de la última evaluación válida? [Cobertura de límites, Spec §FR-011, Spec §FR-013, Spec §FR-014]
- [ ] CHK025 ¿Se precisan el límite de silencio, su instante inicial y los efectos de duplicados o rechazos para categorías con fuente, sin fuente y con total calculado, sin convertir el mínimo de 15 minutos en una frecuencia obligatoria? [Cobertura de límites, Spec §FR-012, Spec §User Story 3 — Escenarios 5 y 10]
- [ ] CHK026 ¿Se define qué dirección corresponde a una entrega pendiente o a un reintento tras cambiar el correo de la cuenta, manteniendo la identidad del destinatario y la dirección efectiva de cada intento anterior? [Cobertura de límites, Spec §FR-005, Spec §FR-015, Spec §FR-024, Spec §User Story 4 — Escenario 9]

## Requisitos no funcionales

- [ ] CHK027 ¿Están especificados los límites de divulgación entre destinatarios, contenido funcional y observabilidad técnica, incluidos datos sensibles y referencias protegidas a vistas o reportes? [Privacidad, Spec §FR-015, Spec §FR-021, Spec §FR-022, Spec §FR-023]
- [ ] CHK028 ¿Se definen los requisitos de continuidad ante fallos de correo o telemetría, prevención de alertas recursivas y prioridad entre modalidades sin postergar indefinidamente los resúmenes periódicos? [Resiliencia, Spec §FR-008, Spec §FR-025, Plan §Technical Context — Performance Goals, Plan §Phase 1: Design & Contracts — Integración y operación]
- [ ] CHK029 ¿Se especifican criterios observables de accesibilidad y comprensión para formularios, denegaciones y estados del historial, distinguiendo espera, ausencia de notificaciones, información insuficiente y error? [Accesibilidad y claridad, Gap, Constitución §V, Interfaz §Historial y detalle, Interfaz §Validación de uso]
- [ ] CHK030 ¿Quedan definidos la identificación del transporte local y los requisitos comunes de autorización, reintentos y estados entre entornos, sin atribuir entrega externa a una aceptación local? [Consistencia entre entornos, Spec §FR-026, Spec §SC-009, Spec §Assumptions — Entornos y correo de prueba]

## Dependencias y supuestos

- [ ] CHK031 ¿Están documentadas las dependencias de cuentas y permisos vigentes, calidad y cobertura de consumo, resultados funcionales y auditoría, así como los requisitos aplicables cuando no está disponible alguna de esas fuentes? [Dependencias, Assumption, Spec §FR-003, Spec §FR-005, Spec §FR-010, Spec §Assumptions — Dependencias y gobierno, Integraciones §Puertos funcionales]
- [ ] CHK032 ¿Se distingue la configuración pendiente del entorno —zona real del edificio, remitente, servicio de correo y dirección pública— de los valores de desarrollo y de las obligaciones funcionales aprobadas? [Supuestos, Assumption, Spec §FR-026, Plan §Technical Context — Constraints, Plan §Phase 0: Research]
- [ ] CHK033 ¿Se explicitan los límites de responsabilidad del monolito y de sus dependencias externas, junto con las obligaciones de documentación de contratos, reglas temporales y decisiones sobre datos? [Dependencias y gobierno, Spec §FR-025, Spec §Assumptions — Dependencias y gobierno, Constitución §II, Constitución §III, Constitución §IV]

## Ambigüedades y conflictos por resolver en la revisión

- [ ] CHK034 ¿Se aclara el tratamiento de episodios urgentes y sucesos funcionales pendientes tras una interrupción, diferenciándolo de la consolidación reservada a ocurrencias periódicas? [Claridad, Gap, Spec §FR-008, Spec §FR-011, Spec §FR-017]
- [ ] CHK035 ¿Se define el efecto de un cambio de fuente o de base del total calculado durante un episodio, incluida la vigencia de su evidencia, sin atribuir normalización a la pérdida de cobertura? [Claridad, Gap, Spec §FR-004, Spec §FR-010, Spec §FR-011, Spec §FR-012]
- [ ] CHK036 ¿Se distingue la conservación de información histórica del permiso actual para consultarla o reenviarla tras retirar permisos, desactivar una cuenta o cambiar su correo? [Claridad, Ambiguity, Spec §FR-015, Spec §FR-020, Spec §FR-023, Spec §FR-024]

## Notes

- Marcar un ítem `[x]` solo cuando quien revisa determine que el criterio de calidad de requisitos está satisfecho.
- Mantener pendientes los ítems que necesiten aclaración, corrección o evaluación; esta generación no evalúa ni aprueba criterios.
- `$speckit-implement` lee el estado del checklist como condición de avance y no debe modificar sus marcadores.
- `checklists/requirements.md` tiene un ciclo separado, mantenido por `$speckit-specify` y `$speckit-clarify`.
- Añadir observaciones y referencias junto al ítem correspondiente; los identificadores son secuenciales.
- Las referencias `Spec §FR-*` y `Spec §SC-*` pertenecen a [spec.md](../spec.md); los nombres de historias y supuestos identifican sus secciones de texto.
- Fuentes complementarias: [plan](../plan.md), [integraciones](../contracts/integrations.md), [interfaz](../contracts/ui.md), [modelo de datos](../data-model.md) y [constitución](../../../.specify/memory/constitution.md).
- `[Gap]`, `[Ambiguity]` y `[Assumption]` señalan preguntas que requieren revisión; no constituyen por sí mismos hallazgos confirmados ni requisitos nuevos.
