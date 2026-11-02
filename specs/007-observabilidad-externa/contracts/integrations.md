# Contrato de instrumentación y cobertura

Propietario 007. [Modelo](../data-model.md), [señales](signals.md),
[políticas/acceso](technical-access.md), [arquitectura](../../../docs/architecture.md).
Puertos internos y configuración de infraestructura; sin API funcional nueva.

## Puertos del emisor

| Puerto conceptual | Entrada / salida y efectos |
| --- | --- |
| `Telemetry.begin` | Operación registrada/contexto confiable → contexto opaco/reloj monotónico; no adopta parent o identidad de cabeceras públicas. |
| `Telemetry.stage` | Contexto/etapa registrada → span/registro de etapa, sin conteo terminal adicional. |
| `Telemetry.complete` | Resultado, código, duración y conteos tipados → admisión best effort; un terminal por transición lógica ganada, no por capa. |
| `Telemetry.continue` | Contexto interno/referencia durable del productor → ejecución relacionada; no reconstruye parentesco desde nombres/texto. |
| `Telemetry.health` | Snapshot acotado de secuencias/colas/pérdidas → heartbeat/control; sin datos de negocio. |
| `Telemetry.shutdown` | Detiene admisión y drena con presupuesto total de 5 s en lifespan; residuo contado, sin espera indefinida. |

Admisión no espera red/disco ni toma locks de negocio. Resultado técnico `enqueued`,
`dropped` o `disabled` no cambia respuesta, permisos o commit. Error de serialización o
exportación se absorbe en frontera técnica y cuenta como pérdida. No registrar el error
del logger recursivamente por el mismo logger. Deshabilitación deja stderr mínimo seguro.

Aplicar allowlist antes de Loguru, SDK y colas. `diagnose=False`/`backtrace=False` no
sustituyen el saneamiento. Deshabilitar handlers por defecto y capturas de cuerpos,
excepciones, SQL, URLs/query, cabeceras, IP, emails y objetos completos. Solo códigos
registrados se convierten en texto legible.

El sink serializa exclusivamente el sobre del esquema, con JSON estricto sin NaN/Infinity;
no volcar el record completo de Loguru ni su `extra` mediante serialización automática.
Cada función/módulo y prueba propios documentan propósito, entradas, salidas, errores
y efectos, conforme a la constitución; los procedimientos se actualizan con el código.

## Resultados

- `success`: contrato ejecutado, incluida consulta sin datos.
- `expected_rejection`: validación, duplicado, anticipo, selección o permiso rechazados
  conforme al dominio; INFO/WARNING y código, sin excepción imprevista.
- `unexpected_error`: fallo técnico inesperado; ERROR y código seguro, sin excepción cruda.
- Recepción mixta terminada con decisiones válidas: `success` y conteos. Sin novedades
  por rechazo/duplicados: `expected_rejection`. Un fallo técnico parcial de un intento
  recuperable termina únicamente su ejecución con `unexpected_error`; no cierra el intento.

El resultado significa lo mismo en las tres señales. Los estados por registro de 002
(`accepted|duplicate|rejected`) conservan sus motivos y no se confunden con resultado global.

## Catálogo de cobertura inicial

Nombres técnicos 007 mapeados al contrato propietario; etapas estáticas. Terminal por
fila como única fuente de `operations_total` para esa operación, salvo admisiones.

| Propietario / operación | Etapas relevantes | Terminal y unidad |
| --- | --- | --- |
| 003 `acquisition.receive` | `authenticate`, `transfer`, `seal` | `operation.completed`: sesión/intento SFTP; abortado/vacío no finge recepción002 |
| 003 `acquisition.process` | `claim`, `parse`, `validate`, `receive`, `publish` | `operation.completed`: evaluación sellada, resumen de archivos |
| 001/002 `reception.accept` | `authorize`, `validate`, `deduplicate`, `commit`, `aggregate` | `reception.completed`: transición durable a intento002 `completed`, resumen completo; `execution.completed`: ejecución de procesamiento, contada aparte |
| 002 `consumption.aggregate` | `claim`, `calculate`, `commit` | `operation.completed`: evaluación de agregado/CAT-01, sin nueva recepción |
| 002 `consumption.retention` | `authorize`, `validate`, `withdraw`, `commit` | `operation.completed`: mantenimiento, sin valores energéticos |
| 001 `consumption.query_detail` | `authorize`, `read`, `project` | `operation.completed`: consulta terminada |
| 002 `consumption.query_aggregates` | `authorize`, `read`, `aggregate`, `project` | `operation.completed`: consulta terminada |
| 004 `cost.calculate` | `authorize`, `capture`, `calculate`, `commit` | `operation.completed`: cálculo solicitado |
| 004 `cost.compare` | `authorize`, `capture`, `compare`, `commit` | `operation.completed`: contraste solicitado |
| 004 `cost.query` | `authorize`, `read`, `project` | `operation.completed`: consulta de costos/boletas/contraste |
| 005 `report.generate` | `authorize`, `capture`, `wait`, `render`, `preflight`, `publish` | `report.admitted`: admisión durable; `report.completed`: generación terminada |
| 005 `report.query`, `report.download` | `authorize`, `read`, `deliver` | `operation.completed`: consulta/descarga, nunca generación |
| 006 `identity.authenticate` | `validate`, `authenticate`, `commit` | `operation.completed`: intento de ingreso sin identidad personal |
| 006 `identity.authorize` | `authorize` | `operation.completed`: decisión de acceso |
| 006 `identity.session` | `validate`, `commit` | `operation.completed`: logout/renovación/cambio propio de contraseña |
| 001/004/006 `administration.change` | `authorize`, `validate`, `coordinate`, `commit` | `operation.completed`: intento administrativo, incluida denegación; origen registrado |
| 006 `administration.query` | `authorize`, `read`, `project` | `operation.completed`: lectura de historial funcional |

Cada fila exige comienzo, etapas ejecutadas y resultado final verificables en logs y
trazas. `operation.started`, `stage.completed`, `execution.completed`, `telemetry.heartbeat`
y `policy.changed` son diagnóstico/control, excluidos de conteos de operaciones. Un span
interrumpido no se cierra como éxito ficticio. Ante denegación previa al módulo, la
dependencia común emite el terminal objetivo una vez; `identity.authorize` es decisión
separada, no se suma como segunda consulta de negocio.

Extender catálogo exige actualizar contrato, esquema, dashboard y pruebas. Instrumentación
008 sigue a cargo de su propietario, sin incluirla implícitamente en aceptación inicial.

## Correlación y reintentos

Ingreso HTTP público genera contexto nuevo: descartar `traceparent`, `baggage`,
`X-Request-ID`, roles o referencias autodeclaradas para relaciones verificadas.
Procesos internos solo usan contexto generado por servidor.

Consumir identidades confiables de [003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md)
y [002](../../002-registro-retencion-consumo/contracts/integrations.md). Publicación
reintentada conserva referencia técnica y cambia intento; recuperación conserva intento
y cambia ejecución. No añadir campos a CSV/JSON, credenciales, lecturas, boletas o PDF.
Bindings distintos no se relacionan solo por nombres/hashes coincidentes.

Trabajo diferido conserva referencia opaca en su sobre interno, propiedad del productor.
Si solo sobrevive referencia lógica, nueva traza con esa referencia y `recovered`, sin
falsificar continuidad. Visores encuentran todas las ejecuciones por operación/publicación.

Productor emite el terminal lógico tras commit, solo al ganar transición exclusiva.
Cada ejecución efectiva de procesamiento de recepción emite `execution.completed` al
terminar, excluido del conteo lógico; releer un resultado terminado sin procesar trabajo no emite otro
terminal ni incrementa ejecuciones de procesamiento. Caída entre commit/emisión puede perder señal: declarar cobertura
limitada, sin convertir el logger en escritor transaccional o reconstruir historial con logs.
005 conserva su contrato `report.admitted`/`report.completed` y duración desde claim.
Un rechazo previo a admisión durable de PDF puede emitir `operation.completed` para
diagnóstico, pero queda excluido de generaciones admitidas/terminadas: esas medidas
solo usan `report.admitted`/`report.completed`. No crear un resultado de generación
ni un evento funcional `pdf.failed` por ese rechazo.

### Recepción parcialmente fallida y recuperada

Aplicar los estados de [002](../../002-registro-retencion-consumo/contracts/integrations.md):
`processing` y `partial_failure` son recuperables, no terminales lógicos. Mientras el
intento permanezca en esos estados, no emitir `reception.completed`. Una ejecución que
termina con fallo emite como máximo un `execution.completed` con `unexpected_error`,
su `execution_ref`, código seguro y `counts=null`. Los logs de etapa pueden identificar
progreso confirmado, pero no alimentan los conteos terminales de registros.

Reservar `reception.completed` para quien gana la transición durable del intento a
`completed`. Su resumen contiene los resultados completos originales del intento,
incluidas posiciones confirmadas antes de recuperarlo; no solo las procesadas en la
última ejecución. Los conteos de recepción y novedades proceden exclusivamente de ese
resumen. Recuperar conserva `attempt_ref` y crea otra `execution_ref`; un reenvío explícito
crea otro intento. Estos eventos técnicos no cambian estados, transacciones o evidencia de002.

Caso de referencia: una ejecución incorpora tres registros y falla con dos pendientes;
otra ejecución del mismo intento incorpora los dos restantes. Sin pérdidas, se observan
dos `execution.completed` (un fallo y un éxito), un `reception.completed` exitoso y cinco
aceptaciones contadas una vez. La proporción de error por ejecución es 50 %; la del
intento lógico completado es 0 %. Cada panel debe indicar la unidad y el denominador.

## Salud de transporte por señal

`Telemetry.health` informa `log_collector_status`/`last_log_collector_success` para
Alloy y `trace_export_status`/`last_trace_export_success` para el exportador OTLP. Los
campos son obligatorios en el objeto `health`, con estados `available|degraded|unknown`
y fechas UTC nullable; el esquema define sus límites. Un estado `available` requiere
un último éxito observado no null. Sin comprobación o exportación observada, usar
`unknown`; una ausencia de nuevos envíos no demuestra por sí sola un fallo.

El exportador incrementa `trace_exported_spans_total` una vez por cada span de un lote
cuya exportación se confirma. Incrementa `trace_export_failures_total` una vez por lote
que termina sin éxito al agotar su presupuesto; los reintentos internos no multiplican
estos contadores. Ambos son enteros acumulados >=0 por arranque, distintos de
`spans_dropped_total` y de la profundidad de cola. Una confirmación OTLP acredita
aceptación por transporte, no persistencia consultable en Jaeger.

El estado de Alloy no certifica trazas. La cobertura de cada señal combina su política,
pérdidas, referencias/ejecuciones esperadas y señales consultables; ante evidencia
insuficiente queda `unknown`. La consulta humana autorizada comprueba las trazas de
Jaeger sin conceder permiso de consulta a credenciales de ingesta. No crear un servicio
o una ruta automática de lectura de trazas para resolver esta verificación.

## Plataforma y productores

009 registra inicialización/cierre y compone extensiones sin importar negocio desde
`observability`. `FunctionalAudit`/`EventWriter` confirman evidencia con resultados del
productor. Eventos técnicos de nombre parecido no se publican en ese bus ni lo reemplazan.

001–006 incorporan llamadas de dominio y prueban resultados conocidos. 007 aporta emisor,
contratos, infraestructura y pruebas transversales. Fixture de productor inexistente
solo prueba el emisor: no acredita SC-002 ni autoriza implementarlo desde 007.
Receptores/visores detenidos no invalidan commits, permisos o registros funcionales.
Sin dependencia de SMTP/consumidor008.
