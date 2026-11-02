# Quickstart de validación: observabilidad externa

[Plan](plan.md), [modelo](data-model.md), [señales](contracts/signals.md),
[emisión](contracts/integrations.md), [acceso/políticas](contracts/technical-access.md).
Guía de la implementación prevista. Hoy hay diseño; aplicación, comandos auxiliares,
pruebas y despliegue técnico aún deben implementarse. Ningún escenario se declara ejecutado.

## Prerrequisitos y arranque

Plataforma009 real: herramientas/lockfiles, reloj, lifecycle, PostgreSQL18, UoW y auditoría.
Para SC-002 completo también productores001–006 reales e instrumentados conforme a
[matriz del plan](plan.md#prerrequisitos-por-capacidad-y-propietario). Sin SMTP/008.
Fixtures sintéticas internas, DB y volúmenes exclusivos de prueba; no crear endpoints
públicos para inyectar datos, adelantar relojes o provocar fallos.

CPython3.14, uv, Docker Compose; Node/npm/Playwright solo para checks de navegador.
Fijar imágenes/digests y dependencias al implementar. Los nombres previstos de servicios
son `app`, `db`, `technical-gateway`, `alloy`, `loki`, `grafana`, `jaeger`.

Comandos previstos desde raíz, después de implementar y regenerar tareas:

```sh
uv sync --locked
npm --prefix frontend ci
docker compose up -d db
uv run alembic -c backend/alembic.ini upgrade head
bash scripts/observability/prepare_local.sh --environment local
bash scripts/observability/manage_programmer.sh grant --environment local --subject prog-test-01
docker compose --profile observability config --quiet
docker compose --profile observability up -d
uv run pytest backend/tests/unit/observability backend/tests/contract/observability
uv run pytest backend/tests/integration/observability backend/tests/integration/test_observability_isolation.py
npm --prefix frontend exec playwright test tests/e2e/observability-isolation.spec.ts
```

`prepare_local.sh` prepara CA/TLS/mTLS, directorios privados y configuración técnica local,
sin secretos en Git. `.env`/mounts externos resuelven rutas. La CA se instala/importa en el
cliente de prueba. El script de provisión pide contraseña por TTY. No pasarla como argumento.
No usar `-k`, autorregistro, puerto de fuentes publicado o bypass para simplificar pruebas.

## 1. Acceso y revocación — US1, SC-001/009

Abrir `https://localhost:3443/grafana/` como Programador. Consultar dashboard, logs y
Jaeger con Basic. Para consulta directa, `curl --user prog-test-01` solicita contraseña:

```sh
curl --cacert "$OBS_LOCAL_CA_FILE" --user prog-test-01 --get   'https://localhost:3443/logs/loki/api/v1/query_range'   --data-urlencode 'query={service_name="ecs-ec",environment="local"}'   --data-urlencode 'limit=100'
```

`OBS_LOCAL_CA_FILE` apunta al certificado público generado en el directorio externo.
Una consulta manual sin start/end usa el rango predeterminado acotado de la herramienta;
la prueba automatizada siempre fija ambos límites y corte para comparar resultados.

| Identidad/caso | Resultado esperado |
| --- | --- |
| Programador autorizado en local | Lectura de tres señales de local; sin edición/administración |
| Operador/Administrador006 solo con cookie/credenciales funcionales | 401/403 sin señal, incluidos URL directa de fuente/proxy/Jaeger |
| Sin identidad, rol autodeclarado, `X-WEBAUTH-USER`/Host/tenant falsificado | Denegación, sin telemetría |
| Certificado/credenciales de proceso de ingesta | Solo rutas automáticas autorizadas, sin consulta humana |
| Programador contra API funcional de consumo/PDF/usuarios/historial | Sin permisos; con productores006 reales, 401/403 |
| Administrador006 crea/cambia cuenta o envía perfil Programador | No concede acceso externo; contrato006 rechaza perfil ajeno |
| Programador solo local contra segundo stack de test en 3444 | Denegación; cambiar filtro/URL/datasource no supera frontera |

Revocar en otra terminal:

```sh
bash scripts/observability/manage_programmer.sh revoke --environment local --subject prog-test-01
```

La siguiente consulta, recurso UI o descarga técnica se deniega, también sobre keep-alive
y con cookies previas. No usar una recarga de Nginx como requisito para refrescar archivo.
Comprobar que puertos host 3000, 3100, 4317, 4318, 12345, 16685 y 16686 no entregan
señales. Verificar navegación funcional sin visor; historial006 sigue permitido al admin.

## 2. Correlación y cobertura — US2, SC-002/004

Ejecutar una operación correcta, un rechazo previsto y un fallo controlado de cada fila
del catálogo con sus productores reales. Guardar referencias sintéticas de operación y
trazas en evidencia. Para recepción usar publicación nativa válida003, validación001,
incorporación y agregado002; para costos004/PDF005 usar resultados reales, no stubs.

Consultar por período/entorno/operación, pasar del panel agregado al log y a la etapa
Jaeger. Comprobar UTC, versión, resultado, código, duración y referencias iguales. Los
rechazos inválido/duplicado/anticipado y permisos no son errores inesperados. Fallo de
cálculo/PDF identifica etapa sin detalle interno en respuesta funcional.

Forzar continuación posterior al request y recuperación tras reinicio: conservar relación
lógica, distinguir ejecuciones y no inventar span continuo. Reenviar publicación completa
con mismo contenido: misma publicación, otro intento. Recuperar el mismo attempt_id no
suma un terminal nuevo. Dos bindings/operaciones con texto/nombre idéntico no se mezclan.
CSV/JSON, credenciales y PDF mantienen su contrato. Contexto no disponible aparece explícito.

## 3. Carga y métricas — US3, SC-003

Pruebas de integración con ventana UTC conocida y cobertura cerrada:

| Fixture | Resultado esperado |
| --- | --- |
| 10 consultas `consumption.query_detail`, 8 correctas y 2 fallos internos | 10 terminadas, 8 success, 2 unexpected_error, 20 %; sin sumar etapas/autorizaciones |
| 5 registros: 3 aceptados, 1 inválido, 1 duplicado en una recepción | Una operación `reception.accept`, 5 posiciones, 3 novedades/1 inválido/1 duplicado |
| Reenvío equivalente y recuperación del intento | Nuevo intento distingue duplicados, sin nuevas aceptaciones; recuperación no duplica resumen |
| Un intento incorpora3 registros, falla con2 pendientes y se recupera incorporándolos | Dos ejecuciones (un fallo/un éxito), un intento lógico completado,5 aceptados una vez; error por ejecución50% y por intento completado0% |
| Duraciones conocidas 100/200/300 ms mediante reloj controlado | Media 200 ms, distribución coherente y no negativa; no son intervalos energéticos |
| Denominador cero con cobertura completa | Operaciones 0 observado, error N/D; no porcentaje inventado |
| Recolector parado o heartbeat ausente >45 s | Cobertura desconocida con último dato; no actividad/error cero |
| Eventos exactamente en inicio/fin de ventanas adyacentes | Cada evento aparece en una sola ventana conforme a `[inicio,fin)` |
| 1000 operaciones con UUID/nombres distintos y mismos tipos/resultados | Sin series nuevas por IDs/archivo/persona; solo dimensiones del catálogo |

Comparar consultas LogQL con resultados conocidos al mismo corte; no verificar una métrica
usando exclusivamente otra métrica derivada del mismo log. Repetir envío/relectura de un
evento serializado y reiniciar Alloy conservando posiciones: sin inflación de conteos.
Perder posiciones/forzar replay ambiguo debe limitar cobertura, nunca aparentar exactitud.

En el caso de fallo parcial, verificar que `processing|partial_failure` no emiten
`reception.completed`. La ejecución fallida emite `execution.completed` con
`unexpected_error`, código seguro, su `execution_ref` y `counts=null`. Al recuperar,
conservar `attempt_ref`, cambiar `execution_ref` y emitir un solo resumen lógico con
los cinco resultados originales completos. Releer el resultado terminado sin procesar
trabajo no incrementa intentos, ejecuciones ni registros. Los porcentajes de error se
consultan con denominadores separados de operaciones lógicas y ejecuciones.

Comprobar heartbeat con los seis campos de salud por señal del [modelo](data-model.md):
estados de recolección de logs y exportación de trazas, sus últimos éxitos UTC nullable,
lotes de exportación fallidos y spans confirmados acumulados por arranque. Un reintento
interno no multiplica estos contadores. Un estado `available` exige éxito observado;
sin evidencia usar `unknown`, sin deducir caída únicamente de que no haya nuevos envíos.

## 4. Privacidad y aislamiento — US4, SC-005/006

Introducir marcadores sintéticos únicos en contraseña, cookie, token, clave SFTP, correo,
IP, nombre libre con saltos/control, contenido CSV/boleta/PDF y valor individual energético/
financiero. Examinar logs locales ya escritos, colas observables de prueba, Loki, Jaeger
y logs de herramientas/gateway: cero coincidencias de los marcadores. El texto no puede
alterar severidad, estructura, rol o correlación. Repetir con excepción que incluya el
marcador; no exportar mensaje/stack crudo. Respuestas funcionales permanecen saneadas.

Detener receptores sin detener aplicación:

```sh
docker compose --profile observability stop alloy loki jaeger
uv run pytest backend/tests/integration/test_observability_isolation.py
docker compose --profile observability start alloy loki jaeger
```

Comparar contra ejecución normal: consultas, mediciones incorporadas, cálculos y PDF
conservan resultados/commits reales y evidencia009. Saturar colas/spool y cuotas con límites
de prueba reducidos, simular timeout/red caída y shutdown: no sobrepasar capacidades,
no esperar red/disco en operación funcional, pérdidas contabilizadas. Medir RAM real y
payload por separado. Ventanas afectadas siguen limitadas tras recuperar transporte.

Repetir además los fallos por separado, restaurando cada componente entre casos:

```sh
docker compose --profile observability stop jaeger
uv run pytest backend/tests/integration/observability/test_collection_continuity.py -k jaeger_only
docker compose --profile observability start jaeger
docker compose --profile observability stop alloy loki
uv run pytest backend/tests/integration/observability/test_collection_continuity.py -k logs_only
docker compose --profile observability start alloy loki
```

Los casos deben existir con esos nombres al implementar T045. Con Jaeger/OTLP caído,
logs/métricas de logs conservan su cobertura propia mientras trazas muestran su
limitación. Con Alloy/Loki caído, las trazas consultables mantienen su evidencia y
logs/métricas declaran el vacío. Tras recuperar, los huecos históricos siguen visibles.
Consultar Jaeger como Programador, sin permisos humanos para credenciales de ingesta;
una exportación confirmada no prueba persistencia consultable. El heartbeat de45s no
obliga a exportar lotes cuando no hay actividad ni rellena señales ausentes.

## 5. Políticas y persistencia — US4, SC-007

Reiniciar Jaeger/Loki/Alloy con volúmenes conservados: señales no vencidas y posiciones
siguen disponibles. Usar perfil desechable 24 h; no acortar ni borrar volúmenes reales.
Comprobar visibilidad antes del vencimiento y retiro mediante compactor/GC hasta 60 min
tras TTL; observar almacenamiento y consulta por separado. Puede ser prueba programada
prolongada, no requisito de terminar en una sesión interactiva.

Revisar que registros funcionales protegidos de 12 meses no cambiaron y que el historial
administrativo mantiene permisos/finalidad. Activar muestreo0.1 solo para caso dedicado:
se informa política/limitación de trazas, logs terminales siguen íntegros y no se declara
que una referencia ausente nunca existió. Restaurar ratio1.0 para cobertura completa.

## 6. Diagnóstico con personas y aceptación local — SC-008/009

Preparar diez tareas con Programadores representativos: localizar operación, reconocer
resultado/etapa y límites de disponibilidad sin ayuda. Registrar éxito/obstáculos por
tarea con sujetos opacos; al menos nueve deben completarse. Sin personas/resultados,
SC-008 permanece pendiente; E2E no lo acredita.

Después de T060, la documentación T062/T063 y los escenarios técnicos de quickstart
T064 pueden completarse mientras T061 espera participantes. Registrar SC-008 pendiente
en esa evidencia parcial, sin contar como ejecutadas las tareas de diagnóstico humano.
T065 requiere tanto T064 como T061 completadas antes del cierre de aceptación.

Con imágenes ya descargadas, ejecutar recorrido local bloqueando salida a servicios
remotos: tres señales consultables por Programador, perfiles funcionales denegados,
recolección sin sesión humana abierta. El modo funcional también arranca y opera sin
activar `observability`. VPS requiere comprobación posterior de TLS/red/secretos reales.

## Evidencia

Guardar comandos, versiones/digests, política, ventanas/cortes, fixtures, resultados,
conteos esperados/observados, pérdidas, capturas saneadas y evaluación con personas en
`specs/007-observabilidad-externa/validation/` cuando se ejecuten. No crear aprobaciones,
marcar checklists de revisión o afirmar validación por generar estos documentos.
