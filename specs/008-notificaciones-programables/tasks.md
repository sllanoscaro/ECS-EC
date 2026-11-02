---
description: "Tareas propias de notificaciones y su integración con capacidades compartidas"
---

# Tasks: Notificaciones programables y alertas por correo

**Input**: [plan](plan.md), [spec](spec.md), [research](research.md), [modelo](data-model.md),
[contratos](contracts/), [quickstart](quickstart.md), [arquitectura](../../docs/architecture.md)
y [hoja de ruta](../../docs/implementation-roadmap.md).
**Prerequisites**: Plataforma009, identidad006 y consumo001/002 reales; emisores de 007
para instrumentación. Sus diseños/implementaciones se resuelven en sus propias specs.
El puente de fallos espera productores004/005; los visores007 no bloquean negocio.
**Tests**: Pruebas primero para comportamiento nuevo; proveedores reales para integración final.
**Organization**: US1 configuración P1, US2 periódicos P1, US3 urgencias P1, US4 historial P2.
**Rutas**: Relativas a la raíz del repositorio, no al directorio de esta spec.
**Estado**: Todas pendientes. Documentar cada archivo/elemento propio; conservar checklists de revisión.
**Propiedad**: Esta lista no implementa core, cuentas, recepción/agregados o visores comunes.
Los IDs son locales a este archivo y se renumeraron al trasladar responsabilidades.

## Phase 1: Setup — integración del módulo

- [ ] T001 Crear `backend/src/ecs_ec/notifications/__init__.py` y configuración/fixtures de correo en `backend/tests/notifications_fixtures.py`; verificar capacidades externas contra `contracts/integrations.md` y registrar faltantes en `specs/008-notificaciones-programables/validation/prerequisites.md`. Agregar Mailpit al perfil local de `compose.yaml` y variables MAIL/SMTP/NOTIFICATION a `.env.example` existentes de plataforma009; conservar versiones/digests fijados, loopback local y correo fuera de readiness. Si falta una base ajena, resolverla en su spec antes de continuar.

## Phase 2: Foundational — modelos y adaptadores propios

- [ ] T002 [P] Escribir `backend/tests/integration/notifications/test_identity_integration.py` con identidad006 real y participante de notificaciones: permisos actuales, cambios concurrentes de correo/estado/perfil con varias reglas, pausa y límite durable del intento. El registro neutral ya debe existir; no implementar sesiones o administración aquí.
- [ ] T003 [P] Escribir `backend/tests/integration/notifications/test_consumption_adapters.py` con módulos001/002 reales: ventanas/cobertura, fuentes ausentes, CAT-01 medida/calculada, duplicados y datos nuevos para silencio; comparar con sus contratos, sin implementar recepción, validaciones o agregados en esta spec.
- [ ] T004 [P] Escribir `backend/tests/integration/notifications/test_constraints.py` para rechazos de restricciones y conservación de evidencia bajo concurrencia real: unicidad de versión, activación, episodio, ocurrencia, entrega, intento y miembro de recuperación. Prerrequisitos: fase 1.
- [ ] T005 Definir regla, versión y destinatarios en `backend/src/ecs_ec/notifications/models.py`: `id`/`building_id` «UUID, edificio único del alcance»; `name` «Texto recortado, 1..120 caracteres»; `status` «`desactivada`, `activa`, `pausada`»; `revision` «Entero para control optimista (`If-Match`)»; versión «UUID/FK; UNIQUE `(rule_id, version_number)`», `mode` «`periodica` o `urgente`», `content_types` «Conjunto no vacío del catálogo permitido», `schedule_id`/`condition_id` «Exactamente uno según modalidad», `timezone` «Zona IANA válida, copiada del edificio o explícita» y destinatario «FK `(version_id, account_id)` única»; incluir procedencia, plantilla y conservación de las tablas del modelo.
- [ ] T006 Añadir programación y activación a `backend/src/ecs_ec/notifications/models.py`: «Una programación por versión periódica»; `kind` «`intervalo`, `diaria`, `semanal`, `mensual`, `anual`»; `starts_at` «Instante RFC3339; límite inferior y ancla para intervalos»; intervalo «Entero >0 y `minutos`/`horas`, solo intervalo»; hora «HH:MM, solo calendario»; día semanal «ISO 1..7, solo semanal»; día mensual «1..31, mensual/anual; conservar el valor nominal»; mes «1..12, solo anual»; zona «Zona IANA; nunca offset fijo en sustitución»; rechazar combinaciones no aplicables y limitar a una activación vigente por regla.
- [ ] T007 Añadir condiciones, evaluación, evidencia y episodios a `backend/src/ecs_ec/notifications/models.py`: consumo «`category_id` CAT-01..07, `unit=kWh`, `window_kind` intervalo/hora/dia/mes/anio, `comparison` gt/gte/lt/lte, `threshold_kwh` Decimal» y resolución «`measurement_interval_seconds` >0»; ausencia «`silence_minutes` entero >=15»; evento «`recepcion_rechazada`, `calculo_fallido` o `pdf_fallido`»; estado «UNIQUE `(activation_id, scope_key)`» y «`scope_key` es la categoría conocida o tipo de evento, nunca un correo»; evaluación «`cumple`, `no_cumple`, `no_evaluable`, `omitida_historica`», «`source_event_id` opcional» y «`episode_id` opcional»; evidencia «`value_kwh` nullable», «Valor ausente es NULL con razón explícita» y `origin` «`medido`, `calculado`, `sin_fuente`»; episodio «`abierto`, `cerrado`, `finalizado_por_regla`», «`source_event_id` opcional», único abierto por activación/alcance y único por activación/evento puntual; conservar todos los campos y referencias del modelo. Referenciar FunctionalEvent de audit/models.py sin duplicar su tabla en notificaciones.
- [ ] T008 Añadir ocurrencia, mensaje, entrega e intento a `backend/src/ecs_ec/notifications/models.py`: ocurrencia «`periodica`, `urgente`, `recuperacion`», `episode_id` opcional y «UNIQUE `(version_id, logical_key)`»; mensaje «`functional_content` tipado e inmutable» y «UNIQUE ocurrencia»; `generation` «0 original; >0 reenvío manual»; entrega «`pendiente`, `en_intento`, `aceptada`, `fallida`, `cancelada`, `indeterminada`», contador «Fecha de elegibilidad y 0..3 para esta entrega», transporte «`local_prueba` o `smtp_produccion`» y «UNIQUE `(message_id, account_id, generation)`»; intento «`aceptada`, `no_aceptada_transitoria`, `no_aceptada_definitiva`, `indeterminada`», «UNIQUE `(delivery_id, attempt_number)`, número 1..3, un intento abierto máximo por entrega»; incluir correo efectivo protegido, tiempos y referencias, sin fijar correo en una entrega pendiente.
- [ ] T009 Añadir recuperación, decisión de reenvío e idempotencia en `backend/src/ecs_ec/notifications/models.py`: «`original_delivery_id` UNIQUE», miembros con «`attempt_count=0`», razón «`consolidada_en_recuperacion`», decisión con «Clave única por administrador/operación y clave idempotente» y registro HTTP «UNIQUE `(actor_id, operation, idempotency_key)`»; persistir campos de actor, operación, hash, recurso, estado HTTP, fechas y conservación del modelo, sin copias de secretos o respuestas indiscriminadas.
- [ ] T010 Crear `backend/migrations/versions/notifications_008_initial.py` únicamente con tablas de T005–T009, FKs a identidad/auditoría existentes y restricciones de `data-model.md`; índices de cola «`(next_attempt_at, id) WHERE state='pendiente'`», programación «`(next_due_at) WHERE ended_at IS NULL`» e historial «`(account_id, created_at, id)`». Enlazar al head real, verificar instalación y rollback sin destruir evidencia; no recrear tablas de otras specs.
- [ ] T011 Concretar los puertos de identidad, ventanas, fuentes, resumen por contenido y auditoría en `backend/src/ecs_ec/notifications/ports.py` y `backend/src/ecs_ec/notifications/adapters.py`; conectar identidad006, series001/002 y auditoría009 reales ya implementadas en sus specs. El puente de costos/PDF se añade en T061 cuando sus entregables están listos, sin productores ficticios ni dependencia inversa. Conservar «Energía y umbrales `NUMERIC`/Decimal finitos no negativos, transmitidos como cadenas decimales sin redondeo implícito», rechazando NaN, infinito y comparaciones con float binario.
- [ ] T012 Crear repositorio transaccional e idempotencia en `backend/src/ecs_ec/notifications/repository.py` y `backend/src/ecs_ec/notifications/idempotency.py`; autenticar/autorizar antes de recuperar una clave confirmada y resolverla antes de `If-Match`, devolver 409 para misma clave con cuerpo distinto y guardar clave/cambio juntos al menos 12 meses.
- [ ] T013 Conectar dependencias de sesión, origen/CSRF y traducción de errores existentes a `backend/src/ecs_ec/notifications/api.py`; usar `core/security.py` de spec-006 y errores comunes de plataforma009, respetando `ecs_ec_session`, `X-CSRF-Token` y `Problem` del contrato sin implementar autenticación en notificaciones.
- [ ] T014 Implementar el participante de notificaciones en `backend/src/ecs_ec/notifications/identity_coordination.py` y `backend/src/ecs_ec/notifications/repository.py`, usando el registro neutral ya entregado por spec-006 en [su contrato de coordinación](../006-acceso-usuarios-rbac/contracts/coordination.md); bloquear reglas por UUID ordenado → cuenta → entrega, revalidar conjunto y reintentar si cambió. Mutación previa al inicio durable impide intento inelegible; intento iniciado conserva historia/correo efectivo. Validar concurrencia mediante T002 antes de T045; identity no importa notifications.
- [ ] T015 Registrar rutas, participante de identidad y servicios internos del módulo desde `backend/src/ecs_ec/notifications/lifecycle.py` en `backend/src/ecs_ec/main.py` y `backend/src/ecs_ec/core/lifecycle.py` existentes de plataforma009. Ejecutar T002–T004 con proveedores reales; los bucles se habilitan en US2/US3 después de sus prerrequisitos. No construir aquí el ciclo de vida ni la aplicación base.

**Checkpoint**: Restricciones, adaptadores y coordinación de notificaciones verificados
con plataforma/identidad/series reales. Ningún módulo ajeno se implementa para saltar un bloqueo.

## Phase 3: User Story 1 — configurar como Administrador técnico (P1) — MVP de configuración

**Goal**: Crear, revisar, previsualizar, activar y pausar reglas versionadas con contenido y destinatarios autorizados.
**Independent Test**: Con Administrador, Operador, Programador y sesión ausente, cubrir los siete escenarios de US1: validaciones, auditoría restringida, próximas fechas, sustitución/pausa y cancelación de pendientes preparados como fixtures; ningún envío real es necesario para aceptar este incremento de configuración.

### Pruebas de US1

- [ ] T016 [P] [US1] Escribir `backend/tests/contract/notifications/test_rules_api.py` para las diez operaciones de catálogo/destinatarios/reglas, incluida previsualización, versiones, activación y pausa; comparar con `contracts/openapi.json` y cubrir 401/403/404, 409, 412/428 y 422, origen/CSRF, ETag e idempotencia. Prerrequisito: fase 2.
- [ ] T017 [P] [US1] Escribir `backend/tests/integration/notifications/test_rule_concurrency.py` para revisiones simultáneas, reintento de la misma clave antes de precondiciones, pérdida de permisos, cancelación de pendientes y conservación de intentos iniciados; usar PostgreSQL y cuentas reales. Prerrequisito: fase 2.
- [ ] T018 [P] [US1] Escribir `backend/tests/unit/notifications/test_calendar.py` con intervalos y las cuatro recurrencias calendario, DST real del tzdata fijado, hueco al primer instante válido, primera hora repetida, enero 31/febrero/marzo y 29 de febrero anual; usar expectativas explícitas y distinguir calendario de retención. Prerrequisito: fase 2.
- [ ] T019 [P] [US1] Escribir `frontend/tests/unit/notification-rule-editor.test.tsx` y `frontend/tests/e2e/notification-rules.spec.ts` para permisos, destinatarios registrados, auditoría exclusiva, validaciones, vista previa vigente, conflictos y pausa, incluyendo teclado y etiquetas. Prerrequisito: fase 2.

### Implementación de US1

- [ ] T020 [US1] Implementar uniones y validadores de entrada/salida en `backend/src/ecs_ec/notifications/schemas.py` según los 38 esquemas del contrato: rechazar campos ajenos, nombre 1..120, zona IANA de longitud 1..100, destinatarios únicos no vacíos, contenido permitido por modalidad, calendario aplicable, umbral decimal como cadena y condiciones con sus límites de T005–T007. Incluir SummaryItem.count entero >=0 o NULL, cobertura por contenido, períodos/huecos/motivo y reglas de estado global del resumen; completa exige conteo conocido.
- [ ] T021 [US1] Implementar catálogo y resolución de destinatarios en `backend/src/ecs_ec/notifications/catalog.py` y `backend/src/ecs_ec/notifications/recipients.py`; limitar a cuentas funcionales activas, comprobar permisos sobre todo el contenido y reservar cambios administrativos a administradores, sin admitir correo libre ni credenciales técnicas.
- [ ] T022 [US1] Implementar cálculo puro de calendario en `backend/src/ecs_ec/notifications/calendar.py`: intervalos UTC, ancla nominal y zona IANA para recurrencias, políticas FR-007, siguiente fecha estrictamente posterior a activación y ventana inicial acotada por `starts_at`; preservar versión tzdata y no generar atrasos previos a activación.
- [ ] T023 [US1] Implementar vista previa sin efectos de envío en `backend/src/ecs_ec/notifications/preview.py`; devolver hasta tres ocurrencias para periódicas y ninguna predicción para urgentes, token opaco ligado a configuración/permisos y vencimiento al menor de cinco minutos o primera ocurrencia; revalidar si cambia tzdata o la elegibilidad.
- [ ] T024 [US1] Implementar creación y revisión inmutable en `backend/src/ecs_ec/notifications/services.py`; nuevas reglas desactivadas, revisión pausada con incremento de número/revisión, auditoría y cancelación de pendientes anteriores en una transacción, sin eliminar versiones ni admitir borrado por API.
- [ ] T025 [US1] Implementar activación/pausa en `backend/src/ecs_ec/notifications/services.py` y `backend/src/ecs_ec/notifications/repository.py`; exigir preview vigente, cuenta/contenido/programación válidos, una activación vigente, siguiente fecha admisible y orden de bloqueo regla → cuenta → entrega, sin alterar intentos iniciados.
- [ ] T026 [US1] Implementar en `backend/src/ecs_ec/notifications/api.py` las diez operaciones bajo `/api/v1/notifications`: catálogo, destinatarios, preview, listado/creación de reglas, detalle/revisión, versiones, activación y pausa; aplicar límites de página 1..100 con 25 predeterminado, filtros, ETag, clave idempotente 1..100 y permisos/errores del contrato.
- [ ] T027 [US1] Crear tipos y cliente en `frontend/src/lib/api/notifications.ts`, sincronizados con el contrato y reutilizando `frontend/src/lib/api/session.ts` de spec-006; conservar decimales como texto, enviar sesión/CSRF, reutilizar claves por acción y manejar 409/412/428 sin repetir mutaciones ni conservar permisos vencidos.
- [ ] T028 [US1] Crear listado y selección de reglas en `frontend/src/app/notificaciones/reglas/page.tsx` y `frontend/src/components/notifications/RuleList.tsx`; usar consulta `?regla=<uuid>`, exportación estática, catálogo y destinatarios del servidor, con administración visible solo para el perfil autorizado.
- [ ] T029 [US1] Implementar formulario en `frontend/src/components/notifications/RuleEditor.tsx`, `frontend/src/components/notifications/ScheduleFields.tsx` y `frontend/src/components/notifications/ConditionFields.tsx`, con todos los campos aplicables, origen/base de CAT-01, restricciones del contrato, mensajes por campo y conservación de entradas ante validaciones.
- [ ] T030 [US1] Implementar preview, activación, pausa e historial de versiones en `frontend/src/components/notifications/RulePreview.tsx` y `frontend/src/components/notifications/RuleActions.tsx`; mostrar zona/ventanas, descartar preview vencido y exigir nueva configuración vigente tras conflictos.
- [ ] T031 [US1] Integrar estados accesibles de espera, error, sesión caducada y autorización revocada en `frontend/src/components/notifications/FormStatus.tsx` y las páginas de T028–T030; diferenciar errores de listas vacías y conservar el retorno seguro a ingreso.
- [ ] T032 [US1] Ejecutar T016–T019 y los siete escenarios US1 con API y UI reales; guardar comandos, versiones y resultados saneados en `specs/008-notificaciones-programables/validation/us1.md`, corrigiendo fallos antes del checkpoint.
- [ ] T033 [US1] Preparar el protocolo de las diez tareas SC-008 en `specs/008-notificaciones-programables/validation/usability.md`, con inicio/fin de medición, cuenta elegible, resumen diario 06:00, identificación de siguiente fecha y registro de ayuda/obstáculos; reservar los resultados reales para T090.

**Checkpoint**: US1 es demostrable con configuración y permisos reales. El MVP de configuración no acredita todavía correo periódico ni urgencias.

## Phase 4: User Story 2 — recibir correo periódico (P1)

**Goal**: Producir ocurrencias y resúmenes periódicos durables, con entregas individuales y aceptación local observable sin sesión humana.
**Independent Test**: Activar el resumen diario 06:00 mediante US1 y cubrir los ocho escenarios de US2: ventana y corte correctos, sin novedades, calendarios excepcionales, destinatarios separados, activación sin atrasos, correo local y referencias configurables protegidas; la validación externa en VPS se completa en T091.
**Dependencia**: US1. La seguridad del despacho, reintentos y reconciliación se implementa aquí porque también la necesita US3; US4 amplía consulta y decisiones administrativas.

### Pruebas de US2

- [ ] T034 [P] [US2] Escribir `backend/tests/contract/notifications/test_periodic_deliveries_api.py` para listado y detalle de entregas, esquemas de contenido/intento, estados, transporte local y ámbito por cuenta; rechazar objeto ajeno sin metadatos y permisos retirados aunque exista historial. Prerrequisito: US1.
- [ ] T035 [P] [US2] Escribir `backend/tests/integration/notifications/test_scheduler.py` para slots únicos, ventanas/cortes inmutables, primera activación, reinicios, consolidación de nunca intentados y pérdida de liderazgo; dos consumidores deben respetar claves y exclusión real PostgreSQL. Prerrequisito: US1.
- [ ] T036 [P] [US2] Escribir `backend/tests/integration/notifications/test_smtp_dispatch.py` para aceptación, transitorio confirmado, tres intentos con esperas, rechazo definitivo, pérdida de confirmación tras DATA, fallo QUIT posterior a aceptación, reinicio antes de registrar resultado y correo/permisos vigentes. Prerrequisito: US1. Ejecutar también cambios de cuenta/regla simultáneos al claim con el protocolo fundacional T014, antes del checkpoint US2.
- [ ] T037 [P] [US2] Escribir `frontend/tests/e2e/notification-periodic.spec.ts` para configurar 06:00, observar entrega propia, distinguir «Sin novedades» de información insuficiente y comprobar etiqueta de transporte local y enlaces autenticados. Prerrequisito: US1.

- [ ] T038 [P] [US2] Escribir `backend/tests/integration/notifications/test_timezone_upgrade.py` con dos versiones controladas de reglas horarias: nuevo inicio cambia solo futuros no materializados, preserva slots/cortes/evidencia existentes e invalida previews afectados. Interrumpir reconciliación y comprobar reanudación idempotente, exclusión de otro líder y ninguna planificación antes de terminar. Prerrequisito: US1.
- [ ] T039 [P] [US2] Escribir `backend/tests/integration/notifications/test_summary_coverage.py` y `frontend/tests/unit/notification-summary-coverage.test.tsx` para historia íntegra en cero, íntegra positiva, primera ventana anterior al registro, conservación vencida, fuente no consultable y mezcla de contenidos. Exigir estado global preciso, un ítem por contenido, NULL desconocido y conteos observados con períodos/huecos, sin usar logs técnicos como cobertura. Prerrequisito: US1.

### Implementación de US2

- [ ] T040 [US2] Implementar planificador durable en `backend/src/ecs_ec/notifications/scheduler.py` y consultas de slots en `backend/src/ecs_ec/notifications/repository.py`; liderazgo con advisory lock de sesión, abandono al perder conexión, materialización acotada por clave estable y avance atómico del cursor sin repetir fechas previas a activación.
- [ ] T041 [US2] Implementar reconciliación automática de tzdata en `backend/src/ecs_ec/notifications/calendar_reconciliation.py`: bajo liderazgo comparar versión instalada/registrada antes de habilitar planificador, recalcular únicamente futuros no materializados preservando ancla nominal e historial y registrar nueva versión/next_due_at por regla transaccionalmente; invalidar previews afectados. Reanudar tras reinicio sin duplicados; conservar vencidos para recuperación y detenerse al perder liderazgo. Integrar al inicio de T050 y satisfacer T038.
- [ ] T042 [US2] Implementar lector de resúmenes en `backend/src/ecs_ec/notifications/summaries.py` con recepción/calidad/cambios por fechas funcionales dentro de `[inicio,fin)`, corte fijo y un ítem por contenido seleccionado. Aplicar «`count` entero no negativo o NULL» y «`coverage` (`completa`, `incompleta`, `desconocida`)», períodos cubiertos/huecos/motivo, usando la evidencia funcional de auditoría. Todos completos en cero permiten sin_novedades; todos completos con algún suceso, disponible; cualquier limitado produce informacion_insuficiente conservando conteos observados; fuente fallida no crea cero ni desaparece del resumen.
- [ ] T043 [US2] Crear contenido funcional tipado, hash/plantilla inmutables y cuerpos texto/HTML escapados en `backend/src/ecs_ec/notifications/content.py` y `backend/src/ecs_ec/notifications/templates.py`; incluir edificio, modalidad/prioridad, regla/versión, ventana/corte, unidades/calidad, recuperación y rutas protegidas, sin adjuntar PDF ni secretos ni otros destinatarios. Conservar cobertura, conteos NULL/observados, períodos y huecos por contenido en el correo y captura; aplicar las tres reglas de estado global del contrato.
- [ ] T044 [US2] Implementar adaptadores de correo en `backend/src/ecs_ec/notifications/transports.py` y transporte determinista interno en `backend/tests/support/mail_transport.py`: un To/envelope por entrega sin CC/BCC ajenos, Message-ID estable con dominio del remitente autorizado, cuatro resultados de aceptación según evidencia DATA/QUIT, Mailpit identificado y producción con STARTTLS obligatorio, certificado/hostname verificados y credenciales externas.
- [ ] T045 [US2] Implementar reserva de capacidad y claim en `backend/src/ecs_ec/notifications/dispatcher.py` y `backend/src/ecs_ec/notifications/repository.py`: reservar antes de reclamar, `FOR UPDATE SKIP LOCKED`, revalidar regla/activación, cuenta, correo actual y permisos en orden regla → cuenta → entrega; registrar intento/incremento atómicamente y confirmar antes del correo fuera de la transacción. Prerrequisito obligatorio: coordinación compartida T014 ya completada y verificada en fundaciones.
- [ ] T046 [US2] Completar resultados y reintentos en `backend/src/ecs_ec/notifications/dispatcher.py`: cuatro plazas iniciales, SMTP en executor dedicado, socket de 10 s con presupuesto total de 30 s y timeout ajustado al presupuesto restante en cada etapa, no liberar plaza mientras su llamada siga activa, máximo tres intentos y esperas de 1/5 minutos desde el fin del anterior; priorizar urgentes con cuota 3:1 cuando ambas colas tengan trabajo y detener automáticos ante definitivo o indeterminado.
- [ ] T047 [US2] Implementar reconciliación de arranque y consolidación periódica en `backend/src/ecs_ec/notifications/recovery.py`: intentos abiertos sin evidencia inequívoca quedan indeterminados; agrupar solo vencidos autorizados nunca intentados por versión/cuenta, conservar miembros/períodos/huecos y cancelar originales atómicamente; no regenerar aceptados, indeterminados ni reintentos ya iniciados.
- [ ] T048 [US2] Implementar consulta básica de entregas y contenido en `backend/src/ecs_ec/notifications/queries.py` y las dos operaciones GET de entregas en `backend/src/ecs_ec/notifications/api.py`; paginar estable, resolver permisos actuales sobre todo el contenido y ocultar datos ajenos, sin presentar aceptación como lectura o recepción externa.
- [ ] T049 [US2] Crear historial básico y detalle en `frontend/src/app/notificaciones/page.tsx`, `frontend/src/components/notifications/DeliveryList.tsx` y `frontend/src/components/notifications/DeliveryDetail.tsx`, usando `?entrega=<uuid>`; distinguir espera, vacío, fallo de consulta, calidad y todos los estados de entrega con correo local identificado. Mostrar por contenido cobertura completa/incompleta/desconocida y alcance; NULL es «No disponible» y un conteo con cobertura limitada es «Eventos observados».
- [ ] T050 [US2] Registrar planificador, despachador y reconciliación en `backend/src/ecs_ec/core/lifecycle.py`, con ciclos iniciales de 5 s, avisos tras cambios confirmados, supervisión, cierre ordenado y liberación segura del liderazgo; funcionar sin sesión humana y sin bloquear consultas con SMTP. Antes de habilitar planificación ejecutar T041; no programar mientras quede una regla sin reconciliar ni después de perder liderazgo.
- [ ] T051 [US2] Añadir y ejecutar integración real con Mailpit en `backend/tests/integration/notifications/test_mailpit_periodic.py`, comprobando destinatarios independientes, correo vigente, contenido autorizado, ventana/corte, URL del entorno y aceptación local; impedir que el resultado afirme entrega a buzón externo.
- [ ] T052 [US2] Añadir comprobación periódica parcial con reloj real en `backend/tests/integration/notifications/test_periodic_latency.py`: dos reglas periódicas para diez destinatarios, 20 entregas, cola vacía, cuatro plazas y aceptación local <=1 s; medir `attempt.started_at - scheduled_at <=60 s`. Registrar recursos/versiones/resultados; el cumplimiento íntegro SC-003 requiere además el perfil mixto de 40 entregas de T070, no se acredita con este caso aislado.
- [ ] T053 [US2] Ejecutar T034–T037, T038, T039, T051–T052 y los escenarios de calendario/correo/reinicio del quickstart; corregir fallos y registrar evidencia saneada en `specs/008-notificaciones-programables/validation/us2.md`, identificando la comprobación externa pendiente de T091.
- [ ] T054 [US2] Actualizar el procedimiento local y límites de aceptación en `specs/008-notificaciones-programables/quickstart.md` y la arquitectura de ejecución en `deploy/README.md`, incluyendo Mailpit, primeros intentos, recuperación, confirmación incierta y ausencia de garantía de bandeja/lectura.

**Checkpoint**: US2 entrega correo periódico local con el núcleo seguro de despacho y recuperación operativo. Sus comprobaciones no dependen del evaluador urgente de US3 ni del reenvío manual de US4.

## Phase 5: User Story 3 — recibir alertas urgentes (P1)

**Goal**: Detectar condiciones válidas de consumo, ausencia y sucesos funcionales, abrir episodios sin duplicación y producir urgencias con evidencia trazable.
**Independent Test**: Con reglas creadas por US1 y núcleo de correo de US2, cubrir los diez escenarios de US3 usando valores conocidos, datos incompletos, CAT-01 calculada, fuentes ausentes, silencio y lotes históricos; la detección urgente no espera un resumen periódico ni otra medición.
**Dependencia**: US1 y núcleo compartido T040–T047/T050. El puente T061, el consumidor de eventos de costos/PDF y su validación real esperan los entregables 004/005; las urgencias de consumo/ausencia pueden avanzar con sus propias dependencias listas. La construcción de US3 puede coincidir con el cierre de validación de US2 cuando no haya archivos compartidos pendientes.

### Pruebas de US3

- [ ] T055 [P] [US3] Escribir `backend/tests/unit/notifications/test_consumption_conditions.py` con las cuatro comparaciones, 100/101/99 kWh, umbral cero, ventanas intervalo/hora/día/mes/año, cobertura incompleta, CAT-01 calculada 20 con base CAT-03/CAT-05 y falta de una contribución; exigir resultados conocidos sin estimaciones. Prerrequisito: núcleo compartido US2.
- [ ] T056 [P] [US3] Escribir `backend/tests/integration/notifications/test_urgent_events.py` para episodios persistentes/normalizados, no evaluable, ausencias por reloj, duplicados/rechazos, recepción histórica, sucesos puntuales repetidos y fuentes calculadas/sin medidor. Prerrequisito: núcleo compartido US2.
- [ ] T057 [P] [US3] Escribir `frontend/tests/e2e/notification-urgent.spec.ts` para reglas de consumo/silencio/evento, unidades, período real/retraso, evidencia de total calculado y restricciones de destinatario/contenido. Prerrequisito: núcleo compartido US2.

### Implementación de US3

- [ ] T058 [US3] Implementar condiciones y selección de evidencia en `backend/src/ecs_ec/notifications/evaluator.py` mediante los puertos reales: únicamente ventanas completas válidas y unidades kWh, comparaciones Decimal, categorías conocidas y total CAT-01 existente con base/alcance; registrar NULL con motivo explícito para un valor ausente.
- [ ] T059 [US3] Implementar transacción de evaluación, cursor y episodio en `backend/src/ecs_ec/notifications/episodes.py` y `backend/src/ecs_ec/notifications/repository.py`; cumplir «Solo una evaluación válida hace avanzar `last_valid_window_end`», no cerrar ante no evaluable, una urgencia por episodio y normalidad válida para rearme; pausa finaliza por regla sin afirmar normalización.
- [ ] T060 [US3] Implementar ausencia de datos en `backend/src/ecs_ec/notifications/absence.py` desde última aceptación de novedades o activación, plazo entero >=15 minutos y evaluación por reloj; duplicados/rechazos no reinician, categorías sin fuente no abren episodio y CAT-01 calculada usa disponibilidad de totales válidos.
- [ ] T061 [US3] Conectar exclusivamente los productores reales ya entregados por `specs/004-costos-tarifa-bt43/tasks.md` y `specs/005-generar-reportes-pdf/tasks.md` con notificaciones mediante `backend/src/ecs_ec/notifications/adapters.py` y `backend/src/ecs_ec/notifications/event_consumer.py`; consumir `cost.failed`/`pdf.failed` de `audit/events.py` con identidad/revisión persistidas y carga saneada, sin implementar cálculos ni generación PDF en 008. Prerrequisito de estas alertas de sistema y su aceptación integral; no bloquea US1/US2 ni las urgencias de consumo con dependencias reales listas.
- [ ] T062 [US3] Implementar consumo de sucesos funcionales en `backend/src/ecs_ec/notifications/event_consumer.py` para rechazo de recepción, fallo de cálculo y fallo PDF; deduplicar identidad/revisión del productor, preservar procedencia/fecha y excluir logs, trazas y fallos de correo como productores recursivos.
- [ ] T063 [US3] Implementar selección de lotes tardíos y correcciones en `backend/src/ecs_ec/notifications/evaluator.py`: solo última ventana admisible, excluir cierres anteriores a activación o superados por cursor válido, registrar omisiones y conservar correcciones en historial/resumen con período real y retraso.
- [ ] T064 [US3] Incorporar cambios de fuente e identidad en `backend/src/ecs_ec/notifications/event_consumer.py` y `backend/src/ecs_ec/notifications/absence.py`; consultar estado vigente/base calculada y preservar episodios cuando se pierde cobertura, sin inventar una medición cero ni conceder permisos por identidad técnica.
- [ ] T065 [US3] Incorporar evaluador y temporizador de ausencias al supervisor de `backend/src/ecs_ec/core/lifecycle.py`; despertar tras eventos confirmados y también por reloj, conservar cursores durables y funcionar sin sesión ni nueva recepción.
- [ ] T066 [US3] Añadir contenido urgente a `backend/src/ecs_ec/notifications/content.py` y `backend/src/ecs_ec/notifications/templates.py`, con evidencia/episodio, origen, base, calidad, fechas de detección/recepción y retraso; crear ocurrencia y entregas junto al estado de evaluación y usar el núcleo seguro de US2.
- [ ] T067 [US3] Añadir presentación de evidencia urgente en `frontend/src/components/notifications/UrgentEvidence.tsx` e integrarla en `frontend/src/components/notifications/DeliveryDetail.tsx`, diferenciando medido, calculado, sin fuente e información insuficiente y conservando unidades y períodos.
- [ ] T068 [US3] Añadir y ejecutar `backend/tests/integration/notifications/test_real_functional_producers.py` con recepción y fuentes base reales, cálculo real de la spec-004 y PDF real de la spec-005 conectados mediante T061; demostrar resultado persistido y evento seguro en la misma transacción de fallo funcional y que reintentos/duplicados no crean urgencias adicionales. No acreditar esta tarea con dobles de productores ni bloquear por ella la validación aislada de consumo.
- [ ] T069 [US3] Añadir y ejecutar `backend/tests/integration/notifications/test_episode_concurrency.py` con consumidores concurrentes, eventos repetidos, pausa y ventanas sucesivas sobre PostgreSQL real; exigir un único episodio/ocurrencia/entrega lógico y ningún cierre por dato insuficiente.
- [ ] T070 [US3] Medir el perfil mixto aprobado con reloj real en `backend/tests/integration/notifications/test_urgent_latency.py`: diez destinatarios, dos reglas periódicas y dos urgentes coincidentes dirigidas a todos, 40 entregas iniciales, cola vacía y cuatro plazas. Verificar aceptación local <=1 s y los 40 primeros intentos <=60 s desde su programación/detección válida, con app/base/correo operativos; medir también la equidad periódica y registrar CPU/memoria/versiones/tzdata, carga, referencias y tiempos en `specs/008-notificaciones-programables/validation/us3.md`. Ejecutar T055–T057/T068–T069; una prueba fuera de las condiciones del perfil no acredita SC-003.

**Checkpoint**: US3 funciona con condiciones y productores reales; una recepción tardía no reproduce todos sus períodos y una condición persistente conserva un solo episodio hasta normalidad válida.

## Phase 6: User Story 4 — revisar entregas y manejar fallos (P2)

**Goal**: Ofrecer historial protegido completo, filtros, decisiones de reenvío y conservación verificable, ampliando el núcleo durable ya entregado.
**Independent Test**: Cubrir los nueve escenarios US4: aceptación/transitorio/incertidumbre, permisos y correo cambiantes, reinicio/consolidación, historial propio del Operador, aislamiento del negocio y trazabilidad conservada; ningún reenvío manual se permite a Operador o Programador.
**Dependencia**: US2 y US3 para revisar ambos tipos de notificación y su evidencia; no se posponen a esta fase las garantías básicas de aceptación incierta ni límites de reintento.

### Pruebas de US4

- [ ] T071 [P] [US4] Escribir `backend/tests/contract/notifications/test_history_resends_api.py` para filtros de los dos GET de entregas y POST de reenvío: 403 ante filtros administrativos del Operador, 404 para entrega ajena, contenido autorizado actual, razón 1..500, `acknowledge_possible_duplicate=true`, 409 ante conflicto y respuesta vinculada idempotente. Prerrequisitos: US2–US3.
- [ ] T072 [P] [US4] Escribir `backend/tests/integration/notifications/test_recovery_resends.py` ampliando reinicios durante correo, fallo de registro tras aceptación, huecos ya intentados, reintentos conservados, revocación concurrente y reenvío vinculado; no suponer deduplicación externa por Message-ID. Prerrequisitos: US2–US3.
- [ ] T073 [P] [US4] Escribir `backend/tests/integration/notifications/test_retention.py` para 12 meses calendario, 29 de febrero, hora inexistente/repetida, revisión sustantiva y dependencia de evidencia; consultas/duplicados no reinician el plazo y la expiración técnica no elimina historia funcional. Prerrequisitos: US2–US3.
- [ ] T074 [P] [US4] Escribir `frontend/tests/unit/notification-history.test.tsx` y `frontend/tests/e2e/notification-history.spec.ts` para filtros, cancelada/indeterminada, acceso propio, permiso retirado y decisión explícita de posible repetición. Prerrequisitos: US2–US3.

### Implementación de US4

- [ ] T075 [US4] Completar consultas en `backend/src/ecs_ec/notifications/queries.py` con período, estado, regla/destinatario solo administrativos y cursor estable; revalidar el permiso sobre todo contenido histórico y omitir metadatos ajenos o auditoría inaccesible tras degradación de perfil.
- [ ] T076 [US4] Implementar reenvío explícito en `backend/src/ecs_ec/notifications/resends.py`: solo Administrador, regla vigente, destinatario elegible y estado fallido/indeterminado; razón 1..500 y reconocimiento verdadero, nueva generación/Message-ID y entrega vinculada con decisión auditada; conservar estado/intentos originales y rechazar aceptadas o reglas pausadas.
- [ ] T077 [US4] Completar filtros GET e implementar `POST /api/v1/notifications/deliveries/{delivery_id}/resends` en `backend/src/ecs_ec/notifications/api.py`; aplicar CSRF, clave por actor/operación, permiso actual antes de replay y respuestas `ResendResult`/`Problem` exactas, sin convertir una petición repetida en otro reenvío.
- [ ] T078 [US4] Completar protección del grafo de conservación en `backend/src/ecs_ec/notifications/retention.py`: usar el helper ya entregado por plataforma009; registro/revisión sustantiva inicia plazo, cada intento/decisión tiene el suyo, extender padres/evidencia hasta el máximo de dependientes protegidos y mantener identidad de cuentas desactivadas; no imponer borrado automático al vencer.
- [ ] T079 [US4] Añadir filtros e historial completo en `frontend/src/components/notifications/HistoryFilters.tsx`, `frontend/src/components/notifications/DeliveryList.tsx` y `frontend/src/components/notifications/DeliveryDetail.tsx`, mostrando razón funcional, intentos, destinatario efectivo permitido, períodos recuperados y vínculos sin direcciones ajenas ni consola técnica.
- [ ] T080 [US4] Implementar diálogo de reenvío en `frontend/src/components/notifications/ResendDialog.tsx` y cliente en `frontend/src/lib/api/notifications.ts`; exigir motivo/advertencia, evitar doble acción, conservar clave durante reintentos y enlazar entrega nueva/original sin ofrecer reenvío automático de indeterminadas.
- [ ] T081 [US4] Completar razones funcionales de cancelación/fallo y su exposición en `backend/src/ecs_ec/notifications/queries.py` y `backend/src/ecs_ec/notifications/dispatcher.py`; distinguir pausa, sustitución, pérdida de permisos y consolidación sin exponer excepciones técnicas ni originar otra alerta por el correo fallido.
- [ ] T082 [US4] Añadir y ejecutar `backend/tests/integration/notifications/test_business_isolation.py` con correo/telemetría indisponibles y módulos reales de recepción, consultas, costos y PDF; exigir mismos datos/reglas, colas técnicas acotadas y ausencia de cadena recursiva de correos.
- [ ] T083 [US4] Ejecutar T071–T074/T082 y escenarios 5, 6 y 8 del quickstart, corrigiendo fallos y registrando referencias de reinicio, reenvío y aniversarios en `specs/008-notificaciones-programables/validation/us4.md` sin secretos ni cuerpos personales.
- [ ] T084 [US4] Documentar consulta, reintentos, conservación y decisión ante indeterminados en `deploy/README.md` y `specs/008-notificaciones-programables/quickstart.md`, aclarando aceptación por servicio, posible repetición manual, alcance propio del Operador y autorización actual del historial.

**Checkpoint**: Las cuatro historias tienen validación independiente y el historial vincula regla, evidencia, destinatario, intentos, recuperación y decisión sin ampliar permisos históricos.

## Phase 7: Polish & Cross-Cutting Concerns — aceptación del módulo

- [ ] T085 Integrar señales propias en `backend/src/ecs_ec/observability/notifications.py` y dashboard `deploy/observability/grafana/dashboards/notifications.json`, reutilizando emisores y perfiles técnicos entregados por spec-007: un evento terminal por operación/intento, contexto opaco o span links, pérdidas visibles y sin datos sensibles; no crear recolectores, gateway o logging/tracing común en esta spec.
- [ ] T086 Añadir y ejecutar `backend/tests/integration/notifications/test_observability_integration.py` para correlación y conteos de programación/evaluación/despacho, caída de visores y colas acotadas; reutilizar infraestructura007 real y sus pruebas de acceso Programador, sin volver a implementar la autorización técnica.
- [ ] T087 Documentar configuración SMTP local/producción y enlaces de correo en `deploy/README.md` y `specs/008-notificaciones-programables/quickstart.md`; comprobar STARTTLS/certificado, remitente y URL pública configurables. Usar HTTPS/respaldo de plataforma009 y acceso técnico de spec-007, sin crear scripts de backup/restore aquí; registrar pruebas locales y pendientes VPS.
- [ ] T088 Ejecutar todas las comprobaciones implementadas del quickstart con PostgreSQL 18 y Mailpit reales, `uv sync --locked`, pytest/HTTPX, Vitest, Playwright y exportación Next; corregir fallos y registrar comandos/versiones/resultados en `specs/008-notificaciones-programables/validation/acceptance.md`, distinguiendo medición real de pruebas con reloj controlado.
- [ ] T089 Actualizar trazabilidad del módulo y enlaces a la arquitectura común en `README.md`, `docs/architecture.md` y `specs/008-notificaciones-programables/validation/coverage.md`, vinculando FR-001..FR-026 y SC-001..SC-009 a módulos, pruebas y evidencia; identificar dependencias reales aún pendientes sin acreditar su integración mediante dobles y preservar los marcadores de revisión de `checklists/notificaciones.md`.
- [ ] T090 Realizar las diez tareas con Administradores técnicos representativos según T033 y registrar resultados observados en `specs/008-notificaciones-programables/validation/usability.md`; exigir al menos nueve sin ayuda en <=3 minutos y corregir obstáculos; si no hay participantes/resultados reales, mantener esta tarea y SC-008 pendientes.
- [ ] T091 Validar el entorno VPS cuando estén disponibles despliegue, dominio y configuración reales conforme a `deploy/README.md`: referencias públicas desde otra red con autenticación/permisos, transporte de producción identificado y STARTTLS/certificado verificados; registrar evidencia en `specs/008-notificaciones-programables/validation/vps.md`, manteniendo pendientes estas comprobaciones si solo se ha probado localmente.
- [ ] T092 Revisar documentación de todos los archivos y contratos propios modificados, fórmulas/conversiones, límites del monolito, permisos y evidencia final en `specs/008-notificaciones-programables/validation/acceptance.md`; registrar resultados reales y trabajo abierto sin declarar completa una comprobación no realizada ni modificar los checklists de calidad sin solicitud de quien revisa.

**Checkpoint**: Aceptación funcional, usabilidad y entorno del módulo requieren resultados
reales. Las dependencias no realizadas se mantienen abiertas; el diseño no acredita entrega.

## Dependencies & Execution Order

La secuencia externa es plataforma009 → identidad006 y series001/002. El emisor007
se reutiliza para instrumentación; sus visores son opcionales para disponibilidad funcional.
US1 precede a US2; urgencias de consumo usan su núcleo y US4 amplía historial/reenvío.
La aceptación del puente de sistema US3 espera productores004 y 005 reales. Los productores
dependen de sus capacidades base, nunca de scheduler/dispatcher/SMTP o aceptación de 008.

La coordinación T014 precede a T045; habilitar scheduler en T050 solo tras T041.
El puente T061 consume eventos existentes, y T057/T067 esperan T049.

No se ejecutan automáticamente tareas de otra spec. Si falta su capacidad, resolverla con
su propietario siguiendo la hoja de ruta. Cambios en modelos, repositorio, API, cliente,
composición o Compose son secuenciales; `[P]` requiere archivos distintos y dependencias listas.

| Fase | Tareas | Cantidad |
| --- | --- | ---: |
| Setup | T001 | 1 |
| Fundaciones | T002–T015 | 14 |
| US1 | T016–T033 | 18 |
| US2 | T034–T054 | 21 |
| US3 | T055–T070 | 16 |
| US4 | T071–T084 | 14 |
| Cierre | T085–T092 | 8 |
| **Total** | **T001–T092** | **92** |

### Trazabilidad de requisitos


| Requisito | Tareas |
| --- | --- |
| FR-001 | spec-006 (cuentas/sesiones), T013, T021, T026, T044, T065 |
| FR-002 | T024, T025, T026, T028, T029, T030 |
| FR-003 | plataforma009 (auditoría), T061, T021, T042, T062 |
| FR-004 | T020, T029, T058, T066 |
| FR-005 | spec-006 (cuentas/sesiones), T021, T023, T025, T045 |
| FR-006 | T022, T023, T040, T050 |
| FR-007 | T018, T022, T040, T038, T041 |
| FR-008 | T046, T052, T070 |
| FR-009 | plataforma009 (auditoría), T042, T043, T039 |
| FR-010 | specs-001/002 (consultas), T011, T055, T058, T059 |
| FR-011 | T056, T059, T069 |
| FR-012 | T056, T060, T064, T065 |
| FR-013 | T056, T063, T068 |
| FR-014 | T004, T008, T009, T012, T040, T047, T069 |
| FR-015 | T002, T017, T036, T045, T014 |
| FR-016 | T024, T025, T040, T047 |
| FR-017 | T035, T047, T050, T072 |
| FR-018 | T036, T046, T048, T049 |
| FR-019 | T036, T046 |
| FR-020 | T071, T076, T077, T080 |
| FR-021 | T043, T051, T066, T067 |
| FR-022 | spec-007 (emisión común), T043, T062, T066, T086 |
| FR-023 | T034, T048, T075, T079 |
| FR-024 | plataforma009 (reloj/retención), T009, T073, T078, T083 |
| FR-025 | T015, T046, T050, T082, T085 |
| FR-026 | plataforma009 (Compose), T044, T051, T087, T091 |
| SC-001 | T002, T016, T017, T032, T071, T014, T083 |
| SC-002 | T018, T035, T047, T053, T072, T038, T041 |
| SC-003 | T052, T070 |
| SC-004 | T003, T055, T056, T068, T069 |
| SC-005 | T036, T046, T047, T072, T083 |
| SC-006 | T016, T034, T043, T071, spec-007 (acceso técnico), T086 |
| SC-007 | T073, T078, T083 |
| SC-008 | T033, T090 |
| SC-009 | plataforma009 (Compose), T044, T051, T082, T087, T088, T091 |


Las capacidades externas nombradas en la tabla remiten a sus propietarios en la hoja de
ruta. Cada fila combina integración local con prerrequisitos reales; no transfiere su alcance.

## Parallel Opportunities

- Fundaciones: T002, T003, T004, después de sus prerrequisitos y con datos de prueba aislados.
- US1: T016, T017, T018, T019, después de sus prerrequisitos y con datos de prueba aislados.
- US2: T034, T035, T036, T037, T038, T039, después de sus prerrequisitos y con datos de prueba aislados.
- US3: T055, T056, T057, después de sus prerrequisitos y con datos de prueba aislados.
- US4: T071, T072, T073, T074, después de sus prerrequisitos y con datos de prueba aislados.

## Implementation Strategy

MVP: configuración US1 con dependencias reales disponibles, seguido de correo local US2.
Añadir urgencias de consumo y conectar eventos de productores004/005 cuando se entreguen;
cerrar historial, conservación, instrumentación propia, usabilidad y VPS. El despliegue
común y los visores no se construyen como tareas ocultas de notificaciones.

## Notes

La matriz de traslado histórica se conserva en la hoja de ruta. No alterar checklists de
calidad de requisitos para acreditar trabajo de implementación. Los informes `validation/`
se crean cuando existan resultados observados, sin anticipar éxito ni incluir secretos.
