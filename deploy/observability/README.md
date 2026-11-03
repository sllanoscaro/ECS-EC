# Stack técnico007

Implementación local parcial: emisor fundamental y MVP de acceso. Sigue pendiente
la cobertura001–006, el catálogo completo/dashboard US3, cuotas/retención real/aislamiento
funcional US4 y evaluación humana. [Evidencia](../../specs/007-observabilidad-externa/validation/access.md).

Loguru privado → spool saneado → Alloy/posiciones persistentes → Nginx mTLS →
Loki TSDB/filesystem. SDK OTel privado → OTLP/HTTP mTLS → Jaeger2.22/Badger.
Grafana Viewer consulta Loki y presenta logs/métricas; Jaeger ofrece navegación de
trazas. No hay worker de negocio, almacén de métricas nativas, visor funcional ni
tablas SQL007. Los productores conservan sus permisos, transacciones y auditoría009.

[Preparación/acceso](../technical-gateway/README.md) y
[scripts](../../scripts/observability/README.md). Dependencias exactas en `uv.lock`
y digests en `versions.env`/`compose.yaml`; actualizar ambos deliberadamente.
Validar con los binarios fijados antes de habilitar una versión distinta.

## Activación local y segundo entorno

El perfil es opcional. `app` no depende de herramientas técnicas y `OBS_ENABLED=false`
por defecto. Arranca y atiende funcionalmente sin el perfil; TLS/spool solo se habilitan
con configuración válida. UID del proceso debe coincidir con el propietario de los
recursos externos, mediante `OBS_UID`; los mounts se limitan a claves del propio
proceso. CA privada y registro humano nunca se montan en aplicación/Alloy/Grafana.

Para el entorno de prueba, usar otro proyecto y recursos, sin reutilizar DB/volúmenes
funcionales o entornos reales:

```sh
bash scripts/observability/prepare_local.sh --environment test
export OBS_RESOURCE_ROOT="$HOME/.local/state/ecs-ec/observability/test"
export OBS_UID="$(id -u)" OBS_ENVIRONMENT=test OBS_PORT=3444
export OBS_PUBLIC_URL=https://localhost:3444/grafana/
export OBS_STORE_SUBNET=172.30.8.0/24 OBS_STORE_DYNAMIC_RANGE=172.30.8.128/25
export OBS_GATEWAY_IP=172.30.8.2 OBS_RETENTION=24h OBS_RETENTION_HOURS=24
bash scripts/observability/manage_programmer.sh grant --environment test --subject prog-test-01
docker compose -p ecs007-test --profile observability up -d technical-gateway
```

Loki/Badger/Grafana/posiciones/spool son directorios técnicos separados en la raíz
externa preparada. Sobreviven al reinicio y `compose down`; no usar `down -v` como
procedimiento de retención ni compartir rutas entre proyectos. Las subredes propuestas
son configuración local: comprobar colisiones antes de usarlas. Fuentes sin puertos host,
bridges internos sin IPv4 del host y gateway con red de entrada independiente.

Para emisión de la aplicación, exportar `OBS_ENABLED=true`, compilar imagen y recrear
`app` con su DB/migraciones reales disponibles. Ese paso no instrumenta automáticamente
operaciones de dominio: cada propietario debe incorporar sus llamadas. Los módulos
006/001/002/004 implementados aún esperan esa integración con007.

Fixture interna reproducible de transporte (no cobertura funcional): después de
construir la imagen de aplicación y configurar un stack **test**, ejecutar en su red:

```sh
export OBS_ENABLED=true
docker compose build app
docker compose -p ecs007-test --profile observability run --rm --no-deps \
  -v "$PWD/scripts/observability/emit_reference.py:/tmp/emit_reference.py:ro" \
  app /app/.venv/bin/python /tmp/emit_reference.py
```

Requiere un PostgreSQL password configurado para resolver Compose, aunque la fixture
no usa DB ni levanta servicios funcionales. Se admiten10 operaciones sintéticas8/2,
no diez consultas funcionales. Guardar corte/referencias de stdout; repetir agrega
otra carga y debe usar una ventana/boot explícitos al comparar resultados.

## Consulta, evidencia y limitaciones

Abrir `https://localhost:3443/grafana/d/ecs-platform/platform` (test3444).
Dashboard inicial: UTC, ventana15min, política/configuración esperadas, logs observados
y conteos por tipo/resultado, cobertura desconocida por defecto. No rellena ausencia
con cero. Acceso directo por Basic a `/logs/loki/api/v1/query[_range]` y
`/jaeger/api/v3/{services,operations,traces}`. SearchDepth<=10000, ventanas<=24h,
consultas finitas30s; rutas UI `jaeger/search` y `jaeger/trace/<32hex>`.
Los límites/semántica completos están en el [catálogo](../../specs/007-observabilidad-externa/contracts/signals.md).
Los paneles US3 de conciliación, pérdidas/replay, porcentajes y percentiles todavía
no están implementados: no inferir exactitud desde los contadores iniciales.

Heartbeat cada15s distingue recolección de logs y exportación OTLP, con fechas de
éxito nullable. Más45s sin heartbeat implica desconocimiento. OTLP confirmado no
prueba persistencia; comprobar traza como Programador. Falta de actividad no inventa
fallo. `available` describe la última evidencia con su edad, no garantía actual.

Spool:1023 datos+1 control,<=16KiB/evento,8x16MiB/TTL<=retención. Spans:256 activos,
2048 pendientes, lotes512, deadline total5s/<=3 intentos; shutdown comparte5s.
Rotación y cierre cuentan pérdida conservadora; los huecos no se reparan por observar
un heartbeat posterior. No usar logs como auditoría durable ni criterio de commit.

Loki usa índice24h/compactor10min/delete delay10min/retención168h (test24h).
Jaeger Badger persistente usa el mismo TTL técnico. Configuración validada; vencimiento
real/GC hasta60min después de TTL todavía requiere T059. Las cuotas persistentes de
2GiB/2GiB/64MiB/256MiB y corte90% de T056 siguen pendientes. No se declara cumplimiento
de esas cuotas ni retirada física por fijar un TTL o por usar binds separados.
Los doce meses funcionales no cambian y ningún servicio técnico monta PostgreSQL.

## Recuperación y VPS

Receptores caídos: la aplicación continúa; observar estado/última fecha/pérdidas,
restaurar servicios con los mismos recursos y conservar huecos históricos.
Nginx resuelve DNS privado cada5s; herramientas reiniciadas no necesitan cambiar
credenciales ni reautorizar por cookie. Pruebas de revocación y fallo de archivo
requieren Basic vigente en cada nueva solicitud. No reconstruir contexto desde nombres.

Restauración técnica: detener servicios técnicos del proyecto, copiar sus directorios
externos/posiciones con permisos y versiones registrados y volver a iniciarlos; nunca
restaurar Badger compartido por dos procesos ni mezclar CA/credenciales/entornos.
La copia/restauración integral y cuotas/retención reales quedan por ejecutar, sin
atribuirles validación por este procedimiento. Fuentes funcionales siguen sus backups009.

VPS requiere hostname/certificado CA real, Host/URL/binding/firewall explícitos, cuotas,
secretos externos, pruebas de aislamiento y restauración; no hereda aceptación local.
[Hoja de ruta](../../docs/implementation-roadmap.md) conserva esas dependencias.
