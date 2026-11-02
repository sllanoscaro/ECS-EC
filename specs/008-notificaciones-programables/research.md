# Research: Notificaciones programables

Consultado: 2026-11-01. Alcance: decisiones de notificaciones y referencias a las decisiones compartidas. Las decisiones
arquitectónicas son propuestas de este diseño; la documentación no acredita la ejecución
de la combinación completa de dependencias.

## R1. Versiones reproducibles

Decisión común trasladada a [plataforma009](../009-fundaciones-plataforma/research.md#r1-versiones-reproducibles).
Las versiones de referencia se centralizan en la [arquitectura](../../docs/architecture.md).

## R2. Next.js dentro del monolito

Construcción/exportación comunes: [plataforma009](../009-fundaciones-plataforma/research.md#r2-nextjs-dentro-del-monolito).
Este módulo consume la API autenticada y usa query/estado cliente para reglas/entregas.

## R3. Estado durable y concurrencia

**Decision**: PostgreSQL 18, SQLAlchemy 2/Psycopg 3 y Alembic. Programaciones, episodios,
eventos y entregas en la misma base. Claves únicas, transacciones cortas, `FOR UPDATE
SKIP LOCKED` para cola y advisory lock de sesión para elegir planificador. SMTP fuera
de transacciones, con intento previamente confirmado.

**Rationale**: PostgreSQL documenta SKIP LOCKED para consumidores de colas, no como una
vista consistente general. Unicidad lógica y exclusión del claim son garantías distintas.

**Alternatives considered**: Memoria pierde trabajo; Redis/Celery/worker independiente
añaden infraestructura y pueden contradecir el despliegue monolítico. No se necesita broker.

**Sources**: [SELECT PG18](https://www.postgresql.org/docs/18/sql-select.html),
[advisory locks](https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS),
[Psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html).

## R4. Ejecución y aislamiento

**Decision**: Supervisor interno desde `lifespan`, bucles cada 5 s y notificación tras
cambios confirmados. Reservar capacidad antes de reclamar entrega; SMTP bloqueante en
executor dedicado de cuatro plazas iniciales. Cierre ordenado y reconciliación al iniciar.

**Rationale**: Debe funcionar sin solicitudes humanas. El polling deja margen para el plazo
de 60 s, pero el cumplimiento se mide end-to-end, incluso con competencia de modalidades.
Elegir SQLAlchemy 2.x con motor asíncrono y Psycopg 3 para que esperas de base tampoco
bloqueen el event loop; SMTP permanece fuera de la unidad de trabajo.

**Alternatives considered**: `BackgroundTasks` como única programación no conserva
horarios; cron externo no debe poseer lógica ni políticas de calendario del producto.

**Source**: [Lifespan](https://fastapi.tiangolo.com/advanced/events/).

## R5. Calendario y retención

**Decision**: UTC para instantes, zona IANA por regla y `zoneinfo`. Fijar `tzdata` y usarlo
reproduciblemente mediante `PYTHONTZPATH` vacío. Intervalos por tiempo transcurrido;
recurrencias conservan día/hora nominales. Repetición usa `fold=0`; huecos se detectan por
roundtrip UTC y avanzan al primer instante local válido posterior. Día inexistente usa
último válido sin perder el ancla: enero31 -> febrero28/29 -> marzo31.

**Rationale**: ZoneInfo no implementa por sí solo FR-007. Guardar intención, resultado UTC
y versión temporal. Retención suma 12 meses calendario desde registro/revisión, con último
día válido en aniversario de 29 de febrero, conforme a spec-002.
En retención, una hora repetida usa la segunda ocurrencia (`fold=1`) y una inexistente
el primer instante válido posterior; el scheduler usa la primera repetida (`fold=0`).

**Alternatives considered**: 24 h para recurrencia diaria cambia la hora local; cron/rrule
sin adaptación pueden omitir o duplicar. No sustituir 12 meses por 365 días.

**Source**: [ZoneInfo Python 3.14](https://docs.python.org/3.14/library/zoneinfo.html).

## R6. Correo y aceptación

**Decision**: Adaptador SMTP con `smtplib`/`email`; submission autenticado con STARTTLS
verificado en producción. Relay, remitente y secretos son configuración. Mailpit local
y transporte determinista en pruebas. Un mensaje por cuenta; `Message-ID` estable para
reintentos y otro identificador para un reenvío manual vinculado.

**Rationale**: Confirmación final de DATA acredita aceptación por servicio, no bandeja.
Desconexión tras posible aceptación deja incertidumbre. Un error QUIT posterior a aceptación
conocida no la revoca. SMTP y PostgreSQL no tienen confirmación atómica común.

**Alternatives considered**: Reintentar todo timeout duplica posibles aceptaciones;
`Message-ID` no garantiza deduplicación. Proveedor comercial concreto no es necesario
para fijar el contrato ni validar localmente.

**Sources**: [smtplib](https://docs.python.org/3.14/library/smtplib.html),
[RFC 5321](https://www.rfc-editor.org/rfc/rfc5321),
[Mailpit](https://mailpit.axllent.org/docs/).

## R7. Loguru, métricas Loki y Jaeger

Infraestructura y políticas trasladadas a [spec-007](../007-observabilidad-externa/research.md#r7-loguru-métricas-loki-y-jaeger).
Notificaciones conserva instrumentación de programación/evaluación/entrega y su dashboard.

## R8. Compose, local y VPS

Base común y operación: [plataforma009](../009-fundaciones-plataforma/research.md#r3-compose-y-persistencia-localvps).
Acceso técnico: [spec-007](../007-observabilidad-externa/research.md#acceso-técnico-localvps).
Mailpit, relay SMTP y enlaces autenticados de correo se validan en [quickstart](quickstart.md).

## Resultado

Decisiones técnicas resueltas. Dominio, zona real y credenciales son configuración de
entorno; los valores de prueba no describen la instalación real. Identidad, series,
auditoría y resultados PDF/costos se integran con módulos de specs anteriores, todavía
no implementados. No quedan aclaraciones técnicas pendientes para esta fase de diseño.
