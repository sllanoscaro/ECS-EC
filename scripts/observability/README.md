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
