# 001:T056 — integración local003/007/008,2026-11-25

**Verificada. FR-019 ySC-006 cuentan con evidencia consumidora real.** Se ejecutaron
dos recorridos completos,CSV yJSON, sobre la aplicación actual. La regresión propia
de consumo terminó con **209 aprobadas,0 fallos,0 errores y0 omisiones en118,83s**;
incluye ambos recorridos y sus dos escenarios Playwright. No se suman como pruebas
independientes las repeticiones previas. [JUnit](artifacts/local-integrations-regression.xml)
y [resumen saneado](artifacts/local-integrations-results.json).

001 queda58/61 tareas completas; T059/personas,T060/VPS yT061/aceptación integral
permanecen pendientes. Esta prueba no cierra tareas de otros propietarios.

## Recorrido y resultados conocidos

| Frontera | Resultado observado en ambos formatos |
| --- | --- |
| Generador/publicador003 independiente | El CLI instalado genera un ciclo con acumulados100→104→108 de CAT-03; dos intervalos conocidos de4kWh, sin importar el parser del backend. |
| SFTP003 real | TCP loopback,clave privada y known_hosts verificados; archivos nativos,CLOSE yEOF limpios. Publicación,entrada e intento quedan durables antes de002. |
| Recepción002 | Dos registros aceptados,una actualización de categoría,ningún rechazo. Recuperar el intento completado no vuelve a incorporar datos. |
| Consulta001/identidad006 | Operador autenticado recibe exactamente4+4=8kWh,con fuente/procedencia y períodos conservados. API,no-store,gráfico y tabla coinciden. CAT-01 física sin lecturas yCAT-05 sin lecturas conservan `no_data`,sin total sustituto ni cero inventado. |
| Zona/permisos | Entrada local21:00–21:30 del31diciembre2025,Santiago,corresponde a00:00–00:30Z del1enero2026. Offset incongruente devuelve422; configuración administrativa al Operador403; lectura sin sesión401. Navegador en Asia/Tokyo conserva las etiquetas de Santiago. |
| Configuración008 | Crear,previsualizar yactivar por HTTP real006/008 dos reglas dirigidas a una cuenta registrada: resumen de recepción/calidad y alerta CAT-03>3kWh por intervalo900s. No se insertan entregas o mensajes desde el test. |
| Captura008 | El resumen contiene una recepción de categoría y cero rechazos conocidos con cobertura completa. La alerta usa el último intervalo cerrado de4kWh y referencia exactamente su registro002; no confunde ese intervalo con el total8kWh. |
| SMTP/Mailpit reales | Dos mensajes aceptados por formato,cuatro en los dos recorridos. Un To/sobre por entrega,sinCC/BCC; captura,entrega e intento quedan aceptados. Se comprueban cuerpos y enlaces al entorno autenticado. |
| Navegador real | Consulta los datos recibidos por SFTP y abre ambos enlaces de correo. Gráfico/tabla a1440/390px,sin desbordamiento horizontal. Sin sesión se oculta el artículo,se ofrece ingreso y la API rechaza el acceso; no hay respuestas interceptadas. |
| Logs/métrica/trazas007 | Alloy→Loki conserva todas las señales admitidas de cada cohorte; LogQL devuelve una recepción lógica en esa cohorte sin replay. OTLP→Jaeger conserva trazas correlacionadas. Grafana devuelve ambos dashboards por el gateway autorizado. |
| Separación técnica | Programador por Basic no obtiene acceso a consumo; una cookie funcional no concede acceso técnico. Consultas técnicas con CA yTLS verificados; ingesta con certificado de aplicación. Señales sin correos,nombre/bytes de archivos ni identificador nativo PAS600. |

Los registros JSON de [CSV](artifacts/local-integrations-csv.json) y
[JSON](artifacts/local-integrations-json.json) vinculan publicación/intento funcional,
registros002,entregas008 y referencias técnicas opacas. Estas últimas se contrastan con
el contexto técnico persistido: no se supone que `attempt_ref` sea el ID funcional.
En la regresión final se observaron537 eventos admitidos/persistidos enCSV y502 enJSON;
son señales de las operaciones del recorrido,no cantidades de lecturas ni correos.

Capturas inspeccionadas: [CSV escritorio](artifacts/local-integrations-csv-1440.png) y
[JSON móvil](artifacts/local-integrations-json-390.png). Todos los datos y las cuentas
son sintéticos; las cuentas no representan participantes de evaluación humana.

## Entorno exclusivo y reproducción

Proyecto Compose `ecs001-step6`,PostgreSQL18.3 enloopback55566,base
`ecs001_step6_test`,distinta de la aplicación; MailpitSMTP11026/interfaz18026;
gatewayTLS3449,subred técnica172.30.89.0/24. TLS/credenciales/datos técnicos en
`~/.local/state/ecs-step6-local-integrations/test`,fuera del repositorio. No se usaron
SQLite,servicios remotos ni la base/los contenedores funcionales del usuario.

Se reutilizaron `compose.yaml`,las imágenes/digests fijados de003/007/008,el generador
independiente y los servicios reales de cada propietario. El monolito Uvicorn sirve
la exportación estática actual desde un puerto loopback efímero. El proceso Docker
temporal del arnés007 solo transporta spans codificados con el exportador real;
no produce eventos funcionales ni reemplaza una operación de negocio.

Desde la raíz,instalar con locks y preparar una exportación de frontend:

```sh
uv sync --locked --group dev
uv sync --directory tools/pas600_simulator --locked --no-dev
npm --prefix frontend ci
npm --prefix frontend run build
```

La ejecución observada reutilizó la instalación bloqueada del CLI003 y la exportación
real ya construida en el paso5; ejecutó de nuevo `uv sync --locked --group dev` y
`npm --prefix frontend run typecheck`. Los comandos anteriores permiten preparar
esos mismos prerrequisitos desde una instalación nueva,sin afirmar otra construcción
realizada en este corte.

Preparar TLS y el sujeto sintético de pruebas mediante los scripts oficiales007:

```sh
bash scripts/observability/prepare_local.sh --environment test --root /ruta/privada/ecs001-step6
uv run --locked python scripts/observability/manage_programmer.py grant --environment test --subject prog-test-01 --root /ruta/privada/ecs001-step6
```

La provisión CLI lee la contraseña porTTY; el fixture de consultas usa exclusivamente
la contraseña sintética `Synthetic technical password 007`. Nunca usar ese sujeto o
valor en producción. La ejecución automatizada aprovisionó el mismo registro mediante
su helper interno007,sin contraseña en argumentos ni salida.

Establecer configuración test explícita en un archivo privado0600 o entorno del
proceso,sin volcar secretos. Los valores usados fueron:

| Variable | Valor / condición |
| --- | --- |
| `DATABASE_URL` / `TEST_DATABASE_URL` | PostgreSQL exclusivo; nombres distintos,el de pruebas termina en`_test`. Las fixtures comprueban destino antes de migrar/limpiar. |
| `POSTGRES_USER`,`POSTGRES_PASSWORD`,`POSTGRES_DB`,`DB_PORT` | Credenciales sintéticas propias,base test y55566. No usar valores de la instalación funcional. |
| `ENVIRONMENT`,`OBS_ENVIRONMENT` | `test` |
| `OBS_ENABLED`,`NOTIFICATION_ENABLED`,`PAS600_SFTP_ENABLED` | `false` en el proceso pytest: el arnés compone sus listeners y llama los servicios internos reales sin arrancar trabajos duplicados. |
| `OBS_RESOURCE_ROOT`,`OBS_TEST_ROOT` | La raíz privada preparada,terminada en`/test`. |
| `OBS_TEST_PROJECT`,`OBS_TEST_URL`,`OBS_PORT` | `ecs001-step6`,`https://localhost:3449`,`3449`. |
| `OBS_UID` | UID del propietario que prepara recursos. |
| `OBS_STORE_SUBNET`,`OBS_STORE_DYNAMIC_RANGE`,`OBS_GATEWAY_IP` | `172.30.89.0/24`,`172.30.89.128/25`,`172.30.89.2`. |
| `OBS_PUBLIC_URL` | `https://localhost:3449/grafana/` |
| `OBS_REQUIRE_QUOTAS`,`OBS_RETENTION`,`OBS_RETENTION_HOURS` | `false`,`24h`,`24`,solo en este test. No acredita cuotas físicas ni vencimiento. |
| `OBS_TEST_IMAGE` | Imagen local ya descargada con el exportador007 real; se usó`ecs007-validation-app:local`. No se desplegó esa imagen como aplicación funcional. |
| `MAILPIT_SMTP_PORT`,`MAILPIT_UI_PORT` | `11026`,`18026`. |
| `CONSUMPTION_LOCAL_INTEGRATIONS` | `1`; sin esta selección explícita los dos casos se omiten. |
| `CONSUMPTION_LOCAL_SMTP_PORT`,`CONSUMPTION_LOCAL_MAILPIT_URL` | `11026`,`http://127.0.0.1:18026`. |
| `CONSUMPTION_LOCAL_BROWSER_WEB` | Ruta absoluta a`frontend/out`,exportación real construida. |
| `CONSUMPTION_LOCAL_ARTIFACTS` | Directorio privado para resultados y capturas. |

Con ese entorno cargado,levantar solo los recursos exclusivos y ejecutar:

```sh
docker compose --project-name ecs001-step6 --profile mail --profile observability config --quiet
docker compose --project-name ecs001-step6 --profile mail --profile observability up -d db mailpit technical-gateway
.venv/bin/pytest backend/tests/integration/consumption/test_local_integrations.py -q
.venv/bin/pytest backend/tests/unit/consumption backend/tests/contract/consumption backend/tests/integration/consumption -q --junitxml=/ruta/privada/consumption-regression.xml
npm --prefix frontend run typecheck
```

El test backend arranca el listenerSFTP y el monolito HTTP efímeros,crea cuentas
sintéticas y ejecuta `frontend/tests/e2e/consumption-local-integrations.spec.ts` con
Node24.21/`--jitless`,un worker yChromium. No ejecutar ese E2E sin su arnés/expectativas
privadas. No existen rutas públicas para sembrar datos,cambiar tiempo o provocar fallos.
Un directorio de capturas existente no se usa como resultado de una ejecución nueva.

Si no se dispone de una imagen local para el transporte privado de spans,construir
un tag exclusivo con `docker build -t ecs001-step6-transport:local .` yseleccionarlo en
`OBS_TEST_IMAGE`. Esto permite reproducir desde cero sin sustituir la imagen o los
contenedores de la aplicación del usuario. No fue necesaria otra construcción en
la ejecución registrada.

## Límites conservados

El reloj de negocio yDate del navegador se controlan privadamente para cerrar ventanas
históricas y conservar el mismo reloj de sesión006. Temporizadores y transportes de red
son reales; no se adelantó el reloj del host ni se midió cadencia900s o SLO de despacho.
El resumen/despacho se ejercita mediante sus servicios internos reales,no se acredita
aquí otra validación de autonomía del supervisor008.

Mailpit acredita aceptación local,no relay de producción,buzón o lectura. No se certifican
DOCA0172EN-19,firmware o medidores físicos. La historia íntegra de esta fixture no
demuestra cobertura real de una instalación. LogQL se contrasta en una cohorte sin
replay; los límites de pérdida/duplicación de007 permanecen vigentes.

El ensayo `ecs007-step4-quotas`,sus mounts,trabajador,plazos y contenedores se conservaron.
No se ejecutaron saturación,caídas,reinicios ni verificación de TTL/GC sobre ese proyecto.
007:T059 y las tareas humanas/VPS de001 siguen pendientes. Las checklists y la selección
persistida003 se conservan; no hay commit ni despliegue de producción implícito.

## Cierre de recursos

Tras guardar evidencia se verificó la etiqueta de proyecto de los siete contenedores
propios yse retiraron únicamente `ecs001-step6`,sus redes ysu volumen PostgreSQL
desechable. Se conservaron los artefactos saneados enlazados yel directorio técnico
privado para inspección. Repetir exige preparar recursos test nuevos según esta guía.
Los tres contenedores originales yel trabajador/stack de retención007 siguen activos;
sus plazos originales no cambiaron.
