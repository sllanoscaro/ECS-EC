# Research: Notificaciones programables

Consultado: 2026-11-01. Alcance: spec-008 y stack indicado por el usuario. Las decisiones
arquitectónicas son propuestas de este diseño; la documentación no acredita la ejecución
de la combinación completa de dependencias.

## R1. Versiones reproducibles

**Decision**: Python 3.14 convencional con GIL, `fastapi==0.162.0` y uv; `.python-version`,
`pyproject.toml` y `uv.lock`, verificados con `uv sync --locked`. React 19.x/Next.js 16.x
con TypeScript, Node >=20.9 y npm con lockfile. Fijar parches e imágenes en implementación.

**Rationale**: FastAPI 0.162.0 está publicado y declara Python 3.14; uv lo soporta. Next.js
16 requiere Node >=20.9 y TypeScript >=5.1. Python y JavaScript necesitan lockfiles propios.
Los mínimos 18+/19+/16+ no se convierten en upgrades mayores automáticos.

**Alternatives considered**: Cambiar FastAPI sin necesidad, rangos sin lock o intentar
administrar npm mediante uv. La resolución real y los wheels se comprobarán al implementar.

**Sources**: [FastAPI 0.162.0](https://pypi.org/project/fastapi/0.162.0/),
[uv/Python](https://docs.astral.sh/uv/reference/policies/python/),
[lock/sync](https://docs.astral.sh/uv/concepts/projects/sync/),
[Next.js 16](https://nextjs.org/docs/app/guides/upgrading/version-16).

## R2. Next.js dentro del monolito

**Decision**: Build multietapa; Next `output: 'export'` genera `out/`, incorporado a la
imagen Python y servido por FastAPI junto con `/api/v1`. Datos privados llegan por API
autenticada; identificadores de reglas/entregas se seleccionan en query/estado cliente.

**Rationale**: Preserva una unidad de aplicación. La exportación no admite Server Actions,
SSR por solicitud, cookies de Next ni rutas dinámicas desconocidas al construir. Sesiones
y autorización corresponden a FastAPI; el HTML exportado no contiene datos privados.

**Alternatives considered**: Next SSR separado incumple la unidad actual; dos runtimes
en un contenedor añaden supervisión innecesaria. Sustituir Next contradice la elección.

**Sources**: [Export estático](https://nextjs.org/docs/app/guides/static-exports),
[StaticFiles FastAPI](https://fastapi.tiangolo.com/tutorial/static-files/),
[Docker multietapa](https://docs.docker.com/build/building/multi-stage/).

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

**Decision**: Loguru JSON saneado -> Alloy -> Loki; métricas derivadas con LogQL y visor
Grafana. Jaeger recibe trazas OTel/OTLP. Conserva Loki para las métricas solicitadas sin
describirlo como almacén general de métricas instrumentadas.

**Rationale**: LogQL permite conteos, tasas, agregación de valores y detección de ausencia.
Emitir un evento terminal por operación/intento y heartbeats. Pérdidas/cobertura desconocida
son visibles; métricas derivadas no sustituyen historial durable ni son exactas si faltan logs.
Etiquetas acotadas; referencias opacas en campos, nunca dimensiones por persona u operación.

**Alternatives considered**: Prometheus/Mimir serviría para métricas nativas generales,
pero añade una selección no solicitada. Envío de red síncrono en negocio o cola ilimitada
incumplen aislamiento; `enqueue=True` de Loguru no acredita por sí solo un límite de memoria.

**Sources**: [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html),
[LogQL métricas](https://grafana.com/docs/loki/latest/query/metric_queries/),
[Alloy](https://grafana.com/docs/alloy/latest/collect/logs-in-loki/),
[Jaeger APIs](https://www.jaegertracing.io/docs/latest/architecture/apis/),
[Badger persistente de instancia única](https://www.jaegertracing.io/docs/2.22/storage/badger/).

## R8. Compose, local y VPS

**Decision**: Aplicación y PostgreSQL; perfil local Mailpit y perfil técnico Alloy/Loki/
Grafana/Jaeger. PG18 monta `/var/lib/postgresql` y usa PGDATA `/var/lib/postgresql/18/docker`.
Salud de base/migraciones antes de app; SMTP/telemetría no condicionan readiness funcional.
VPS con HTTPS, URL pública y secretos externos. Consulta técnica separada de perfiles web.
La puerta técnica es Nginx de infraestructura con autenticación Basic sobre TLS y archivo
de Programadores por entorno, externo a cuentas funcionales. Cada solicitud revalida el
archivo sin caché; revocar sustituye el archivo y debe denegar la siguiente consulta.
Grafana usa permiso Viewer y Jaeger consulta solamente; las fuentes permanecen privadas.

**Rationale**: Compose no espera disponibilidad solo por iniciar contenedores; PG18 cambió
el volumen oficial. El desarrollo debe verificar correo y señales sin VPS ni servicios remotos.

**Alternatives considered**: Depender del proveedor final impide FR-026; enlaces localhost
en correo de producción no permiten acceso desde otras redes.

**Sources**: [Compose y salud](https://docs.docker.com/compose/how-tos/startup-order/),
[imagen PG18](https://github.com/docker-library/docs/blob/master/postgres/README.md),
[autenticación Nginx](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html).

## Resultado

Decisiones técnicas resueltas. Dominio, zona real y credenciales son configuración de
entorno; los valores de prueba no describen la instalación real. Identidad, series,
auditoría y resultados PDF/costos se integran con módulos de specs anteriores, todavía
no implementados. No quedan aclaraciones técnicas pendientes para esta fase de diseño.
