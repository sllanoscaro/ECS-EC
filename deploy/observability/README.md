# Stack técnico007

Cobertura técnica001–006, dashboard y cuotas verificados localmente en el paso4.
Retención24h/GC, recorrido final sin salida remota y personas siguen sujetos a sus
pruebas. [Estado y evidencia](../../specs/007-observabilidad-externa/validation/step4.md).

Loguru privado → spool saneado → Alloy → Nginx mTLS → Loki TSDB/filesystem;
SDK OTel → OTLP/HTTP mTLS → Jaeger2.22/Badger. Grafana Viewer muestra las señales.
Los hilos técnicos viven en el monolito; no hay servicio de negocio adicional,
almacén de métricas nativas, tablas007 ni visor en la interfaz funcional.
001–006 conservan permisos, transacciones y auditoría009.008 instrumenta su propio
módulo mediante el emisor007 y publica el dashboard `ecs-notifications`.

## Preparar y activar

Requiere Linux, Docker/Compose, uv/Python3.14 y OpenSSL. Versiones/digests están
fijados en `versions.env`, `compose.yaml` y lockfiles. La instalación del host debe
proporcionar `mkfs.ext4` y dispositivos loop para el perfil de cuotas comprobado.
Preparar una raíz nueva, externa al repo, sin datos funcionales:

```sh
uv sync --locked
bash scripts/observability/prepare_local.sh --environment test
export OBS_RESOURCE_ROOT="$HOME/.local/state/ecs-ec/observability/test"
export OBS_UID="$(id -u)" OBS_ENVIRONMENT=test OBS_PORT=3444
export OBS_PUBLIC_URL=https://localhost:3444/grafana/
export OBS_STORE_SUBNET=172.30.8.0/24 OBS_STORE_DYNAMIC_RANGE=172.30.8.128/25
export OBS_GATEWAY_IP=172.30.8.2 OBS_RETENTION=24h OBS_RETENTION_HOURS=24
export OBS_REQUIRE_QUOTAS=true OBS_POLICY_REVISION=007-v1 OBS_TRACE_RATIO=1.0
# Construir antes de crear los recursos privilegiados exclusivos del host.
docker compose build app
uv run python scripts/observability/prepare_quotas.py prepare   --root "$OBS_RESOURCE_ROOT" --image ecs-ec-platform:local --allow-host-mounts
bash scripts/observability/manage_programmer.sh grant --environment test --subject prog-test-01
docker compose -p ecs007-test --profile observability config --quiet
docker compose -p ecs007-test --profile observability up -d technical-gateway
# Con identidad006, DB y migraciones ya configuradas según su guía:
export OBS_ENABLED=true
docker compose -p ecs007-test --profile observability up -d app
```

La imagen local usada por `--image` debe ser la construida por Compose; comprobar
su nombre con `docker compose config --images` o usar un tag explícito mediante
`docker build -t ecs007-host-tools:local .`. El script necesita `nsenter`, mount y
chown de esa imagen; crea únicamente cinco imágenes ext4 nuevas y sus mounts
exclusivos. Rechaza destinos no vacíos, symlinks, raíces compartidas o dentro del
repo. No modifica scripts Spec Kit ni configura montajes persistentes del sistema.

Para local: preparar otra raíz/CA/proyecto, puerto3443, retención168h y subred sin
colisión. No compartir datos, posiciones, claves o credenciales entre entornos.
`app` no depende de los receptores: `OBS_ENABLED=false` y ausencia del perfil permiten
operar negocio. Configuración técnica inválida deshabilita emisión con motivo seguro.
`OBS_REQUIRE_QUOTAS=false` solo admite fixtures parciales de entorno test; no acredita
cuotas ni aceptación integral. UID debe coincidir con el propietario de los recursos.
Los procesos montan solo su certificado y CA pública, nunca la clave CA privada.

## Cuotas y conservación

Presupuestos máximos por entorno: spool128MiB, posiciones64MiB, Loki2GiB,
Badger2GiB y Grafana256MiB. Cinco sistemas de archivos distintos limitan físicamente
el crecimiento; metadatos ext4 reducen el espacio utilizable y se miden aparte.
El presupuesto usado incluye bloques reservados/no disponibles para el proceso:
`total - f_bavail * f_frsize`. El10% reservado impide consumir el margen con usuarios
sin privilegios. No equivale al tamaño de payload ni a RAM; memoria/overhead se miden aparte.

La aplicación ve únicamente cinco directorios vacíos `.capacity` en lectura,
escribe un estado acotado atómico en `quota-status/status.json` cada15s y valida
capacidad antes de habilitar emisión. No lee contenidos de Loki/Badger/Grafana.
Gateway exige estado válido, de su entorno, <=30s y cada cuota <90%; en otro caso
rechaza ingesta con507. Salud mTLS y consulta humana conservan sus permisos.
Estado ausente/estancado no autoriza ingesta. No publicar manualmente un estado
permitido ni conceder al Programador acceso operativo al host.

Spool:1023 datos+1 control, <=16KiB/evento, ocho segmentos de16MiB. TTL desde el
primer timestamp original de cada segmento, conservado al escribir/reiniciar: añadir
heartbeats no renueva registros viejos. La retirada conservadora del segmento puede
perder registros jóvenes y lo contabiliza. Nunca reescribir fecha/cuerpo/event_id.
Spans:256 activos/2048 pendientes, lotes512, presupuesto OTLP total5s/<=3 intentos;
shutdown total5s. Saturación/rotación/cierre cuentan pérdidas y no cambian commits.

Loki: índice24h, compactor10min, demora de borrado10min, marcadores persistentes.
Badger: una instancia, consistencia y directorios persistentes, mantenimiento10min.
Retención normal168h/test24h; cambios de TTL no se presumen retroactivos. Consulta
404 no certifica liberación física. [Ensayo prolongado](../../specs/007-observabilidad-externa/validation/retention.md)
conserva por separado consulta, spool y GC, con verificación hasta60min tras TTL.
Los doce meses funcionales y el historial006 conservan sus propias políticas.

## Consultar y diagnosticar

Abrir `/grafana/d/ecs-platform/platform` con Basic/TLS vigente. Importar la CA pública,
sin desactivar verificación TLS. [Provisión/revocación](../technical-gateway/README.md).
Panel `ecsec-coverage-panel` nativo de Grafana, fuente manual local y sin dependencias
remotas. Solo ese identificador se admite como plugin sin firma; no habilitar una
allowlist global. Conserva Viewer y las APIs finitas autorizadas existentes.

Ventana inicial15min/selecciones1min–24h, UTC `[inicio,fin)`, corte, versión, revisión,
unidades, denominadores y cobertura independiente de logs/trazas. Concilia event_id,
cuerpo, secuencias, pérdidas y heartbeats que encuadran el corte; >=10000 filas o fallo
produce unknown. Ventana abierta es provisional. Jaeger debe contener las trazas
esperadas: una confirmación OTLP no demuestra persistencia. Sin heartbeat45s no hay
continuidad demostrada; no inventar fallo por ausencia de nuevos lotes.

El panel calcula medidas sobre eventos únicos recuperados, sin IDs como dimensiones.
Muestra N/D para proporciones sin cobertura completa/denominador positivo, y conteos
observados con sus causas. El agregado nativo LogQL sirve de contraste: un replay
idéntico dio1001 entregas frente a1000 eventos únicos; se señala `replay_en_agregado`
y cobertura parcial. El panel nativo de entregas brutas no es un total lógico exacto.
[Catálogo y fórmulas](../../specs/007-observabilidad-externa/contracts/signals.md).

Filtrar operación/resultado/severidad o referencia opaca; abrir traza en otra pestaña
para evitar que el router Grafana capture la ruta Jaeger. «Otras ejecuciones» filtra
operation_ref/publication_ref del mismo entorno. No reconstruir relaciones por nombres.
Códigos tienen textos de catálogo, sin excepciones ni datos energéticos/financieros.

Para otra revisión/ratio, generar dashboard privado coincidente antes de desplegar:

```sh
uv run python scripts/observability/render_dashboard.py --help
```

El generador incluye `platform.json` y `notifications.json` con la misma política.
La puerta técnica admite lectura de ambos UID conocidos; las escrituras y los UID
ajenos siguen denegados. [Evidencia008](../../specs/008-notificaciones-programables/validation/observability.md).
Definir `OBS_DASHBOARD_DIRECTORY` con el directorio generado. Solo ratios1.0 y0.1;
0.1 exige revisión explícita distinta de007-v1, aviso y cobertura limitada de trazas.
Logs terminales/control nunca se muestrean. Aceptación técnica usa1.0.

## Recuperación y limpieza

Restaurar receptores con sus propios recursos; conservar huecos históricos. Alloy
expone inicio/reinicios de proceso: reiniciar o perder posiciones no restaura exactitud.
El gateway resuelve DNS privado; la siguiente consulta vuelve a validar Basic. Rotar
TLS preparando otra raíz válida, sin sobrescribir material existente inválido.

Para desmontar: detener **solo** el proyecto técnico y sus procesos que usen estos
mounts, comprobar ausencia de usuarios y ejecutar `prepare_quotas.py unmount` con
los mismos argumentos raíz/imagen/`--allow-host-mounts`. Verifica cada loop/backing
contra su manifiesto; conserva imágenes/datos y no usa force/lazy. No desmontar durante
el ensayo24h. No hay remount automático: tras reinicio del host, verificar/restablecer
los montajes propios antes de habilitar telemetría; la validación fallará cerrada.

Backup técnico: detener sus procesos y copiar directorios/posiciones con permisos y
versiones; nunca compartir Badger entre procesos, CA o entornos. Restauración integral
técnica y VPS siguen sin acreditarse. VPS necesita hostname/TLS, binding/firewall,
cuotas/montajes durables y nueva matriz de aislamiento. [Hoja de ruta](../../docs/implementation-roadmap.md).
