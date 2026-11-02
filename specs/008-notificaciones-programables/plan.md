# Implementation Plan: Notificaciones programables y alertas por correo

**Branch/contexto**: `008-notificaciones-programables` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: [spec.md](spec.md), [arquitectura común](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). El identificador es el contexto de
funcionalidad; la selección de Spec Kit no equivale a una rama Git creada.

## Summary

Implementar configuración versionada de notificaciones, resúmenes periódicos, episodios
urgentes y entregas individuales por correo, con permisos de spec-006, calendario explícito,
recuperación durable y conservación funcional mínima de 12 meses calendario.
Solo el Administrador técnico configura y reenvía; el Operador consulta sus propias entregas.

FastAPI sirve la API y la exportación estática React/Next.js desde una única imagen.
Planificación, evaluación y despacho viven en el monolito; PostgreSQL conserva sus estados.
Docker Compose integra las dependencias de datos, correo local y observabilidad externa.
Diseño previo a implementación, con trabajo propio en [tasks.md](tasks.md).
La base común se construye en plataforma009; identidad en 006, consumo en 001/002
y emisores/visores técnicos en 007. Esta spec integra esas capacidades sin construirlas.

## Technical Context

**Language/Version**: Python 3.14 convencional y TypeScript conforme a la arquitectura común.
**Primary Dependencies**: FastAPI, SQLAlchemy/Psycopg asíncronos y React/Next exportado;
reutilizar manifiestos/lockfiles de plataforma009. SMTP estándar con executor dedicado.
**Storage**: PostgreSQL 18; tablas propias de reglas, evidencia, episodios y entregas.
**Testing**: pytest/HTTPX con PostgreSQL real, Vitest/Testing Library, Playwright y Mailpit;
reloj/transporte inyectables para casos de calendario, concurrencia y aceptación incierta.
**Target Platform**: Monolito local/VPS definido por plataforma009; correo local y producción configurables.
**Project Type**: Módulo de notificaciones con programación, evaluación y despacho internos durables.

**Performance Goals**: FR-008/SC-003: cada primer intento <=60 s desde programación o
detección válida en el perfil aprobado: 10 destinatarios elegibles, dos reglas periódicas
y dos urgentes coincidentes, las cuatro dirigidas a esas diez cuentas, 40 entregas iniciales,
cola vacía, cuatro plazas de envío y transporte local con aceptación confirmada <=1 s.
Medir los 40 resultados con reloj real y registrar recursos/versiones; el bucle inicial
es de 5 s. La selección urgente conserva equidad para periódicos. El perfil no garantiza
volúmenes distintos ni llegada a bandeja o lectura.

**Constraints**: Tres intentos totales solo ante no aceptación transitoria confirmada,
con esperas de 1 y 5 minutos. Aceptación incierta exige decisión manual. Datos ausentes
no son cero. Zona IANA del edificio copiada a cada regla; `America/Santiago` es valor de
desarrollo configurable, no confirmación de la ubicación del edificio. Conservación funcional
de 12 meses calendario; telemetría tiene política propia. Fallos SMTP/telemetría no bloquean negocio.

**Scale/Scope**: Un edificio, siete categorías CAT-01..CAT-07, dos perfiles funcionales
y Programador externo. El perfil de aceptación fija 10 destinatarios, cuatro reglas y
40 entregas; no establece máximos del producto ni un SLO para cargas distintas. Dimensionar
la VPS con su carga real y conservar los recursos del perfil medido en la evidencia.

## Constitution Check

*Gate evaluado antes de investigación y reexaminado después del diseño de Fase 1.*

| Principio/restricción | Previo | Evidencia del diseño | Posterior |
| --- | --- | --- | --- |
| I. Propósito eléctrico | PASS | Recepción/calidad y alertas sobre series existentes; sin nuevos umbrales monetarios. | PASS |
| II. Monolito modular | PASS | Una imagen FastAPI con export Next; programación y despacho internos. Dependencias externas documentadas. | PASS |
| III. Documentación integral | PASS | Estructura, contratos y guía reproducible; cada archivo, función, clase, componente, prueba y script propio deberá documentarse. | PASS |
| IV. Integridad y trazabilidad | PASS | Decimal/kWh, evidencia inmutable, zonas, cortes, claves estables y tratamiento explícito de vacíos/duplicados. | PASS |
| V. Visualización verificable | PASS | UI/correo comparten contenido versionado, unidades, períodos, calidad y estados distinguibles. | PASS |
| Rendimiento/conservación | PASS | Plazo de 60 s de FR-008 y 12 meses desde registro/revisión, sin sustituirlos por 365 días. | PASS |
| Autorización/verificación | PASS | Permisos actuales en servidor; casos de calendario, datos incompletos, concurrencia y fuentes. | PASS |

No hay excepciones constitucionales. SSR dinámico o un worker propio independiente
requerirían revisar el diseño y tramitar la enmienda correspondiente antes de incorporarlos.
Los PASS acreditan el diseño, no una implementación ejecutada.

## Project Structure

### Documentation (this feature)

```text
specs/008-notificaciones-programables/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.json
│   ├── integrations.md
│   └── ui.md
├── tasks.md
└── checklists/{requirements.md,notificaciones.md}
```

`tasks.md` conserva únicamente trabajo propio de notificaciones; las dependencias
externas y el orden de integración figuran en la hoja de ruta.

### Source Code (repository root, estructura propuesta)

```text
backend/src/ecs_ec/notifications/
  __init__.py, api.py, schemas.py, models.py, services.py, calendar.py
  calendar_reconciliation.py, evaluator.py, scheduler.py, dispatcher.py
  repository.py, transports.py, ports.py, adapters.py, lifecycle.py
  idempotency.py, preview.py, catalog.py, recipients.py, templates.py
  summaries.py, queries.py, resends.py, recovery.py, retention.py
backend/migrations/versions/notifications_008_initial.py
backend/tests/{unit,integration,contract}/notifications/
backend/src/ecs_ec/observability/notifications.py
frontend/src/app/notificaciones/
frontend/src/components/notifications/
frontend/src/lib/api/notifications.ts
frontend/tests/{unit,e2e}/
deploy/observability/grafana/dashboards/notifications.json
```

**Structure Decision**: Este árbol muestra archivos del módulo y su instrumentación.
La estructura general y los manifiestos son de [plataforma009](../009-fundaciones-plataforma/plan.md).
Las migraciones propias se enlazan al head existente y no crean tablas de audit/identity/consumption.
Notificaciones añade rutas, participante de identidad y servicios internos al registro común;
el registro ampliable y el frontend base ya deben existir. El código todavía no está implementado.

## Phase 0: Research

[research.md](research.md) resuelve persistencia propia, calendario y correo, y enlaza
la investigación común trasladada a 009/007. No quedan decisiones técnicas sin resolver.
Dominio público, credenciales del relay y zona real del edificio son configuración de
entorno y no se inventan para completar el plan.

## Phase 1: Design & Contracts

### Flujo durable

1. API valida sesión, contenido y destinatarios; guarda versión y auditoría en una
   transacción. La creación queda desactivada. Una revisión sustituye la anterior,
   cancela pendientes y queda pausada hasta activación explícita con vista previa vigente.
2. `lifespan` supervisa planificador, evaluador y despachador. Un advisory lock de sesión
   PostgreSQL elige planificador; perder la conexión impide seguir programando. Antes de
   habilitar planificación, el líder compara tzdata instalada con la versión registrada,
   reconcilia solo futuros no materializados y preserva ocurrencias existentes e historial.
   La reconciliación es transaccional/reanudable por regla y conserva el ancla nominal;
   invalida previews afectados. Los vencidos conservan la política de recuperación existente.
3. Eventos funcionales se registran atómicamente con su cambio de negocio en la misma
   base mediante `audit/events.py` y `FunctionalEvent` de `audit/models.py`, compartidos
   por productores y consumidores sin importar el módulo de notificaciones desde costos/PDF. Evaluar identidades únicas y solo la ventana más reciente admisible por regla.
   Un reloj detecta ausencias sin esperar datos. Episodio, cursor y entregas se confirman
   juntos. Datos insuficientes no normalizan episodios.
4. Claves únicas protegen ocurrencias/entregas. Reservar capacidad antes de reclamar;
   revalidar regla, cuenta, correo y permisos en transacción corta; registrar `en_intento`
   y confirmar antes de invocar SMTP fuera del event loop. Mutaciones concurrentes usan
   orden de bloqueos regla, cuenta, entrega. El registro neutral de participantes se implementa en
   [identidad006](../006-acceso-usuarios-rbac/contracts/coordination.md); esta spec conecta
   su participante concreto antes de habilitar cualquier despacho. Para una mutación que
   afecta varias reglas, bloquearlas por UUID ordenado antes de la cuenta, revalidar el conjunto
   y reintentar si cambió. El inicio durable delimita la carrera con pausa/revocación/correo.
5. Confirmación SMTP final produce `aceptada`; rechazo transitorio confirmado produce
   `pendiente` con próxima fecha hasta tres intentos. Timeout o reinicio con aceptación
   desconocida produce `indeterminada`. `Message-ID` no garantiza deduplicación externa.
6. Reinicio: reconciliar intentos abiertos y consolidar solo periódicos vencidos nunca
   intentados y aún autorizados por versión/cuenta; conservar períodos y vínculos originales.
   Excluir aceptados, indeterminados y cualquier entrega ya intentada. Un reintento existente
   conserva identidad/plazo; un fallo de registro posterior a SMTP no acredita no aceptación.

### Integración y operación

- [data-model.md](data-model.md): entidades, restricciones, conservación y transiciones.
- [contracts/openapi.json](contracts/openapi.json): API HTTP, esquemas y errores.
- [contracts/integrations.md](contracts/integrations.md): eventos, calendario, SMTP y señales.
- [contracts/ui.md](contracts/ui.md): navegación, formularios y contenido funcional.
- [quickstart.md](quickstart.md): comandos previstos y escenarios de validación.
- Consumir [plataforma009](../009-fundaciones-plataforma/plan.md) para core/auditoría,
  [identidad006](../006-acceso-usuarios-rbac/tasks.md) y
  [consumo001](../001-visualizar-consumo-categorias/tasks.md)/[historial002](../002-registro-retencion-consumo/tasks.md)
  como dependencias reales; completar su planificación/implementación en sus propias specs. Costos se construye mediante [plan004](../004-costos-tarifa-bt43/plan.md)
  y [tareas004](../004-costos-tarifa-bt43/tasks.md); PDF mediante
  [plan005](../005-generar-reportes-pdf/plan.md) y [tareas005](../005-generar-reportes-pdf/tasks.md).
  Cada productor entrega resultados reales persistidos y su evento funcional de fallo en la
  misma transacción del registro de ese fallo. La integración de 008 solo consume esos eventos
  y no implementa cálculos BT4.3 ni genera PDF. Su dependencia bloquea las alertas de sistema
  correspondientes y la aceptación integral, sin bloquear US1, US2 o urgencias de consumo.
  No existe dependencia de los productores sobre scheduler, dispatcher ni consumidor de la spec-008;
  los puertos compartidos de identidad/series/auditoría se reutilizan por capacidad, evitando ciclos.
  Dobles no acreditan la integración final de un productor ausente.
- Resúmenes: cada tipo conserva cobertura funcional y conteo conocido o NULL. Cobertura completa
  requiere historia íntegra de toda la ventana; incompleta conserva huecos conocidos y alcance
  observado; desconocida señala integridad no determinable o fuente no consultable. Solo todos
  completos con cero eventos permiten `sin_novedades`; todos completos con algún evento,
  `disponible`; cualquier incompleto/desconocido, `informacion_insuficiente`. Mantener conteos
  observados con sus límites; una consulta fallida no crea cero. La evidencia de cobertura
  pertenece a auditoría funcional y sobrevive a la retención técnica independiente.
- Producción: relay SMTP submission autenticado con STARTTLS obligatorio y certificado
  verificado (587), remitente autorizado y secretos externos. Proveedor intercambiable;
  desarrollo usa Mailpit sin red remota.
- Entorno común y respaldo/restauración: [plataforma009](../009-fundaciones-plataforma/quickstart.md).
  Esta spec incorpora Mailpit al perfil local y documenta/valida relay SMTP y enlaces del correo.
- Infraestructura técnica y acceso Programador: [spec-007](../007-observabilidad-externa/tasks.md).
  Esta spec emite señales de sus etapas usando sus APIs y agrega su dashboard. La disponibilidad
  de SMTP/visores no bloquea negocio y su retención no sustituye cobertura funcional.

### Cobertura

| Requisitos | Diseño | Validación |
| --- | --- | --- |
| FR-001..005, 023 | Versiones, catálogo y autorización | Roles, destinatarios y auditoría administrativa |
| FR-006..009 | Calendario/ocurrencias | 06:00, intervalos, DST, fin de mes, ventanas y <=60 s |
| FR-010..013 | Evidencia, cursor y episodios | Límites, incompletos, CAT-01 calculada, sin fuente y lote histórico |
| FR-014..020 | Unicidad, intentos y recuperación | Concurrencia, fallos, reinicios y cambio de correo/permisos |
| FR-021..022, 024 | Contenido protegido y retención | Redacción, enlaces y aniversarios calendario |
| FR-025..026 | Dependencias aisladas y correo local | Caídas, Mailpit y validación en VPS |

SC-001..007 y SC-009 se verifican según la guía. SC-008 necesita además administradores
representativos: 9 de 10 tareas sin ayuda en <=3 minutos; no se sustituye por automatización.

### Verificación documental

La reorganización requiere comprobar enlaces relativos, referencias locales OpenAPI,
identificadores de tareas y resolución de rutas con los scripts oficiales de Spec Kit.
Estas comprobaciones no ejecutan aplicación, SMTP, costos o PDF reales. La aceptación
funcional, los participantes de usabilidad y la medición de 40 entregas siguen pendientes.
Los marcadores de checklists conservan el estado de quien revisa.

## Complexity Tracking

Sin violaciones que justificar. Persistencia/exclusión mutua responden a reinicios y
duplicados exigidos; no se incorpora broker ni worker de negocio desplegable por separado.
