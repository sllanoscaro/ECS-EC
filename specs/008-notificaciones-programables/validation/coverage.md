# Trazabilidad008 —2026-11-25

Implementación propia en `backend/src/ecs_ec/notifications/`, adaptador técnico en
`backend/src/ecs_ec/observability/notifications.py` y UI en
`frontend/src/components/notifications/`. Los proveedores reales001/002/004/005/006/009
conservan su propiedad. Las pruebas no convierten fixtures en productores aceptados.

| Requisito | Implementación y comprobación local |
| --- | --- |
| FR-001 | API, permisos006 y SessionGuard; contratos de reglas/historial y Playwright. |
| FR-002 | services/models/RuleEditor/RuleActions; creación desactivada, revisiones, preview y pausa. |
| FR-003 | catalog/summaries/event_consumer; recepción, calidad, auditoría y productores004/005 reales. |
| FR-004 | schemas/ConditionFields/evaluator; cuatro comparaciones Decimal, límites y unidades. |
| FR-005 | recipients/preview/identity_coordination; cuentas vigentes y totalidad de permisos. |
| FR-006 | calendar/scheduler/lifecycle; intervalos, activación futura y ejecución autónoma. |
| FR-007 | calendar/calendar_reconciliation; tzdata fijado, DST, ancla y reconciliación interrumpida. |
| FR-008 | dispatcher y test_urgent_latency; perfil supervisado40 y equidad3:1 separados. |
| FR-009 | summaries/SummaryCoverage; íntegro cero/positivo, huecos, desconocido y primer corte vacío. |
| FR-010 | adapters/evaluator/episodes; consumo real, total20 y base, intervalos/cobertura íntegros. |
| FR-011 | episodes; apertura única, normalidad válida y no cierre ante insuficiencia. |
| FR-012 | absence/source_status;15min por reloj, aceptación nueva, duplicados y sin fuente. |
| FR-013 | event_consumer/consumed_event; último período admisible, omisiones e identidades durables. |
| FR-014 | modelos/migraciones/idempotency; restricciones y consumidores PostgreSQL concurrentes. |
| FR-015 | participante006 y prepare_attempt; regla→cuenta→entrega e inicio durable antes de SMTP. |
| FR-016 | activación/pausa/revisión; cancelación de pendientes y conservación de iniciados. |
| FR-017 | recovery; indeterminados y consolidación exclusiva de nunca intentados/períodos originales. |
| FR-018 | transports/dispatcher; tres intentos y esperas1/5min, DATA/QUIT y cierre de socket. |
| FR-019 | recovery/resends; pérdida de confirmación sin reintento SMTP automático. |
| FR-020 | decisión auditada y ResendDialog; motivo, reconocimiento, generación/vínculo e idempotencia. |
| FR-021 | content/templates/UrgentEvidence; captura tipada, HTML escapado y referencias protegidas. |
| FR-022 | adaptador007, catálogo cerrado y panel; privacidad, operación/intento y colas/pérdidas. |
| FR-023 | queries/DeliveryList/DeliveryDetail; filtros, ámbito propio, estados e intentos efectivos. |
| FR-024 | retention/anniversary009;12 meses calendario, padres/evidencia, lectura sin renovación. |
| FR-025 | Runner/business_isolation; monolito, SMTP fuera del loop y fallos técnicos aislados. |
| FR-026 | Compose/mail/settings y enlaces del entorno; local real; relay/VPS enT091. |

| Criterio | Evidencia / límite |
| --- | --- |
| SC-001 | Contratos, RBAC, coordinación y revisión/pausa; [US1](us1.md)/[US4](us4.md). |
| SC-002 | Calendario, exclusión, reconciliación y recuperación; [US2](us2.md). |
| SC-003 | Dos casos separados de40 entregas: supervisor real y equidad con ambas colas; [US3](us3.md). |
| SC-004 | Condiciones y productores001/002/004/005 reales; [US3](us3.md). |
| SC-005 | Transitorios, DATA/QUIT, registro perdido, indeterminación y decisión; [US4](us4.md). |
| SC-006 | Alcance funcional actual, Programador técnico separado y privacidad; [señales](observability.md). |
| SC-007 | Aniversarios y grafo protegido; [US4](us4.md). |
| SC-008 | **Pendiente** de diez tareas con administradores representativos; [protocolo](usability.md). |
| SC-009 | Entorno local y aislamiento verificados; enlaces externos/relay reales siguen en [VPS](vps.md). |

El [informe de aceptación](acceptance.md) conserva comandos/resultados finales. La
integración transversal del paso6 y la aceptación humana/externa de otras specs siguen
en sus listas propias. No se cierran por asociación con estos resultados008.
