# US1: acceso local parcialmente validado

Fecha local2026-11-02. Emisor básico y MVP técnico ejecutados; SC-001/007 integral
**pendiente**. No se marcaron checklists de revisión ni se crearon permisos006.

## Recursos y comandos reales

Proyectos exclusivos `ecs007-validation` (test,3444,172.30.77.0/24) y
`ecs007-other-validation` (local,3445,172.30.78.0/24). Raíces privadas fuera del repo,
CA independientes, UID propietario, datos/posiciones separados y rangos dinámicos
`.128/25`; gateway `.2` fuera del pool. Imagen de aplicación construida localmente
`ecs007-validation-app:local`, sin reemplazar imágenes/proyectos previos.
Dependencias/digests: [registro](dependencies.md), `deploy/observability/versions.env`.

```sh
uv sync --locked
uv run pytest backend/tests/unit/observability backend/tests/contract/observability/test_log_event.py -q
#Con stack007 preparado y CA confiable; PostgreSQL *_test separado para las pruebas006:
OBS_TEST_ROOT=/ruta/externa/test OBS_TEST_OTHER_ROOT=/ruta/externa/local \
  uv run pytest backend/tests/contract/observability backend/tests/integration/observability -q
```

`test_browser.py` requiere imagen local indicada, Chromium/Playwright y trust store
NSS en un HOME exclusivo (`OBS_BROWSER_HOME`). Se descargó/extrajo `libnss3-tools`
en `/tmp` y se importó la CA con `certutil -A -t C,,`; no se cambió el trust store del
usuario ni se deshabilitó validación TLS. `NODE_EXTRA_CA_CERTS` verifica requests Node.
Fixtures/bases son explícitas y privadas; no existe endpoint público de provisión,
semillas, reloj o inyección. El harness lanza el monolito real con export compilado y
sesiones006, y lo cierra después. Falta de proveedor produce skip explícito, no aceptación.

## Resultados verificados

| Caso | Resultado |
| --- | --- |
| CA/TLS/bcrypt real | Cliente con CA confiable y sujeto provisionado consulta; bcrypt5.0.0/$2b$/coste12 interoperó con crypt de Nginx fijado. |
| Provisión por TTY | PTY real pide contraseña/confirmación sin echo; stdout solo revisión/resultado. Argumentos/stdin no conceden alta. Revocación/regrant/rename/fsync probados. |
| Rol/headers/cookies públicos | Sin Basic válido:401; headers autodeclarados y cookies previas no conceden identidad. Host extraño403. |
| Revocación | Misma conexión/cliente falla en la siguiente solicitud sin reload. Navegador y enlaces posteriores también deniegan. Archivo ausente falla cerrado, se restaura explícitamente. |
| Dos entornos | Basic de test no autoriza local; credencial local explícita consulta su propio stack. CA, redes y directorios distintos. |
| Procesos | App solo POST/v1/traces; Alloy entrega logs reales; salud solo GET/collector-health filtrado. Certificados app/Alloy/salud no consultan como humanos; Basic no satisface mTLS. |
| Fuentes directas | Puertos host ausentes; HTTP a IPs privadas desde host falla con fuentes en ejecución. Bridges internos inhiben IPv4; solo listener8443 publica loopback. |
| Rutas/métodos | Denegadas administración, Live/tail/streams, ingesta humana, proxy genérico, traversal/encodings, slashes ambiguos y datasource ajeno. POST solo ds/query local. |
| Límites | >64KiB y >10000 rechazados. SearchDepthv3 probado sobre Jaeger2.22; parámetros de paginación posteriores se deniegan. Cuatro consultas suspendidas acaban504 al deadline30s; quinta429. Prueba real39.76s incluyendo DNS/arranque/cleanup. |
|006 real/API | Administrador conserva historial; Operador lo tiene denegado; ambos carecen de acceso técnico con sus cookies. Basic técnico no crea sesión/permisos funcionales. |
| Browser real | Dashboard Viewer con logs/métrica observada, traza Jaeger por referencia, administración denegada; navegación funcional sin visor técnico, historial admin permitido/operator oculto y revocación UI. |

Fixture exclusivamente técnica con emisor real:10 operaciones sintéticas,8 success y
2 unexpected_error; Loki devolvió33 eventos y10 terminales del tipo consultado;
Jaeger devolvió traza concreta,20 spans confirmados,0 descartes/errores de exportación.
Salud independiente informó disponibles ambos transportes con fechas no null.
Esto acredita transporte/acceso y **no** diez consultas funcionales001 ni SC-002/003.
El script reproducible es `scripts/observability/emit_reference.py`.

## Fallos encontrados y corregidos

- CA sin keyUsage no superaba validación estricta de Python3.14: se generó CA explícita
  de firma y validación estricta; raíces antiguas no se sobrescriben.
- IP fija colisionaba con asignación dinámica: pool separado y redes recreadas solo en test.
- Njs no admite for-of en la imagen fijada: bucles compatibles, `nginx -t` ejecutado.
- Nginx necesitaba tempdirs explícitos en raíz read-only; se movieron a tmpfs acotado.
- Redes solo internas no publicaban listener; se añadió red de entrada exclusiva al gateway.
- Red privada con IPv4 host permitía acceso a IP interna: se inhibió la IPv4 del bridge,
  se verificó backend vivo por loopback interno y fallo de conexión desde host.
- `disable_login=true` retiraba resolvedor necesario para AuthProxy de Grafana13;
  se mantuvo resolvedor con Basic/formulario/login/rutas alternativas deshabilitados.
- Lecturas versionadas de Grafana13 se concretaron con navegador. POST de métricas,
  feature flags e historial/preferencias queda denegado; no se abrió una API genérica.
- Alta con tty en modo r+ fallaba por falta de seek; stream de salida w y PTY real
  comprobaron el flujo. Secretos nunca se introdujeron en argv/stdout.
- Jaeger devuelve404/`No traces found` para ventana vacía; prueba distingue esa respuesta
  de rechazo del gateway y mantiene comprobación de traza concreta persistida.

## Pendientes obligatorios

- T022/SC-001: no hay generador/API PDF005 real; sus permisos no se acreditan con404
  de una ruta inexistente. El test lo omite expresamente.
- T028/T029: Compose/configuración/procedimientos están preparados y ejecutados en test,
  pero se mantienen tareas pendientes por la cadena de prerrequisitosT022.
- T030 permanece pendiente: suites disponibles pasaron, matriz completa todavía no.
- US2–US4: recepción/adaptador003, generación005 e instrumentación propia001–006;
  terminales especiales/correlación completa, catálogo/paneles de cobertura, cuotas reales,
  privacidad/aislamiento funcional integral, TTL24h/GC y personas siguen pendientes.
- No aceptación de VPS ni SC-008. Ninguna fixture o documento sustituye esos resultados.

[Estado de tareas](../tasks.md), [prerrequisitos](prerequisites.md),
[emisor](emitter.md). Los resultados de regresión final se conservan en
[validación parcial](acceptance.md), sin cerrar T065.
