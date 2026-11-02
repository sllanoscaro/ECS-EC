# Contratos internos: Productor real de PDF

Puertos dentro del monolito. Dependencias de datos/eventos no dependen de `notifications`, de SMTP ni de la presencia de un consumidor activo.

## Captura coherente

`Reports.capture(selection, building_id, principal, cutoff_at, unit_of_work)` abre o usa una única transacción REPEATABLE READ. Los puertos siguientes comparten esa sesión; filtros de revisiones/recepciones impiden incorporar datos posteriores a `cutoff_at`. Se copia el resultado inmutable, se confirma y se libera la transacción antes de renderizar.

| Puerto | Salida necesaria |
| --- | --- |
| `Identity.require_report_access(principal, building_id)` | Cuenta activa, sesión válida y permisos actuales de spec-006; rechazo por defecto para identidades técnicas. |
| `Consumption.read_report_snapshot(building_id,start,end,scale,cutoff_at,principal)` | Siete filas energéticas, totales/agregados válidos conservados, origen/base/alcance CAT-01, bloques hora/día/mes con desfase, calidad/cobertura, procedencia y referencias/revisiones. Filas y bloques conservan `source_mode` (`measured`, `calculated`, `mixed` o `unavailable`) y `provenance_segments` con límites, modo, fuente, revisiones y `basis_sources`, conforme a los productores 001/002. |
| `Costs.read_snapshot(building_id,start,end,cutoff_at,principal)` | Ciclos realmente cerrados cuyo fin efectivo está en `[start,end)` y ya ocurrió al corte; último cálculo y última revisión de boleta visibles al corte, y última comparación de ese par exacto; importes/desglose/unidades/moneda/base tributaria, estados/completitud y pares comparables. |
| `EventWriter.append(event, unit_of_work)` | Evento durable idempotente confirmado con el resultado funcional del productor. |

El puerto de costos se coordina con [spec-004](../../004-costos-tarifa-bt43/contracts/integrations.md). No prorratear, sumar dos revisiones, cambiar moneda/base ni recalcular BT4.3. Si hay costos 10/20/30 CLP y boletas 9/29 para ciclos primero/tercero, el subtotal disponible es 60 en tres ciclos y el contraste es 40 frente a 38, diferencia 2 en dos pares. Ausencia de pares no se expresa como diferencia cero.

Los pares de ese ejemplo requieren comparaciones persistidas de las revisiones seleccionadas. Si una boleta se corrige o un cálculo se revisa sin crear otra comparación del par exacto, el ciclo informa `comparison_status=missing_for_selected_revisions`, conserva referencias/valores disponibles y diferencias null, y queda fuera del contraste agregado. No reutilizar una comparación anterior ni retroceder revisiones para obtenerla. Mostrar «Contraste pendiente para estas revisiones»; una captura anterior conserva el par que era visible a su corte. `available`, `no_calculation` y `no_bill` siguen el contrato productor; las consultas no crean comparaciones.

Un total anual válido con detalle mensual retirado sigue siendo el total; el gráfico declara su detalle ausente. Categoría sin fuente es distinta de instalada sin datos y de cero medido. CAT-01 calculada puede informar energía, pero no satisface la base medida requerida para un costo completo.

Si el período atraviesa cambios de modo, fuente o base, copiar los segmentos del productor sin reconstruirlos ni recalcular energía. El PDF sintetiza los períodos, fuentes y bases necesarios para interpretar el total y señala «Origen mixto» cuando corresponda. Un agregado válido de 30 kWh con segmentos de 10 medidos y 20 calculados conserva ese total y ambas procedencias; no se convierte en medición física para costos. Un cambio dentro de un intervalo que el productor declara no numérico conserva su diagnóstico y no se transforma en cero ni se divide para inventar mediciones válidas.

## Instrumentación propia de reports

La capacidad emisora común pertenece a spec-007, según su [especificación](../../007-observabilidad-externa/spec.md) e [investigación trasladada](../../007-observabilidad-externa/research.md), y se implementa en `backend/src/ecs_ec/observability/logging.py` y `tracing.py`. Reports consume ese emisor y añade su instrumentación; no implementa aquí recolectores, visores ni la infraestructura común. El emisor real es prerrequisito de aceptación de esta integración, sin exigir completar toda spec-007.

Propagar el contexto técnico de correlación desde la solicitud hasta el executor y sus etapas de captura, espera, render, preflight y publicación; instrumentar también la descarga. Las trazas identifican comienzo, etapas, duración observada y resultado final, con referencias opacas confiables y distinción entre intentos. El contexto técnico no se añade al contenido funcional del PDF ni al hash funcional de su captura. Tras reinicio, la reconciliación identifica su propia ejecución y la referencia opaca del trabajo recuperado, sin inventar continuidad de un span ya interrumpido.

Los logs estructurados incluyen fecha UTC, entorno, versión, operación, etapa, severidad, resultado, código saneado y correlación cuando exista. Distinguir éxito, rechazo esperado y fallo inesperado. No registrar cookies, tokens, credenciales, binarios ni valores de consumo o importes; las referencias únicas son campos de correlación, nunca etiquetas de métricas.

| Medida derivada mediante LogQL | Hecho y unidad | Ventana y agregación |
| --- | --- | --- |
| Generaciones admitidas | Un evento `report.admitted` por nueva solicitud durable, incluida captura admitida fallida; unidad: generación | Conteo por ventana de observación `[inicio,fin)`; replays idempotentes, rechazos previos, consultas y descargas no incrementan generaciones |
| Resultados terminales de generación | Evento `report.completed` tras confirmar resultado generado o fallido; unidad: generación por resultado | Conteo por ventana `[inicio,fin)` de registro técnico; emitir solo tras ganar la transición exclusiva, sin volver a emitir al releer un resultado terminal |
| Duración de procesamiento | `duration_ms` observado desde claim hasta finalización de render/preflight/publicación, mediante reloj monotónico; unidad: ms | Promedio por ventana `[inicio,fin)` y resultado sobre observaciones presentes; interrupción sin duración observable conserva null y queda fuera del promedio, nunca cero imputado |

Los eventos de etapa y de operaciones HTTP se distinguen de esos eventos de conteo. Dimensiones permitidas: entorno, operación de catálogo, etapa y resultado; sin identidad de persona, edificio, reporte ni archivo como etiquetas. Pérdidas o falta de cobertura se presentan como limitación de las métricas observadas, conforme al emisor de spec-007; no sustituyen resultados/eventos funcionales durables.

La emisión usa las colas acotadas y la política de pérdidas del emisor común. Una caída de transporte, recolectores o visores no impide generar, descargar ni confirmar resultados y `pdf.failed`; no se realizan envíos de red síncronos dentro de las transacciones funcionales.

## Generación y preflight

`Reports.render(snapshot, template_version)` produce en memoria bytes PDF y manifiesto de composición. `Reports.preflight(bytes,manifest)` comprueba parseo independiente, una página 210×297 mm con tolerancia técnica <=0,1 mm, todo texto >=10 pt, seis secciones obligatorias y cajas dentro de márgenes sin intersecciones incompatibles.

La tolerancia de dimensiones responde a representación en puntos, no permite otro formato. Cada cifra compara contra snapshot, las fuentes se incrustan y todas las advertencias esenciales permanecen en la misma página. Un conjunto que no cabe produce fallo funcional, nunca texto menor, anexos o descarga truncada.

`Reports.publish(result,binary,unit_of_work)` verifica hash/longitud, publica `generado` y binario juntos. Guardar BYTEA evita éxito confirmado con objeto externo ausente. Trabajos iniciados por un proceso interrumpido se reconcilian como fallo único; no se entrega su buffer parcial.

## Resultado fallido y evento `pdf.failed`

Modelo compartido: `backend/src/ecs_ec/audit/models.py`; escritor: `backend/src/ecs_ec/audit/events.py`. Los productores no importan modelos ni servicios del consumidor.

| Campo | Valor/contrato |
| --- | --- |
| `event_id` | UUID estable asignado por productor |
| `type` | `pdf.failed` |
| `source_module`, `source_entity_id`, `source_revision` | `reports`, identidad del resultado y revisión positiva; UNIQUE por módulo/entidad/revisión/tipo |
| `occurred_at`, `recorded_at` | Instante del fallo y registro UTC; no sustituir período medido |
| `category_id` | NULL para fallo global del documento |
| `measurement_window` | Ventana seleccionada cuando es conocida, sin inferirla desde `recorded_at` |
| `accepted_new_data` | `false` |
| `functional_result`, `safe_payload` | Estado fallido, motivo de catálogo y referencia opaca de reporte; sin consumos personales, binario, excepciones, SQL, credenciales ni configuración |
| `correlation_ref` | Referencia opaca confiable, no correo ni nombre de persona |

Resultado fallido y evento se guardan en la misma transacción. Tras error de una transacción abortada, abrir una unidad de trabajo nueva para registrar ambos; jamás publicar el evento de forma aislada mientras el resultado desaparece en rollback. Si no se puede confirmar base, no se afirma que el resultado/evento sean durables.

Motivos funcionales de diseño: `captura_no_disponible`, `composicion_no_admisible`, `validacion_documento_fallida`, `generacion_interrumpida`, `generacion_no_completada`. El detalle técnico se sanea según observabilidad y no viaja en el evento. Un reporte válido sin datos no es un fallo. Descarga repetida, consulta de estado y rechazo previo por permisos/selección no crean eventos de fallo del generador.

Consumir/reintentar el mismo evento no crea otro resultado de PDF. La spec-008 conecta este contrato cuando exista el productor real; su ausencia no impide probar generación, persistencia y evento aquí.
