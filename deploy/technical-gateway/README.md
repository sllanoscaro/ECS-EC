# Frontera técnica007

Nginx1.31.8/njs sirve solo el listener humano TLS8443 y tres listeners internos
mTLS8444/8445/8446. Basic por solicitud lee `credentials/authorized` sin caché;
montar el directorio, nunca el inode de un archivo. Una revocación por rename
aplica a la siguiente solicitud, incluso keep-alive/cookies. Error de archivo
deniega; no hay fallback a006/Grafana, tail, Live, SSE o proxy a URL arbitraria.

Preparación desde raíz (requiere Docker26+ Linux/Compose, uv/Python y OpenSSL):

```sh
uv sync --locked
bash scripts/observability/prepare_local.sh --environment local
export OBS_RESOURCE_ROOT="$HOME/.local/state/ecs-ec/observability/local"
export OBS_UID="$(id -u)"
export OBS_ENVIRONMENT=local OBS_PORT=3443
bash scripts/observability/manage_programmer.sh grant --environment local --subject prog-local-01
docker compose --profile observability config --quiet
docker compose --profile observability up -d technical-gateway
```

La contraseña se pide por `/dev/tty`; no ponerla en argumentos/env/stdout.
El script usa bcrypt5.0.0/coste12, probado con crypt() de Nginx fijado. Los sujetos
`prog-[a-z0-9-]` son opacos; la relación con personas es operativa y externa.
Registro privado por entorno con estado/revisión; reactivar exige otro `grant`
explícito. No lee ni escribe cuentas006. Revocar:

```sh
bash scripts/observability/manage_programmer.sh revoke --environment local --subject prog-local-01
```

Operador del host prepara recursos y puede desplegar. Programador solo conoce
su Basic, CA pública y URL; no recibe acceso al host, Docker, directorios de claves
o credenciales administrativas. Importar la CA pública en el cliente. Nunca usar
`-k`/ignoreHTTPSErrors. Pruebas de navegador usan NSS/CA en HOME exclusivo.

Separación: un proyecto/red/CA/directorio por entorno. Solo gateway tiene red de
entrada con puerto publicado en loopback. Las redes internas deshabilitan también
la asignación IPv4 del bridge (`inhibit_ipv4=true`): sin ello un navegador en el host
podría llegar a la IP privada de una fuente aunque no publique puertos. No añadir
rutas host ni conectar esas fuentes a la red de entrada. Estas opciones se comprobaron
en Docker26.1.5; verificar aislamiento de nuevo al cambiar motor/red/despliegue.
La IPv4 del gateway debe quedar fuera del rango dinámico y coincidir con la whitelist
AuthProxy de Grafana. Las identidades de ingesta no tienen permisos humanos; CA, hoja
y clave se montan por proceso, sin clave CA ni claves de otros procesos.

`gateway.js` fija destinos y rutas. Métodos GET/HEAD de recursos/consultas enumerados;
POST solo `/grafana/api/ds/query`, datasource local `ecs-loki`,64KiB/4 queries,
ventana<=24h, filas/series solicitadas<=10000. Cuatro consultas concurrentes por sujeto,
deadline total30s más timeout de fuente. Loki rechaza limit>10000; Jaeger v3 usa
`query.searchDepth`, no el parámetro legacy `limit`; no reenviar parámetros desconocidos.
El backend de trazas Jaeger2.22.0/FindTraces no admite
paginación de IDL posterior. Los archivos estáticos son de las imágenes fijadas;
los metadatos GET de Grafana13 se enumeran sin habilitar APIs de escritura.
`ofrep`, métricas frontend, cambios de preferencias e historial UI por POST permanecen
fuera de la allowlist; el dashboard de lectura funciona sin ellos.

AuthProxy necesita el resolvedor local de usuarios (`disable_login=false`) en Grafana13;
Basic, formulario, anonymous, cookies de login y rutas públicas de login siguen
deshabilitados. Identidad/rol se sobrescriben como sujeto opaco/Viewer. Cookies,
Authorization, cabeceras de proxy/tenant/identidad y cabeceras arbitrarias del cliente
no se reenvían a fuentes. Access/error logs de gateway desactivados; Docker no conserva
stdout de herramientas. Njs inspecciona también URI original para rechazar ambigüedades.

Ante actualización interrumpida del registro/authorized, el siguiente cambio del script
falla al detectar discrepancia. Operador revoca acceso retirando `authorized`, repara el
registro privado y vuelve a provisionar explícitamente; jamás permitir cookies como
recuperación. La falta de archivo puede responder500, pero nunca entrega señales.
Rotar TLS a una raíz nueva; el script rechaza material existente inválido/expirado y
no lo sobrescribe. Hojas30d/CA365d. La VPS requiere CA/certificados de hostname reales,
reemplazar la allowlist Host `localhost`, URL pública, binding y verificar firewall/red,
cuotas y restauración técnica. La validación local no acredita esa instalación.

[Operación del stack](../observability/README.md),
[scripts](../../scripts/observability/README.md),
[contrato de acceso](../../specs/007-observabilidad-externa/contracts/technical-access.md).
