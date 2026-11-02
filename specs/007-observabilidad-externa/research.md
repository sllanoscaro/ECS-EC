# Research: Observabilidad externa y Programador

**Fecha**: 2026-11-02. Fase0 de [plan](plan.md). Se leyeron [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md), [constitución](../../.specify/memory/constitution.md),
[spec](spec.md), [tareas trasladadas](tasks.md) y contratos de propietarios. La investigación
técnica se repartió con un agente de solo lectura y se contrastó con fuentes primarias.
Sin instalación, ejecución, aceptación o comprobación de compatibilidad del stack.

Las decisiones R7 y acceso local/VPS conservan sus títulos/anclajes para enlaces de008.
Los cinco trabajos trasladados de007 quedan incorporados al diseño y pendientes en tareas.

## R1. Límites de propiedad y despliegue

**Decision**: módulo `observability` en el proceso del monolito; herramientas técnicas
como infraestructura opcional, una instancia/volúmenes por entorno. 009 conserva scaffold,
core y auditoría; 001–006 instrumentan sus operaciones; 008 instrumentará su propio dominio.

**Rationale**: respeta constitución y hoja de ruta. Emisor implementable antes que productores
y visores; aceptación completa espera productores reales. Ninguna transacción depende
obligatoriamente del transporte de telemetría ni del consumidor de notificaciones.

**Alternatives considered**: worker propio desplegado aparte viola la unidad seleccionada;
recrear recepción, identidad o auditoría en007 transfiere indebidamente propiedad.

## R2. Sobre seguro y resultados comunes

**Decision**: JSON tipado con allowlist y esquema cerrado, saneado antes de Loguru/OTel/
colas. UTC inequívoco y duración monotónica. Éxito, rechazo esperado y fallo inesperado
con significado común entre señales. Solo códigos registrados, sin mensajes/excepciones
libres, datos personales, contenidos o valores energéticos/financieros individuales.

**Rationale**: `diagnose=False` evita exposición de variables en diagnósticos, pero no
sanea por sí solo un mensaje o atributo. Instrumentación manual de dominio evita captura
automática de URL/query, SQL, cabeceras y excepciones sensibles.

**Alternatives considered**: redacción posterior en Loki deja copias sensibles previas;
registrar `str(exception)` o stacks completos puede filtrar payloads y secretos.

**Sources**: [API de Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html),
[excepciones OpenTelemetry](https://opentelemetry.io/docs/specs/otel/trace/exceptions/).
El esquema y los límites concretos son decisiones del proyecto, no garantías de esas librerías.

## R3. Recursos y aislamiento de emisión

**Decision**: cola propia de1024 eventos <=16KiB, admisión sin espera y spool rotativo
<=128MiB. Un slot de control reemplazable conserva el último heartbeat; registrar descartes
y secuencias. OTel: <=2048 spans pendientes, lotes <=512, <=256 activos y atributos acotados.
`OTLPSpanExporter(timeout=5)` y deadline total de reintentos explícito; cierre técnico
acotado a5s en lifespan, jamás flush por petición. Valores completos en contrato técnico.

**Rationale**: `enqueue=True` no declara capacidad máxima de Loguru. El código actual de
Python `BatchSpanProcessor` indica que su `export_timeout_millis` no pasa el timeout a
`export`; el timeout de red debe configurarse en exportador. La operación de negocio
no escribe disco ni envía red directamente para producir señales.

**Alternatives considered**: cola ilimitada, envío síncrono y confiar únicamente en
`OTEL_BSP_EXPORT_TIMEOUT` no acreditan las garantías de aislamiento requeridas.

**Sources**: [Loguru](https://loguru.readthedocs.io/en/stable/api/logger.html),
[código SDK Python](https://opentelemetry-python.readthedocs.io/en/latest/_modules/opentelemetry/sdk/trace/export.html),
[exportador OTLP](https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html).
Los límites de activos/tamaño y observación de pérdidas requieren envoltorios propios probados.

## R4. Correlación confiable y continuidad

**Decision**: referencias opacas internas de operación/publicación/intento/ejecución.
Reutilizar las identidades confiables de003/002, mapear claves semánticas a referencia
opaca por entorno y no exportar nombres/hashes. Contextvars en ejecución y referencias
durables del productor entre ejecuciones. Tras reinicio, otra traza con misma operación;
link solo si sobrevivió contexto confiable. Cabeceras y textos públicos no fijan parentesco.

**Rationale**: reenvío y recuperación no son el mismo hecho; los contratos existentes
ya diferencian ambos. No hace falta cambiar PAS600/SFTP, mediciones ni PDF para relacionar
señales. Perder un padre no autoriza inventar un span continuo.

**Alternatives considered**: correlación por nombre/valor externo mezcla operaciones;
añadir trace IDs al archivo nativo modifica contrato ajeno. El span no es evidencia durable.

**Sources**: [contrato003](../003-simulador-pas600-sftp/contracts/sftp-reception.md),
[contrato002](../002-registro-retencion-consumo/contracts/integrations.md),
[contrato005](../005-generar-reportes-pdf/contracts/integrations.md).

## R5. Semántica de métricas y unicidad

**Decision**: evento terminal único por transición lógica/operación; admisiones, ejecuciones,
etapas, archivos, posiciones y novedades con medidas distintas. Resúmenes de registros
por intento completo, no por fragmento. Error%=100*fallos inesperados/todas las operaciones
terminadas del mismo tipo/ventana; denominador cero/desconocido → N/D. Dimensiones cerradas.

Precisar el cierre de recepción: `processing|partial_failure` no emiten
`reception.completed`; la ejecución fallida emite `execution.completed` con
`unexpected_error` y `counts=null`. Solo la transición durable a `completed` publica
el resumen completo del intento, incluidas aceptaciones anteriores a la recuperación.
`execution_unexpected_error_percent` tiene su propio denominador de ejecuciones. El
caso3 aceptados/fallo/2 aceptados recuperados produce dos ejecuciones, un intento y
cinco novedades, sin duplicación; una lectura sin procesamiento no crea otro terminal.

**Rationale**: diez consultas con ocho éxitos y dos fallos deben dar10 y20%, sin incluir
las decisiones de autorización como consultas extra. Un nuevo intento evalúa posiciones
de nuevo; duplicados no son nuevas aceptaciones. La cola no participa en commit: una
caída entre commit/emisión es pérdida posible y limita exactitud técnica.

**Alternatives considered**: contar líneas de etapa infla operaciones; contar invocaciones
recuperadas duplica incorporaciones; métricas por UUID/archivo elevan cardinalidad sin límite.

**Sources**: [métricas LogQL](https://grafana.com/docs/loki/latest/query/metric_queries/),
[semántica de recepción002](../002-registro-retencion-consumo/contracts/integrations.md),
[medidas de PDF005](../005-generar-reportes-pdf/contracts/integrations.md).

## R6. Cobertura y recolección

**Decision**: heartbeat15s y continuidad desconocida tras45s; estado separado por señal,
última observación y pérdidas. Persistir posiciones de Alloy y conservar timestamp,
etiquetas y JSON idénticos al releer. Conciliar ventanas cerradas con secuencias,
contadores y estado del transporte; consultas no verificables quedan desconocidas.

El sobre separa `log_collector_status`/`last_log_collector_success` de
`trace_export_status`/`last_trace_export_success`, con contadores acumulados de spans
confirmados y lotes fallidos, sin multiplicar por reintento. El éxito OTLP no demuestra
persistencia consultable: contrastar trazas esperadas y política con Jaeger bajo
autorización Programador. Probar caídas independientes Jaeger y Alloy/Loki y mantener
los huecos históricos tras recuperar; no interpretar falta de actividad como fallo.

**Rationale**: Alloy permite posiciones persistentes, pero pérdida/corrupción puede causar
relectura o descarte. Su estado healthy no demuestra entrega. El componente agrega
`filename`: retirarlo antes de Loki. Loki describe deduplicación de timestamp/etiquetas/
cuerpo iguales; probar esa propiedad en reinicios, sin asumir exactly-once por event_id.
La WAL de `loki.write` figura experimental: no se requiere para el diseño inicial.

**Alternatives considered**: heartbeat solo, estado healthy o panel sin datos convertido
siempre en cero esconden fallos. Muestreo de trazas no afecta por sí solo cobertura de logs.

**Sources**: [Alloy file](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/),
[Alloy write](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.write/),
[componentes Loki y deduplicación](https://grafana.com/docs/loki/latest/get-started/components/).

## R7. Loguru, métricas Loki y Jaeger

**Decision**: conservar Loguru JSON → Alloy → Loki/LogQL y Grafana para logs/métricas
derivadas; OTel/OTLP → Jaeger2.22.0 con Badger persistente de instancia única. API v3 para
verificación programática, rutas UI versionadas para navegación de personas.

**Rationale**: LogQL admite conteos, tasas, sumas, duraciones, cuantiles y ausencia;
no se describe Loki como almacén general de métricas instrumentadas. Jaeger recibe
trazas OTLP; no almacena logs/métricas. Badger evita un almacén remoto adicional en la
escala inicial. La API JSON usada internamente por UI no tiene la estabilidad de v3.

**Alternatives considered**: Prometheus/Mimir añade otro almacén no necesario para este
catálogo; Badger compartido entre varios procesos no es el diseño de instancia única;
almacén remoto de trazas se reserva para una necesidad de escala posterior.

**Sources**: [LogQL](https://grafana.com/docs/loki/latest/query/metric_queries/),
[Alloy](https://grafana.com/docs/alloy/latest/collect/logs-in-loki/),
[Jaeger APIs2.22](https://www.jaegertracing.io/docs/2.22/architecture/apis/),
[Badger2.22](https://www.jaegertracing.io/docs/2.22/storage/badger/),
[configuración Badger v2.22.0](https://github.com/jaegertracing/jaeger/blob/v2.22.0/cmd/jaeger/config-badger.yaml).

El [OpenAPI oficial v3](https://github.com/jaegertracing/jaeger-idl/blob/main/swagger/api_v3/query_service.openapi.yaml)
identifica lecturas GET de servicios, operaciones, búsqueda y detalle de trazas. La
allowlist inicial expone esas lecturas; no necesita habilitar todo el prefijo v3.

## Acceso técnico local/VPS

**Decision**: Nginx Basic/TLS, archivo de Programadores individual por entorno, autorización
en cada petición. Reemplazo atómico en directorio montado, sin caché. Stack separado por
entorno, Grafana Viewer vía AuthProxy sin login token, fuentes privadas y allowlist de
consultas. Credenciales mTLS de ingesta separadas. Sin streams o exportaciones que
permitan nuevas entregas sin autorización vigente.

**Rationale**: el módulo Basic valida contra archivo; el código abre el archivo durante
el handler. Montar directorio preserva la sustitución por rename, a diferencia del inode
de un archivo montado. AuthProxy puede emitir cookie si se habilita login token: se deja
inhabilitado. Viewer puede consultar fuentes, sin requerir Editor. Separar stacks evita
confiar en filtros del cliente como autorización entre entornos.

**Alternatives considered**: reutilizar sesión006 concede equivalencia indebida;
cookie independiente o caché de autorización demora revocación; Grafana OSS Viewer solo
no sirve como barrera universal entre fuentes de varios entornos; exponer Loki/OTLP
sin frontera permitiría bypass. Identidad federada puede evaluarse después sin omitir
revocación ni permisos por entorno.

**Sources**: [Nginx Basic](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html),
[handler Nginx](https://github.com/nginx/nginx/blob/master/src/http/modules/ngx_http_auth_basic_module.c),
[Grafana AuthProxy](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/auth-proxy/),
[roles Grafana](https://grafana.com/docs/grafana/latest/administration/roles-and-permissions/).
La lectura por petición/revocación efectiva se prueba además sobre imagen fijada y keep-alive.

## R9. Retención y muestreo por señal

**Decision**: logs/métricas derivadas168h y trazas168h para local/VPS; perfil desechable24h
para ambas fuentes. Sin muestreo de terminales/control; trazas ratio1.0 inicial/aceptación.
Caso separado ratio0.1 muestra limitación. Cuotas técnicas por volumen y spool rotativo;
no afectar los doce meses calendario de evidencia funcional.

**Rationale**: Loki requiere retención explícita con compactor, índice24h y marcadores
persistentes; borrado asíncrono. Badger define persistencia y `ttl.spans`. TTL no equivale
a borrado físico instantáneo. Comprobar vencimiento, consulta y compacción/GC; presupuesto
operativo60min tras TTL en pruebas. Cuota/ingesta acotada impiden disco ilimitado durante
ese período; exceso produce pérdida técnica visible.

**Alternatives considered**: heredar12meses aumenta almacenamiento sin requisito;
TTL sin compactor/GC ni cuotas no acredita retiro ni límites. Muestreo parcial no prueba SC-002.

**Sources**: [retención Loki](https://grafana.com/docs/loki/latest/operations/storage/retention/),
[Badger2.22](https://www.jaegertracing.io/docs/2.22/storage/badger/).

## R10. Versiones y verificación reproducible

**Decision**: mantener pila común y Jaeger2.22.0; resolver versiones restantes/digests al
implementar con uv.lock/Compose, comprobar CPython3.14 y registrar comandos/resultados.
La selección de APIs y límites está cerrada; resolver lockfiles no es una aclaración de alcance.

**Rationale**: SDK OTel1.45.1 declara Python3.14; Loguru0.7.3 declara rango Python amplio,
pero esa metadata no demuestra la ejecución del conjunto. No instalar dependencias ni
simular compatibilidad desde planificación. Pruebas reales preceden a habilitación.

**Alternatives considered**: inventar digests/compatibilidad ejecutada o modificar versiones
comunes fuera de su propietario produce evidencia falsa; cambiar a otra pila no está justificado.

**Sources**: [OTel SDK1.45.1](https://pypi.org/project/opentelemetry-sdk/1.45.1/),
[Loguru](https://pypi.org/project/loguru/), [arquitectura común](../../docs/architecture.md).

## Cierre de fase0

Sin incertidumbres de diseño pendientes. Capacidades externas aún sin implementar,
verificación de versiones y dominios/secretos reales son prerrequisitos de implementación/
operación, no resultados obtenidos. [Quickstart](quickstart.md) define la evidencia pendiente,
incluidas personas para SC-008. No se marcaron checklists ni tareas como realizadas.
