# Data Model: Reportes PDF por período

## Convenciones y relaciones

Modelo lógico del módulo `reports`, previo a migraciones. Identidades, edificio, cuentas, energía y costos pertenecen a sus módulos; aquí se conservan referencias y la captura necesaria para reproducir el documento.

- Identidades: «UUID generado por la aplicación».
- Instantes: «UTC con zona IANA del edificio identificada»; ventanas «`[inicio,fin)`, siempre inicio < fin».
- Valores: «Decimal finito serializado como cadena; ausencia es NULL con motivo, nunca cero imputado».
- Conservación: «al menos 12 meses calendario desde registro o revisión sustantiva; no borrar evidencia referenciada todavía protegida».
- JSONB: «estructura tipada y versionada, sin secretos ni detalles técnicos de excepción».

```text
Cuenta/Edificio -> ReportRequest -> ReportSnapshot -> ReportResult -> ReportBinary
                                     |
                     Referencias de consumo/costos/calidad
ReportResult fallido -> FunctionalEvent (audit, tipo pdf.failed)
```

## Solicitud (`report_request`)

| Campo | Restricción |
| --- | --- |
| `id`, `building_id`, `requested_by` | UUID generado por la aplicación; actor/edificio conocidos |
| `scale` | `diario`, `mensual` o `anual` |
| `selection` | Exactamente los campos aplicables: fecha; año/mes; o año |
| `timezone`, `window_start`, `window_end` | Zona IANA válida y límites calendario; inicio < fin |
| `cutoff_at`, `created_at` | Corte fijado al inicio; no avanzar durante render o descarga |
| `state` | `pendiente`, `generando`, `generado`, `fallido` |
| `revision` | Entero positivo para transición exclusiva |
| `idempotency_key`, `request_hash` | UNIQUE `(requested_by, operation, idempotency_key)`; misma clave/cuerpo devuelve solicitud original; cuerpo distinto es conflicto |
| `retain_until` | Aniversario mínimo y dependencias protegidas |

Una selección totalmente futura, incompleta o inexistente se rechaza antes de crear un reporte válido. Año/mes deben representar un intervalo real; mensual usa mes 1..12. No hay opciones arbitrarias de páginas/secciones.

## Captura (`report_snapshot`)

| Campo | Restricción |
| --- | --- |
| `id`, `request_id` | UUID; UNIQUE `request_id` |
| `schema_version` | Entero positivo |
| `source_revisions`, `source_refs` | Referencias versionadas y opacas, sin secretos |
| `building_name`, `window`, `timezone`, `cutoff_at` | Los mismos valores fijados en solicitud |
| `energy_rows` | Exactamente siete filas, CAT-01..CAT-07, sin categorías repetidas; cada fila conserva `source_mode` y `provenance_segments` del productor |
| `chart_blocks` | Hora/día/mes según escala; límites reales y desfase identifican horas repetidas; conservar también modo y segmentos de procedencia de cada bloque |
| `financial_snapshot` | Resultado tipado de Costs.read_snapshot con cierres efectivos y revisiones al corte |
| `quality_notes`, `provenance` | Limitaciones funcionales y origen de prueba identificado, sin informe privado del simulador |
| `functional_hash`, `created_at`, `retain_until` | SHA-256 del contenido funcional canónico y conservación |

Captura «inmutable después de confirmarse». Una fila energética conserva código/nombre, valor nullable, unidad kWh, cobertura, estado temporal/calidad, `source_mode: measured|calculated|mixed|unavailable` y `provenance_segments` conforme a los productores de [001](../001-visualizar-consumo-categorias/contracts/http.md) y [002](../002-registro-retencion-consumo/contracts/http.md). Cada segmento conserva límites temporales, modo, fuente, revisiones y `basis_sources` con los pares categoría/fuente contribuyentes, además de la base/alcance de CAT-01 cuando corresponda. El estado sin medidor se mantiene separado del modo de origen. La captura copia estos datos sin reconstruir segmentos ni recalcular energía; totales históricos válidos se conservan aunque falte detalle del gráfico.

El conjunto financiero preserva ciclo, cierre efectivo, alcance de consumo, moneda/base tributaria, cálculo/boleta/comparación/revisiones, cantidades/importes y limitaciones. «No sumar monedas o bases incompatibles». Subtotal disponible y comparación pareada son alcances separados; no prorratear ni contar dos revisiones del mismo ciclo.

Conservar `comparison_status` y las referencias seleccionadas tal como las entrega spec-004. `missing_for_selected_revisions` mantiene diferencias nulas y excluye ese ciclo de importes y conteo del contraste agregado, conservando aparte sus importes disponibles. Una comparación anterior no sustituye la del par seleccionado; una comparación nueva no altera capturas confirmadas.

## Resultado (`report_result`)

| Campo | Restricción |
| --- | --- |
| `id`, `request_id`, `snapshot_id` | UUID; UNIQUE `request_id`; snapshot opcional solo si falló su captura |
| `state` | `generado` o `fallido` |
| `issued_at`, `cutoff_at` | Fecha de emisión distinta del corte |
| `filename` | Nombre seguro que identifica edificio, escala y período |
| `page_count` | Exactamente 1 para resultado generado |
| `page_width_mm`, `page_height_mm` | 210 y 297 para resultado generado |
| `minimum_font_pt` | >=10 para todo el texto del resultado generado |
| `layout_manifest`, `validation_version` | Cajas/fuentes/estados de validación tipados; sin exposición técnica en UI |
| `functional_reason_code`, `correlation_ref` | Código funcional saneado si falló y referencia opaca |
| `binary_id`, `sha256`, `byte_length` | Presentes solo para generado; hash/longitud corresponden a bytes íntegros |
| `created_at`, `retain_until` | Registro y conservación mínima |

Resultado «inmutable después de confirmarse». Un fallo no tiene binario descargable. Si el render no cabe o su preflight falla, el resultado es fallido y no se presenta un éxito parcial.

## Binario (`report_binary`)

`id`, `result_id` UNIQUE, `content_type=application/pdf`, `content` BYTEA, longitud positiva y SHA-256. «Acceso solo mediante descarga autenticada y autorización vigente». No ruta estática/pública, carga remota ni secreto en metadatos. Su publicación es atómica con el resultado generado.

## Evento funcional compartido

`FunctionalEvent` reside en `audit/models.py` y su escritor en `audit/events.py`. Campos/envelope de [integrations.md](contracts/integrations.md). Un fallo publicado cumple «UNIQUE `(source_module, source_entity_id, source_revision, type)`», `type=pdf.failed` y `accepted_new_data=false`.

No genera eventos de fallo de PDF una mera consulta de estado o repetición de descarga, ni una petición rechazada por validación/permisos antes de admitirse. El resultado de fallo admitido y evento se confirman juntos. Falta de base para registrar el resultado no se presenta como evento durable confirmado.

## Transiciones y consistencia

| Estado | Hecho | Resultado |
| --- | --- | --- |
| Sin solicitud | Petición válida y captura persistida | Pendiente |
| Pendiente | Claim exclusivo de capacidad | Generando |
| Generando | Bytes/preflight válidos | Generado y binario íntegro atómicos |
| Pendiente/generando | Fallo funcional admitido | Fallido y pdf.failed atómicos |
| Generando tras reinicio | Proceso anterior interrumpido | Fallido con razón de interrupción y evento único |
| Generado/fallido | Nueva petición para reintentar | Nueva identidad; anterior conservada |

La captura usa unidad de trabajo REPEATABLE READ compartida con puertos de energía/costos, limita versiones por corte y se confirma antes del render. No se mantienen transacciones de lectura mientras se compone el PDF. UNIQUE/CAS impiden publicar dos resultados para una solicitud. La retención usa la función común de aniversario con segunda ocurrencia si se repite la hora.
