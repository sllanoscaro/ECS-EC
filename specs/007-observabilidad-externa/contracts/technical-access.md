# Contrato de acceso técnico, recursos y despliegue

[Plan](../plan.md), [modelo](../data-model.md), [catálogo](signals.md).
Infraestructura de 007, separada de sesiones/permisos funcionales006 y de auditoría009.

## Fronteras e interfaces

Un stack y gateway por entorno, con credenciales, volúmenes y fuentes separados.
El entorno efectivo se fija por listener/hostname, no por cabecera o selector del usuario.
No basar el aislamiento en el filtro LogQL ni en permisos por datasource no disponibles
universalmente en Grafana OSS. Local publica solo `127.0.0.1:3443`; segundo entorno de
prueba en `127.0.0.1:3444`. VPS usa hostname HTTPS propio, sin abrir puertos de fuentes.

| Interfaz humana detrás de TLS/Basic | Métodos permitidos / alcance |
| --- | --- |
| `/grafana/` y recursos estáticos versionados | GET/HEAD de UI y dashboards provisionados, sin guardar cambios |
| `/grafana/api/ds/query` | POST de consultas, limitado a fuentes locales provisionadas y Viewer |
| Lecturas de dashboard/fuentes y proxy de consulta Grafana | Allowlist exacta de rutas/metodos requerida por versión fijada; sin proxy genérico a URLs arbitrarias |
| `/logs/loki/api/v1/query`, `/logs/loki/api/v1/query_range` | GET de logs/métricas del entorno, finitos y acotados |
| `/logs/loki/api/v1/labels`, `/logs/loki/api/v1/label/{name}/values` | GET de catálogo de etiquetas; nombres de etiqueta permitidos |
| `/jaeger/` y su UI | GET/HEAD de estáticos y consultas; compatibilidad de rutas UI comprobada con Jaeger fijado |
| `/jaeger/api/v3/services`, `/jaeger/api/v3/operations` | GET de catálogo de trazas |
| `/jaeger/api/v3/traces` y `/jaeger/api/v3/traces/{traceId}` | GET de búsqueda y detalle v3, con parámetros oficiales; sin wildcard permisivo a administración |

Enumerar en `nginx.conf` las lecturas exactas usadas por UI/versiones resueltas. Denegar
por defecto el resto: escritura/configuración de dashboards/fuentes/usuarios, tokens,
alertas, ingesta, borrado, sampling remoto, profiling, admin y APIs de gestión. POST no
significa automáticamente escritura: la excepción `ds/query` es solo consulta. Preflight
mediante `nginx -t` y pruebas de rutas normales, codificadas, duplicación de slash,
traversal, Host y método; rutas desconocidas no se reenvían.

Sin WebSockets, Live, tail, SSE, caché de señales o URL pública de exportación que
entregue información después sin reautorizar. Consultas finitas <=30 s, logs <=10000 filas,
cuerpo de consulta <=64 KiB y 4 consultas
simultáneas por sujeto y entorno. Aplicar límites en gateway y backends; al excederlos
responder 4xx/timeout explícito sin resultado parcial presentado como completo.

## Identidad humana, provisión y revocación

Basic únicamente sobre TLS con CA confiable (CA local en desarrollo; no `curl -k`).
Archivo htpasswd por entorno con sujetos opacos individuales y hash bcrypt verificado
contra `crypt()` de la imagen fijada. No importar cuentas/contraseñas de006 ni compartir
credenciales humanas. Sin parámetro para declarar Programador: pertenecer al archivo
autorizado del entorno constituye esa autorización de lectura.

Procedimiento de operador del host, distinto del Programador de consulta:

1. `manage_programmer.sh grant --environment local --subject prog-test-01`: pedir
   contraseña por TTY, comprobar entorno y crear verificador; sin contraseña en argumentos,
   stdout, Git o historial. Directorio de secretos externo al repo.
2. Actualizar archivo temporal con permisos restrictivos, validar y reemplazar mediante
   rename atómico en el mismo directorio. Montar el **directorio** de credenciales en
   Nginx read-only: montar solo el archivo conservaría el inode anterior al sustituirlo.
3. `manage_programmer.sh revoke --environment local --subject prog-test-01`: retirar
   autorización por el mismo procedimiento. Registrar revisión y resultado operativos
   sin contraseña ni datos personales en telemetría.
4. La siguiente petición, también en keep-alive, vuelve a leer la autorización vigente.
   Fallo de lectura/configuración deniega acceso, sin fallback a cookie/identidad funcional.

Nginx valida en cada solicitud, sin caché de autorización/respuestas. Grafana AuthProxy
recibe identidad/rol fijados por gateway, `Viewer`, `sync_ttl=0`, `enable_login_token=false`,
registro público y autenticación anónima/local humana deshabilitados. Sobrescribir
cabeceras de identidad/rol y retirar Authorization/Cookie antes de upstream; restringir
AuthProxy a la red del gateway. La existencia de usuario Grafana no concede acceso por sí sola.
Las credenciales de bootstrap/admin de herramientas quedan solo en operación privada.

No hay streaming ni entregas diferidas humanas en este diseño. Cada consulta/página/
descarga técnica nueva requiere Basic vigente. Revocar no borra información ya recibida
ni interrumpe retroactivamente una respuesta cuya admisión fue previa; no permite otra
entrega autorizada por una sesión o enlace conservado.

## Identidades automáticas e ingesta

Red de almacenamiento privada; sin puertos host de Alloy, Loki, Grafana, Jaeger query,
Badger o OTLP. Aplicación y Alloy alcanzan solo listeners internos de ingesta TLS del
gateway. Certificados mTLS de proceso separados por entorno y productor, sin pertenencia
al archivo humano:

| Identidad técnica | Alcance |
| --- | --- |
| Aplicación OTel | POST `/v1/traces` al receptor OTLP/HTTP Jaeger del entorno, sin consultas |
| Alloy | POST `/loki/api/v1/push` al Loki del entorno, sin consulta/borrado |
| Salud del emisor | GET de ruta interna exacta `/collector-health` que expone contadores Alloy de transporte; filtrar antes de guardar, no acceder a señales de negocio |

`/collector-health` aporta evidencia de logs, no de Jaeger. La evidencia de exportación
de trazas procede del propio exportador OTLP en el monolito. Su persistencia consultable
se verifica mediante las consultas humanas autorizadas ya descritas, sin ampliar
permisos de lectura de las identidades de ingesta.

Certificados de proceso no validan Basic humano; contraseñas Programador no validan
mTLS de ingesta. El monolito escribe spool saneado; Alloy solo monta ese directorio en
lectura y escribe sus posiciones en otro volumen. Sin Docker socket ni logs generales
del host. Recolección sigue sin sesiones humanas abiertas. No registrar cabeceras,
query strings, IP, sujetos, contraseñas o certificados en access/error logs técnicos;
configurar salida mínima saneada o deshabilitar esos logs cuando la herramienta no pueda filtrarlos.

## Política inicial por entorno

Valores de diseño, verificables al implementar; no límites de carga aprobados del negocio.
La revisión de política identifica cada cambio y se muestra en visores.

| Recurso / señal | `local` y `vps` iniciales | `test` desechable |
| --- | --- | --- |
| Logs y métricas derivadas | 168 h, sin muestreo de logs terminales/control | 24 h, sin muestreo |
| Trazas | 168 h, ratio de raíz 1.0, hijos heredan | 24 h, ratio 1.0 para aceptación |
| Perfil de prueba de muestreo | Cambio explícito a ratio 0.1 con revisión y aviso | Solo caso de limitación, no prueba de cobertura completa |
| Cola logs | 1024 eventos totales, <=16 KiB cada uno; 1023 datos + 1 control reemplazable | Mismos valores, reducción explícita para saturación |
| Spool logs | 8 archivos de 16 MiB, <=128 MiB y TTL <=retención de logs | Mismos máximos o reducción registrada |
| Spans | <=256 activos, <=2048 pendientes, <=16 KiB/span; lotes <=512 | Igual, reducción explícita para saturación |
| Exportación OTLP | Timeout de red 5 s en exportador, sin flush por request | Igual |
| Heartbeat / continuidad | 15 s / desconocida tras 45 s sin señal | Reloj inyectable para casos unitarios; comprobación real 45 s en integración |
| Reintento de transporte | Presupuesto total OTLP 5 s, incluidos hasta 3 intentos; Alloy timeout 5 s por intento y 3 reintentos máximos fuera de negocio | Igual |
| Cuota técnica de disco | Spool 128 MiB, posiciones Alloy 64 MiB, Loki 2 GiB, Badger 2 GiB, Grafana 256 MiB por entorno | Cuotas menores explícitas, volúmenes independientes |
| Corte por disco | >=90 % de cuota: rechazar nueva ingesta técnica hasta espacio disponible y marcar pérdida; jamás borrar datos funcionales | Igual |

Los límites cuentan payloads serializados; medir memoria real, overhead de Python y
componentes con carga de prueba. No equiparar 16 MiB de payload de cola con RAM total.
Al llenarse cola: descarte del evento nuevo, contador y hueco de secuencia; control
conserva último snapshot sin bloquear. Al llenarse spool/destino se pierde telemetría y
se ve su limitación; no se hace backpressure al dominio. Workers técnicos son hilos/tareas
del lifespan, sin otro servicio propio. Reintentos del exportador y su librería deben
compartir el presupuesto, sin multiplicar silenciosamente deadlines.

Rotación/TTL de spool y cuotas se aplican en su worker. Los volúmenes usan cuotas reales
o tamaño fijo y límites de ingesta, no una promesa basada solo en TTL. Alcanzar cuota,
fallar escritura o fallar exporter se refleja en contadores/heartbeat; si el canal está
caído, la ausencia advierte desconocimiento y los contadores se recuperan cuando sea posible.

## Conservación y operación

Loki: TSDB filesystem, índice 24 h, compactor único con retención habilitada y directorio
persistente de marcadores/delete requests. Badger: Jaeger 2.22.0 instancia única,
`ephemeral=false`, keys/values persistentes y `ttl.spans` según perfil. TTL no equivale
a borrar físicamente en el mismo segundo: prueba de vencimiento con compacción/GC,
intervalo de compacción 10 min y demora de borrado 10 min; presupuesto de verificación
60 min tras TTL. Si no se verifica, aceptación pendiente, no borrado afirmado.

La retención de métricas derivadas es la de logs; no hay conservación independiente
implícita. La interfaz avisa cuando la ventana excede datos retenidos y distingue
muestreo, pérdidas y desconocimiento. No asumir que cambiar TTL afecta datos antiguos
retroactivamente. Nunca montar volúmenes de PostgreSQL/auditoría en recolectores ni usar
scripts de retirada técnica sobre mediciones/boletas/cálculos/PDF.

Compose añade `observability` como perfil opcional: `app` no tiene `depends_on` de estos
servicios ni readiness funcional ligada a ellos. Para operar solo negocio no se activa
el perfil. VPS conserva separación de redes/secretos, TLS y cuotas; su procedimiento
va en `deploy/technical-gateway/README.md` y `deploy/observability/README.md`, enlazados
desde el `deploy/README.md` común de009. Despliegue/VPS no se acredita con este documento.
