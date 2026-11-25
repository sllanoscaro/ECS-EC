# Recursos técnicos externos

`bash scripts/observability/prepare_local.sh --environment local` crea la CA y
certificados TLS/mTLS en `~/.local/state/ecs-ec/observability/local` (test usa
otro directorio/CA). `--root /ruta/externa` cambia solo la raíz privada; nunca
usar un descendiente del repo, symlinks ni una raíz compartida legible por terceros.
Requiere Python3, OpenSSL y Linux/flock. No importa cuentas006.

El script publica atómicamente la preparación; repetir valida permisos, expiración,
CA y correspondencia clave/certificado. Ante material inválido falla y preserva lo
existente. No renueva automáticamente; preparar nueva raíz y cambiar mounts de forma
explícita. Hojas válidas30d y CA365d; validar antes de24h de su vencimiento.
El operador conserva CA/key privada; los procesos solo deben montar su hoja/key y
CA pública, nunca la clave CA o credenciales de otro proceso. Claves/certificados
0600 y directorios0700; ajustar mounts/UID de forma explícita al integrar Compose.

`local` y `test` nunca comparten CA, credenciales, spool ni volúmenes. El script no
configura VPS ni acredita autenticación, autorización, retención o transporte integrado.

Los mounts `clients/{gateway,app,alloy,health}` contienen solo CA pública y
hoja/clave de su proceso; el directorio raíz conserva la CA privada fuera de todos
los contenedores. `data/{alloy,loki,jaeger,grafana}` separa persistencia técnica.
Python3.14 usa validación X.509 estricta: la CA incorpora keyUsage crítico de firma.
`OBS_UID` debe coincidir con `id -u` de quien prepara esos recursos.

`manage_programmer.sh` requiere `uv sync --locked`; alta/revocación usan registro
JSON/htpasswd privados por entorno, lock, fsync y rename. Una discrepancia entre
registro y autorización tras interrupción requiere recuperación explícita del host;
revocar primero retirando authorized. La contraseña solo entra por TTY y nunca se
lee de argumentos/stdin/env. Ver [frontera](../../deploy/technical-gateway/README.md).

`emit_reference.py` produce una fixture interna limitada a test para probar transporte
con el emisor real. Imprime referencias/corte/salud técnicos; no ejecuta consultas de
negocio y no acredita cobertura001–006. Ejecutarlo en red de ingesta del stack con
certificados de aplicación/salud, nunca como endpoint público. Ver comando reproducible
en [stack](../../deploy/observability/README.md).

## Cuotas y dashboard

`prepare_quotas.py prepare|unmount --root /raíz/privada --image <imagen-local>
--allow-host-mounts` requiere intención explícita de operar mounts exclusivos. Preparar
TLS primero, con sus destinos técnicos vacíos. Usa Docker privilegiado sin red y
nsenter al namespace de montaje del host para las cinco imágenes ext4 nuevas;
no toca volúmenes funcionales ni configura fstab. No admite sobrescribir recursos.
`unmount` verifica propietario, mountpoint exacto y loop/backing registrado; conserva
imágenes para revisión. Si falla a mitad, conserva manifiesto y estado para limpieza
verificada, sin desmontar rutas ajenas. El perfil comprobado es Linux local/test,
no un procedimiento de VPS ya validado. [Operación y reservas](../../deploy/observability/README.md).

`render_dashboard.py --environment test --policy-revision 007-sampling-test
--trace-ratio 0.1 --output /raíz/privada/dashboard` genera `platform.json` y
`notifications.json` con la misma política, a partir de sus dashboards versionados.
Cada archivo se publica atómicamente. Salida externa0700/0600, sin secretos ni red.
Configurar OBS_DASHBOARD_DIRECTORY con ese directorio y alinear revisión/ratio del
emisor. Admite1.0/0.1; ratio0.1 exige revisión distinta de007-v1. El módulo JS del
plugin es fuente manual, no un bundle generado; se prueba con Node --test.

## Ensayo reanudable24h

`retention_probe.py start` exige raíz test propia con manifiesto de cuotas, CA y stack
exclusivo. El contenedor `<project>-worker` es una fixture técnica privada que ejecuta
el emisor real con sus certificados/spool, sin HTTP de negocio; el operador puede
usar el app del proyecto como productor ajustando explícitamente su fixture. No se
añade este worker a la composición de producción. La contraseña de prueba debe
residir en archivo propio0600, sin mostrarse en argumentos ni resultados:

```sh
uv run python scripts/observability/retention_probe.py start \
  --root /raíz/privada/test --project ecs007-ensayo \
  --image ecs007-host-tools:local --url https://localhost:3446 \
  --password-file /raíz/privada/test/probe-password
uv run python scripts/observability/retention_probe.py run --root /raíz/privada/test
uv run python scripts/observability/retention_probe.py status --root /raíz/privada/test
```

`start` comprueba mounts antes de reiniciar únicamente Loki/Jaeger del ensayo; emite
10operaciones técnicas y verifica tres señales antes/después. El archivo
retention-probe.json guarda cortes, archivos/asignación física y referencias, nunca
contraseñas. `run` usa UTC real/CLOCK_BOOTTIME, espera en intervalos<=60s y puede
reiniciarse. No ejecutar simultáneamente fallos/cuotas, alterar reloj, recrear datos
ni desmontar recursos del ensayo. Mantener el emisor técnico para heartbeat/TTL de
spool y snapshot de cuotas; sin snapshot fresco ingesta se cierra507.

`expired_query_confirmed_physical_review_pending` no acepta GC. Los dos casos
real_time de test_retention_sampling.py revisan expiración consultable y retirada de
archivos físicos originales por separado; Badger puede necesitar evidencia adicional.
Ningún script marca tareas/checklists. [Límites y continuación](../../specs/007-observabilidad-externa/validation/retention.md).
