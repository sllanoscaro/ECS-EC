# Catálogo de señales y consultas

[Integración](integrations.md), [modelo](../data-model.md), [acceso](technical-access.md).
Catálogo v1. No contiene consumos ni importes individuales. Las métricas se derivan de
logs y comparten su cobertura, independientemente del muestreo de trazas.

## Dimensiones y filtros

Etiquetas Loki persistentes permitidas: `service_name="ecs-ec"`, `environment` (catálogo
de despliegues, inicial `local|test|vps`), `operation` (catálogo de integración), `outcome`
y `severity`. Quitar etiquetas automáticas `filename`, ruta, container ID y nombres
libres; tampoco indexar boot/event/trace/attempt/publication/user IDs. Etapas, versión,
revisión de política y referencias son campos JSON, consultables sin indexarlos.

Las agregaciones finales conservan solo entorno/operación/resultado y severidad donde
aplique. El parser JSON extrae únicamente campos necesarios; no usar `| json` sin
selección que convierta referencias en dimensiones intermedias de métricas. Categorías
CAT-01–CAT-07 podrían registrarse en una ampliación explícita; no hacen falta al catálogo inicial.

Consulta humana siempre acota entorno autorizado, UTC `[inicio,fin)` y corte. El dashboard
muestra zona UTC, unidad, función, resultado, política y cobertura. La ventana inicial es
15 min, elegible entre 1 min y 24 h; no consultar más allá de la retención sin aviso.
El gateway fija el entorno por despliegue: cambiar un selector no concede otro entorno.

## Medidas

| Nombre de presentación | Unidad / hecho | Cálculo y exclusiones |
| --- | --- | --- |
| `operations_total` | operaciones terminadas por tipo y resultado | Conteo del terminal registrado para ese tipo; excluye etapas, heartbeat, admisión y ejecución recuperada. No sumar una cadena de funciones como si fueran una sola recepción. |
| `attempt_executions_total` | ejecuciones por intento/resultado | `execution.completed`; recuperaciones separadas del intento lógico. Referencias solo como filtros diagnósticos. |
| `report_generations_admitted` | generaciones admitidas | `report.admitted` por nueva solicitud durable; replay HTTP, selección/permisos rechazados y descargas excluidos. |
| `unexpected_error_percent` | % de operaciones terminadas | `100 * unexpected_error / (success + expected_rejection + unexpected_error)` de misma operación/ventana; denominador 0 o desconocido → N/D. Rechazos no son errores inesperados. |
| `execution_unexpected_error_percent` | % de ejecuciones de procesamiento terminadas | Misma fórmula exclusivamente sobre `execution.completed`, con operación/ventana/filtros iguales; denominador 0 o desconocido → N/D. No mezclar sus eventos con terminales lógicos. |
| `processing_duration_ms` | milisegundos de ejecución técnica | Media y p50/p95 observados de duración terminal no negativa; null/interrupción excluidos con aviso. 005 mide desde claim conforme a su contrato; espera se muestra en etapa separada. |
| `reception_files_total` | archivos por evaluación003 | Suma de `files_seen`, `files_parsed`, `files_unreadable` del terminal `acquisition.process`, por categoría de resultado estática. No sumar resúmenes y logs por archivo a la vez. |
| `reception_records_total` | posiciones evaluadas por intento002 | Sumas de `records_seen`, `records_accepted`, `records_invalid`, `records_duplicate`, `records_other_rejected` en `reception.completed`. Un terminal del intento completo, no por fragmento/categoría. |
| `reception_new_records_total` | novedades confirmadas | `records_accepted`; reenvío equivalente solo aporta duplicados, recuperación no vuelve a aportar aceptados originales. No afirma un conteo de todos los registros únicos históricos. |
| `telemetry_dropped_total` | señales descartadas por causa/señal | Deltas de contadores acumulados en heartbeat, considerando resets/arranques; no sumar repetidamente snapshots acumulados. |
| `telemetry_queue_depth` | eventos/spans pendientes | Último heartbeat disponible, con edad y límite; no rellenar huecos con cero. |
| `collection_continuity` | estado por señal/ventana | `complete|partial|unknown`, último heartbeat, evidencia propia de recolección/exportación/consulta y motivos. Logs y trazas conservan evaluaciones independientes. |

`records_invalid` es subconjunto rechazado por validación; `records_other_rejected`
incluye `too_early`, conflictos/superposición u otros motivos de dominio no ya contados.
La clasificación exacta la resuelve el adaptador002, sin cambiar resultados funcionales.
Con resumen completo: `seen = accepted + invalid + duplicate + other_rejected`.
Si falla antes de conocerlo, dejar conteos no conocidos en null y declarar resumen parcial.
En archivos: `seen = parsed + unreadable` solo al completar la evaluación; no confundir
archivos transferidos con archivos parseados o registros aceptados.

Un reenvío explícito es otro intento: sus posiciones se cuentan como nuevamente evaluadas,
pero duplicados no incrementan novedades. Recuperar el mismo intento no duplica terminal,
archivos o aceptaciones. Las métricas de intento y las de novedades tienen nombres/unidades diferentes.

Un intento002 `processing`/`partial_failure` todavía no aporta `reception.completed`.
Su ejecución fallida aporta `execution.completed` con `counts=null`; el resumen completo
se emite solo al ganar la transición a `completed`, incluyendo aceptaciones previas a
la recuperación. No sumar conteos de etapas o ejecuciones al resumen lógico. Una lectura
sin procesamiento no incrementa ejecuciones. En el caso tres aceptaciones, fallo y dos
aceptaciones al recuperar: dos ejecuciones, un intento terminado y cinco novedades; el
error por ejecución es 50 % y por intento lógico terminado 0 %, si la cobertura es completa.

## Consultas LogQL de referencia

Ejemplos para cinco minutos; provisionar expresiones parametrizadas y comprobarlas sobre
la versión fijada. El panel de cobertura acompaña siempre a estos valores:

```logql
sum by (environment, operation, outcome) (
  count_over_time(
    {service_name="ecs-ec", environment="local", operation="consumption.query_detail"}
    | json event="event"
    | event="operation.completed"
    | __error__="" [5m]
  )
)
```

Para recepción, seleccionar su terminal y desenvolver el contador explícito:

```logql
sum by (environment, operation) (
  sum_over_time(
    {service_name="ecs-ec", environment="local", operation="reception.accept"}
    | json event="event", records_accepted="counts.records_accepted"
    | event="reception.completed"
    | unwrap records_accepted
    | __error__="" [5m]
  )
)
```

`quantile_over_time(0.95, ... | unwrap duration_ms | __error__="" [5m])` agrupa únicamente
por entorno/operación; no promediar percentiles de etapas para obtener duración total.
En versiones de Loki cuyo rango usa frontera `(inicio,fin]`, mapear el contrato de ventana
`[inicio,fin)` a los timestamps discretos de Loki desplazando ambos extremos un nanosegundo;
probar eventos exactamente en las dos fronteras, sin duplicarlos entre ventanas adyacentes.

Denominadores y numeradores comparten filtros/corte. Un vector ausente de errores puede
completarse con cero solo si hay denominador >0 y cobertura completa de esa ventana.
La división se evalúa únicamente con denominador conocido >0; nunca `clamp_min(...,1)`
ni cero global para ocultar ausencia. `absent_over_time` sobre heartbeat identifica
falta de señal, sin demostrar inactividad de negocio.

## Cobertura, duplicados y continuidad

Cada evento conserva timestamp/etiquetas/cuerpo inmutables al reintentarse. La
recolección usa posiciones persistentes; una relectura no regenera fecha ni event_id.
Validar deduplicación de Loki con entrega repetida y reinicio. Si se pierden posiciones,
se cambia serialización o no puede demostrarse deduplicación, la ventana es parcial o
desconocida y no se publican totales como exactos.

La evaluación de cobertura concilia secuencias y contadores entre heartbeats que
encuadran una ventana cerrada, eventos efectivamente recuperables y estado del recolector.
En el dashboard usar paneles de control y transformaciones sobre filas de log acotadas;
no convertir UUID/sequence en etiquetas de métricas. Límite de conciliación: 10000 eventos
por consulta; si se alcanza o falla la consulta, cobertura `unknown`, nunca completa.
Una ventana todavía abierta se presenta provisional. Para ventanas grandes, usar
subventanas conciliadas; un hueco no se oculta promediando estados.

El ciclo de salud del emisor puede consultar contadores de Alloy mediante ruta interna
autorizada de diagnóstico (solo métricas de transporte); filtra nombres permitidos antes
de emitirlos. No incorporar Prometheus como almacén, un servicio propio adicional ni un
prerrequisito funcional. Si falla esa comprobación, la cobertura de recolección queda desconocida.

Un contador de pérdidas acumulado que crece, huecos de secuencia, reset de arranque,
retención o fallos de entrega invalidan continuidad afectada. Reinicio nunca restaura
retroactivamente la cobertura. Heartbeat por sí solo no certifica integridad de trazas.

### Evidencia independiente de logs y trazas

El heartbeat separa `log_collector_status`/`last_log_collector_success` de
`trace_export_status`/`last_trace_export_success`; los contadores de spans exportados y
lotes fallidos complementan los descartes y la profundidad de cola. Son observaciones
de transporte con su fecha, no una prueba de persistencia o disponibilidad actual de
consulta. No reutilizar el éxito de Alloy como evidencia de éxito de Jaeger.

Evaluar trazas con la política de muestreo vigente, exportación/pérdidas y las referencias
de ejecuciones/spans esperados que efectivamente puede consultar el Programador en
Jaeger. Comparar sobre ventana cerrada y declarar provisional la entrega aún pendiente;
si la consulta falla, está truncada o no permite conciliar lo esperado, usar `unknown`.
Una pérdida demostrada o muestreo parcial produce la limitación correspondiente. Con
evidencia íntegra puede presentarse cero observado; sin nuevos lotes, la ausencia de
exportaciones no demuestra por sí sola interrupción ni disponibilidad del receptor.
El umbral de45s se aplica a la continuidad del heartbeat, no a exigir lotes cuando no hay actividad.

Validar por separado: Jaeger/OTLP caído con logs disponibles; Alloy/Loki caído con trazas
consultables; y recuperación de ambos conservando los huecos históricos. Una caída
limita su señal y las derivadas de ella, sin trasladar esa conclusión automáticamente a la otra.

## Vistas técnicas y navegación

`platform.json` provisiona vistas de resumen por operación, resultados/rechazos, archivos
versus registros, distribuciones y continuidad/pérdidas/política. Un panel de logs filtra
por período, función, resultado, severidad y referencia opaca. Enlaces de datos pasan
trace_id a Jaeger y referencias de operación a otras ejecuciones del mismo entorno.
Una traza no disponible muestra límite de muestreo/retención/cobertura, no «nunca ocurrió».
Viewer consulta estos dashboards y fuentes; no necesita Editor ni administración.
El historial administrativo de 006 sigue en su vista funcional y no sirve estos paneles.
