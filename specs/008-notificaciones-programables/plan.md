# Implementation Plan: Notificaciones programables y alertas por correo

**Branch/contexto**: `008-notificaciones-programables` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: `specs/008-notificaciones-programables/spec.md` y stack definido por el usuario.
El identificador proviene de `.specify/feature.json`; no se pudo verificar una rama Git en este entorno.

## Summary

Implementar configuración versionada de notificaciones, resúmenes periódicos, episodios
urgentes y entregas individuales por correo, con permisos de spec-006, calendario explícito,
recuperación durable y conservación funcional mínima de 12 meses calendario.
Solo el Administrador técnico configura y reenvía; el Operador consulta sus propias entregas.

FastAPI sirve la API y la exportación estática React/Next.js desde una única imagen.
Planificación, evaluación y despacho viven en el monolito; PostgreSQL conserva sus estados.
Docker Compose integra las dependencias de datos, correo local y observabilidad externa.
Este plan termina en Fase 1 de diseño; no genera implementación ni `tasks.md`.

## Technical Context

**Language/Version**: CPython 3.14 convencional con GIL; `requires-python = ">=3.14,<3.15"`.
TypeScript y Node.js >=20.9 para construir el frontend, fijando versiones exactas en implementación.

**Primary Dependencies**: `fastapi==0.162.0`, uv como gestor Python, Pydantic 2, Uvicorn,
SQLAlchemy 2 con Psycopg 3 y Alembic; React 19.x y Next.js 16.x App Router con `output: 'export'`.
npm y `package-lock.json` administran dependencias JavaScript. Acceso de base asíncrono
con `AsyncSession` y motor Psycopg; SMTP usa executor dedicado. Loguru produce logs JSON;
Grafana Loki almacena logs y calcula métricas derivadas con LogQL; OpenTelemetry exporta
trazas a Jaeger mediante OTLP. Grafana es el visor técnico y Alloy el recolector de logs.

**Storage**: PostgreSQL 18 como versión inicial dentro de 18+; transacciones, claves únicas,
JSONB para evidencia tipada e instantes `timestamptz` en UTC. Los mínimos 18+/19+/16+ del
usuario se concretan en versiones y digests fijados; no implican upgrades mayores automáticos.

**Testing**: pytest, HTTPX y PostgreSQL 18 real para contratos, concurrencia y recuperación;
reloj/transporte inyectables para calendario y fallos. Vitest/Testing Library y Playwright
para formularios, estados y permisos. Mailpit verifica SMTP local; un adaptador determinista
reproduce fallos antes/después de aceptación. SQLite no acredita bloqueos de PostgreSQL.

**Target Platform**: Linux con Docker Compose en desarrollo y VPS posterior con HTTPS.
Una imagen de aplicación y un proceso Uvicorn inicial, sin servidor Node en ejecución.
PostgreSQL, relay SMTP y observabilidad son dependencias, no servicios propios de negocio separados.

**Project Type**: Aplicación web monolítica modular con API HTTP y tareas internas durables.

**Performance Goals**: FR-008/SC-003: primer intento elegible <=60 s desde programación
o detección válida con aplicación y correo operativos. Bucle interno cada 5 s y cuatro
plazas de envío iniciales, prioridad urgente con equidad para periódicos; son parámetros
operativos ajustables, no garantías nuevas de volumen. Medir retraso de cola y preparación
end-to-end, también con competencia entre modalidades. No garantizar llegada a bandeja ni lectura.

**Constraints**: Tres intentos totales solo ante no aceptación transitoria confirmada,
con esperas de 1 y 5 minutos. Aceptación incierta exige decisión manual. Datos ausentes
no son cero. Zona IANA del edificio copiada a cada regla; `America/Santiago` es valor de
desarrollo configurable, no confirmación de la ubicación del edificio. Conservación funcional
de 12 meses calendario; telemetría tiene política propia. Fallos SMTP/telemetría no bloquean negocio.

**Scale/Scope**: Un edificio, siete categorías CAT-01..CAT-07, dos perfiles funcionales
y Programador externo. No se especifican cantidades de usuarios, reglas o envíos; no se
inventa un SLO de carga. Dimensionar la VPS con carga acordada, además de los casos de referencia.

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
└── checklists/requirements.md
```

`tasks.md` corresponde a `$speckit-tasks` y no se crea en esta fase.

### Source Code (repository root, estructura propuesta)

```text
pyproject.toml
uv.lock
.python-version
.env.example
Dockerfile
compose.yaml
backend/
├── src/ecs_ec/
│   ├── main.py
│   ├── cli.py                 # bootstrap administrativo controlado
│   ├── core/                  # configuración, reloj, unidad de trabajo y sesiones
│   ├── identity/              # integración spec-006
│   ├── consumption/           # integración specs-001/002
│   ├── audit/                 # historial administrativo funcional
│   ├── notifications/
│   │   ├── api.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── calendar.py
│   │   ├── evaluator.py
│   │   ├── scheduler.py
│   │   ├── dispatcher.py
│   │   ├── repository.py
│   │   └── transports.py
│   ├── observability/         # instrumentación, sin visor funcional
│   └── web/                   # export Next copiado durante build
├── migrations/
├── alembic.ini
└── tests/{unit,integration,contract}/
frontend/
├── package.json
├── package-lock.json
├── next.config.ts
├── src/app/notificaciones/
├── src/components/notifications/
├── src/lib/api/
└── tests/{unit,e2e}/
deploy/
├── observability/            # Alloy, Loki, Grafana y Jaeger
├── technical-gateway/        # Nginx y autorización técnica por entorno
└── README.md                 # TLS VPS, secretos, respaldo y restauración
```

**Structure Decision**: `backend/` y `frontend/` separan código/construcción dentro de un
único entregable. uv administra Python desde la raíz; npm construye frontend. Dominio y
servicios internos no dependen de HTTP/SMTP/Loki; adaptadores concretan sus contratos.
El repositorio contiene especificaciones; estos directorios son propuestos, no código existente.

## Phase 0: Research

[research.md](research.md) resuelve versiones, export estático, persistencia, calendario,
correo y observabilidad con fuentes oficiales. No quedan decisiones técnicas sin resolver.
Dominio público, credenciales del relay y zona real del edificio son configuración de
entorno y no se inventan para completar el plan.

## Phase 1: Design & Contracts

### Flujo durable

1. API valida sesión, contenido y destinatarios; guarda versión y auditoría en una
   transacción. La creación queda desactivada. Una revisión sustituye la anterior,
   cancela pendientes y queda pausada hasta activación explícita con vista previa vigente.
2. `lifespan` supervisa planificador, evaluador y despachador. Un advisory lock de sesión
   PostgreSQL elige planificador; perder la conexión impide seguir programando.
3. Eventos funcionales se registran atómicamente con su cambio de negocio en la misma
   base. Evaluar identidades únicas y solo la ventana más reciente admisible por regla.
   Un reloj detecta ausencias sin esperar datos. Episodio, cursor y entregas se confirman
   juntos. Datos insuficientes no normalizan episodios.
4. Claves únicas protegen ocurrencias/entregas. Reservar capacidad antes de reclamar;
   revalidar regla, cuenta, correo y permisos en transacción corta; registrar `en_intento`
   y confirmar antes de invocar SMTP fuera del event loop. Mutaciones concurrentes usan
   orden de bloqueos regla, cuenta, entrega. Ese inicio delimita la carrera con pausa/revocación.
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
- Integrar cuentas/sesiones/correos de spec-006, series/calidad de specs-001/002 y resultados
  funcionales de costos, PDF y auditoría como módulos internos. Dobles de prueba no acreditan
  integración final hasta ejecutar contra módulos reales.
- Producción: relay SMTP submission autenticado con STARTTLS obligatorio y certificado
  verificado (587), remitente autorizado y secretos externos. Proveedor intercambiable;
  desarrollo usa Mailpit sin red remota.
- Compose monta PostgreSQL 18 en `/var/lib/postgresql` y espera salud de base/migraciones.
  SMTP y observabilidad no condicionan readiness funcional. VPS: HTTPS, dirección pública,
  respaldo y restauración; no se ejecuta despliegue en esta fase.
- Loguru emite eventos saneados; Alloy -> Loki y consultas LogQL. Heartbeats/pérdidas
  hacen visible cobertura desconocida. Jaeger recibe OTLP; visores separados autorizan
  exclusivamente Programador, sin heredar permisos funcionales. Nginx técnico verifica
  credenciales externas por solicitud; sus fuentes permanecen en red privada.

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

### Verificación documental de esta fase

Contrato JSON analizado, 38 esquemas comprobados con JSON Schema Draft 2020-12 y 141
referencias locales resueltas. Se validaron nueve entradas de regla y se rechazaron diez
entradas inválidas de referencia, además del reconocimiento obligatorio de posible
repetición en reenvíos. Hay 13 operaciones con identificadores únicos y parámetros de
ruta declarados. Estas comprobaciones no ejecutan FastAPI, SMTP, Compose ni la interfaz;
la validación funcional prevista queda en `quickstart.md`.

## Complexity Tracking

Sin violaciones que justificar. Persistencia/exclusión mutua responden a reinicios y
duplicados exigidos; no se incorpora broker ni worker de negocio desplegable por separado.
