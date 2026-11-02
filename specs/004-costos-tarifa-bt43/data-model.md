# Data Model: Costos BT4.3

Diseño previo a código. Propiedad de `costs`; identidad, consumo y eventos pertenecen a sus módulos comunes. No existen claves foráneas hacia notificaciones.

## Convenciones

- «UUID para identidades; revisión entera >=1». Tablero y suministro pertenecen al edificio único.
- «Instantes UTC y zona IANA; ventanas [inicio,fin), inicio < fin». Conservar también límites declarados y criterio temporal cuando una boleta solo proporciona fechas.
- «Decimal finito en cadenas y NUMERIC; sin float, NaN o infinito». Precios/cantidades medidas no negativos; los importes de boleta y diferencias conservan signo.
- «created_at, actor_id o process_ref y retain_until en toda revisión histórica». El actor procede de identidad autenticada, nunca del cuerpo declarado por el usuario.
- Las capturas JSONB tienen esquema y versión; no contienen archivos, secretos ni excepciones. No hay eliminación en cascada de evidencia protegida.

## Entidades compartidas desde fundaciones

### Suministro (`cost_supply`)

| Campos | Restricción |
| --- | --- |
| `id`, `building_id` | «UNIQUE building_id; un suministro general por edificio» |
| `revision`, `updated_at`, `actor_id` | Revisión positiva, incrementada atómicamente al modificar; ETag fuerte derivado de id/revisión. Actor autenticado y auditoría en la misma UoW. |
| `general_board_ref`, `category_id` | «category_id=CAT-01; medición física del tablero general» |
| `distributor`, `location`, `connection_conditions`, `document_refs` | Referencias administrativas; su ausencia impide un perfil real completo, no se inventan valores. |
| `measurement_point_differences` | Diferencias documentadas respecto del punto de la distribuidora; sin factores implícitos. |

La primera escritura crea revisión 1 mediante `If-None-Match: *`; las siguientes exigen el ETag vigente en `If-Match`. La captura de cada cálculo conserva id/revisión y los valores del suministro utilizados, incluidos sus diferencias de punto de medición; editar el suministro no modifica capturas anteriores.

### Perfil versionado (`cost_profile_version`, `cost_profile_segment`, `cost_profile_charge`)

| Campos | Restricción |
| --- | --- |
| `id`, `supply_id`, `revision`, `previous_version_id` | «UNIQUE (supply_id, revision); versiones inmutables»; anterior nullable solo para primera versión. |
| `tariff`, `currency` | «tariff=BT4.3; currency=CLP inicialmente» |
| `publication_state`, `created_at` | `draft` o `published`, fijado al crear la revisión; un borrador no cambia la selección publicada. Publicarlo exige una nueva revisión. |
| `timezone`, `source_refs`, `territory_conditions` | Zona IANA y referencias/condiciones capturadas de la revisión. |
| Segmento: `id`, `profile_version_id`, `valid_from`, `valid_to` | «valid_to nullable o >valid_from»; intervalos [inicio,fin) sin superposiciones dentro de la misma revisión. |
| Segmento: `peak_calendar`, `historical_rule`, `billing_month_policy`, `rounding_policy`, `source_refs` | Datos tipados documentados, con versión y vigencia; no basta una etiqueta sin parámetros. |
| Cargo: `segment_id`, `code`, `kind`, `quantity_unit`, `unit_price`, `tax_basis`, `applicability`, `vigency_strategy`, `source_refs` | «UNIQUE (segment_id,code); precio Decimal >=0» |
| `kind` | «energia, transmision, servicio_publico, fijo, demanda_punta, potencia_suministrada, impuesto, otro_documentado» |
| `tax_basis` | «neto, impuesto_incluido, impuesto_separado» |
| `rounding_policy` | «precisión >0, quantum >0, modo y etapa de redondeo explícitos» |

Cada revisión contiene el calendario completo de segmentos, incluidos los antecedentes históricos que conserva. Seleccionar la última revisión `published` visible al corte y resolver todos los cargos contra sus segmentos; no mezclar calendarios de distintas revisiones. Un hueco de vigencia limita los cargos afectados. Sin revisión publicada, el perfil no está disponible para un resultado completo.

Publicar una revisión sustituye la selección para cálculos nuevos sin modificar revisiones anteriores. Ejemplo sintético: V1 contiene [enero,infinito) a 100 CLP/kWh; V2 contiene [enero,julio) a 100 y [julio,infinito) a 110. Una corrección retroactiva V3 copia el calendario completo con los segmentos corregidos; cálculos existentes conservan V1/V2 y solo un recálculo explícito usa V3. El solapamiento entre revisiones es histórico y válido; dentro de una revisión se rechaza.

`expected_previous_version_id` es obligatorio en la creación (null solo si aún no existe ninguna revisión). Comparar bajo bloqueo del suministro con la última revisión guardada, incluidos borradores; discrepancia devuelve 409 sin publicación parcial. La asignación de revisión, encadenamiento y auditoría son atómicos. `GET /costs/profiles` expone `latest_version_id` y `selected_published_version_id` para distinguir concurrencia y selección.

El núcleo conoce estrategias versionadas y cerradas. `vigency_strategy` y `applicability` identifican estrategia soportada y parámetros/documento; una desconocida produce limitación, no evaluación de texto. Energía se segmenta por vigencias sin dividir lecturas carentes de resolución. Cargos fijos/demanda se aplican únicamente cuando su estrategia documentada resuelve el ciclo, sin prorrateo arbitrario. Capturar id/revisión del perfil y los segmentos utilizados.

### Ciclo (`cost_billing_cycle`)

`id`, `supply_id`, `start_at`, `end_at`, `timezone`, `declared_start/end`, `boundary_criterion` y `boundary_limited`. El mes de referencia de demanda pertenece a la captura de cada cálculo, no a una propiedad mutable del ciclo.
«UNIQUE (supply_id,start_at,end_at); start_at < end_at». El mes de emisión no sustituye sus límites. El fin efectivo determina su selección en reportes; ciclo cerrado significa `end_at <= cutoff_at` con límites efectivos identificables.

### Captura de entradas (`cost_input_snapshot`)

`id`, `cycle_id`, `cutoff_at`, `schema_version`, `engine_version`, `input_hash`, `source_refs`, `supply_capture`, `general_measurements`, `demand_blocks`, `monthly_maxima`, `profile_capture`, `billing_month_ref`, `billing_month_source_ref`, `billing_month_policy_version`, `source_coverage`, `measurement_point_differences`, `created_at`, `retain_until`.

«Solo CAT-01 de origen medido; nunca sustituir por total calculado». Conservar los valores, unidades, períodos, cobertura y revisiones de cada antecedente usado; las referencias originales son complementarias. Máximos incluyen mes, valor y calidad, sin deduplicar meses por igualdad de valor. El hash incluye representación decimal canónica, referencias, políticas temporales y versión del motor.

`billing_month_ref` es `YYYY-MM` o null con causa `billing_month_unresolved`. `billing_month_policy` identifica versión, fuente documental y modo `documented_rule` (regla cerrada/parametrizada) o `explicit_evidence` (mes aportado con evidencia y validado en servidor). No inferirlo del mes de emisión, inicio o fin sin una regla documentada que lo autorice. Capturar el mes resuelto, fuente y versión de política; ante ausencia o contradicción limitar los cargos históricos/de punta afectados, conservando los demás componentes calculables. Si los segmentos no resuelven una política inequívoca para el ciclo, también hay limitación. Corregir el mes genera otra revisión del cálculo, conservando la captura anterior.

La política declara `version`, `mode`, `source_refs` y, en modo `documented_rule`, `rule_id`/`parameters` del catálogo cerrado. En modo `explicit_evidence`, `billing_month_source_ref` contiene referencia documental y metadatos de suministro, límites del ciclo y mes declarado, preservados con actor autenticado. Validar formato, coincidencia de esos metadatos con la solicitud y compatibilidad con la política registrada; la verificación del contenido documental la declara el Administrador y no exige interpretación automática/OCR. En modo de regla documentada, el servidor genera la referencia a la fuente/política que resolvió el mes.

## Entidades de resultados e historias

### Cálculo (`cost_calculation`, `cost_calculation_component`)

| Campos | Restricción |
| --- | --- |
| `id`, `cycle_id`, `revision`, `snapshot_id`, `previous_id` | «UNIQUE (cycle_id,revision); previous_id nullable solo en primera revisión» |
| `execution_state` | «completado o fallido» |
| `temporal_state` | «en_curso o cerrado» |
| `sufficiency` | «completo, parcial o no_calculable» |
| `available_subtotal`, `complete_total`, `net_total`, `tax_total`, `currency` | «complete_total nullable; solo presente si sufficiency=completo y execution_state=completado» |
| `reason_codes`, `cutoff_at`, `engine_version`, `created_at`, `recorded_by`, `retain_until` | Causas funcionales tipadas y evidencia, sin detalles técnicos sensibles. |
| Componente: `code`, `basis_value`, `unit`, `rule_id`, `unit_price`, `tax_basis`, `unrounded_amount`, `presented_amount`, `state`, `limitation_codes`, `profile_version_refs`, `evidence_refs` | «UNIQUE (calculation_id,code); importes/base nullable si no calculables» |

Un cálculo puede ser completo pero provisional por ciclo en curso: no proyecta consumo al cierre. `available_subtotal` se identifica como disponible, nunca como costo BT4.3 completo cuando faltan conceptos. Resultados y componentes son inmutables; una corrección crea nueva revisión. Consulta ordinaria lee resultados disponibles y no genera revisiones administrativas.

### Boleta y revisión (`cost_bill`, `cost_bill_revision`, `cost_bill_line`)

Identidad: `id`, `supply_id`, `external_identifier_normalized`; «UNIQUE (supply_id,external_identifier_normalized)». Una repetición idéntica devuelve el recurso; cambiar datos requiere una revisión explícita y conserva las anteriores.

Revisión: `id`, `bill_id`, `revision`, `cycle_id`, `issued_at`, `document_reference`, `currency`, `energy_read`, `demand_read`, `demand_billed`, `declared_tax`, `total_payable`, `boundary_limited`, `created_at`, `actor_id`, `retain_until`; «UNIQUE (bill_id,revision)». Lecturas y bases facturadas tienen campos separados y pueden ser null cuando el documento no las proporciona.

Línea: `code`, `description`, `quantity`, `unit`, `amount`, `tax_basis`, `tax_amount`, `cycle_relation`, `document_reference`; «amount firmado; quantity/tax_amount nullable si no constan». Las deudas, intereses, créditos y ajustes no se fuerzan al costo eléctrico comparable. No se carga OCR ni se interpreta un PDF.

### Comparación (`cost_comparison`, `cost_comparison_line`)

`id`, `calculation_id`, `bill_revision_id`, `revision`, `cutoff_at`, `comparable_calculated`, `comparable_billed`, `delta_amount`, `delta_percent`, `excluded_lines`, `limitation_codes`, `created_at`, `actor_id/process_ref`, `retain_until`; «UNIQUE (calculation_id,bill_revision_id,revision)».

Línea conserva código, suministro, ciclo, moneda, base tributaria, ambas cantidades/importes y referencias. Solo líneas alineadas entran a subtotales comparables. «delta=calculado-facturado; delta_percent=100*delta/abs(facturado) si facturado!=0; NULL si facturado=0». Sin boleta se mantiene el cálculo y no se crea una comparación inventada. Corrección registra otra comparación con referencias previas intactas.

### Idempotencia (`cost_operation_idempotency`)

`actor_id`, `operation`, `key`, `request_hash`, `resource_id`, `http_status`, `created_at`, `retain_until`; «UNIQUE (actor_id,operation,key); misma clave/cuerpo reutiliza resultado, cuerpo distinto conflicto». Guardar con el cambio; autorizar antes de recuperar la clave. Revisión mediante `If-Match` previene sobrescritura concurrente.

## Fórmulas y estados

- Energía: suma de kWh físicos válidos contenidos completamente en la ventana, por vigencia, multiplicada por precio de cada cargo energético. No promediar, imputar ni cobrar categorías parciales.
- Demanda desde energía: `P_kW=E_kWh/0.25` para bloque exacto de 15 minutos completo. Registros de potencia integrados válidos también sirven; datos horarios no permiten inferir el máximo.
- Potencia suministrada: promedio de los dos mayores máximos mensuales de la ventana de 12 meses incluida la referencia facturada, con cobertura suficiente y sin descartar empates de meses diferentes.
- Punta: máximo válido leído en punta del mes aplicable o promedio de los dos mayores máximos mensuales del período de punta inmediatamente anterior en meses sin punta, conforme al perfil registrado.
- Redondeo: aplicar exactamente la política capturada. Impuestos incluidos no se vuelven a aplicar. Cada total/subtotal se reconcilia con su desglose visible.
- `en_curso` no significa incompleto por sí solo; cobertura, suficiencia y temporalidad se declaran por separado. Ausencia o resolución insuficiente nunca crea una magnitud cero.

## Resultado fallido y evento común

`FunctionalEvent` pertenece a `audit/models.py`; su escritura a `audit/events.py`. El evento `cost.failed` identifica módulo `costs`, id de cálculo fallido y revisión, fechas UTC, código funcional permitido, referencias opacas y `accepted_new_data=false`. «UNIQUE (source_module,source_entity_id,source_revision,type)».

Un resultado `fallido` y su evento se confirman juntos en la misma unidad de trabajo válida. Si el intento anterior abortó, el registro usa una nueva transacción después del rollback. Un error de validación del formulario o una base incompleta prevista no produce automáticamente `cost.failed`. Un fallo de base impide afirmar persistencia y no se transforma en evento de correo recursivo.

## Conservación y lectura a corte

Registro/revisión inicia su mínimo de 12 meses calendario en la zona del edificio. Día inexistente usa último válido; hora inexistente primer instante posterior y repetida la segunda ocurrencia. Consulta/duplicado no reinicia el plazo. Proteger captura, máximos, perfil y boleta hasta la fecha máxima de sus dependientes conservados. No hay borrado automático obligatorio al cumplir el mínimo.

`Costs.read_snapshot` es un DTO inmutable de lectura; no duplica tablas de resultados. Por ciclo selecciona el último cálculo y la última revisión de boleta visibles a `cutoff_at`; después la última comparación cuyo `calculation_id` y `bill_revision_id` coincidan exactamente con ambos. No retroceder a versiones antiguas para obtener una comparación. Una corrección posterior al corte no cambia esa captura.

Con ambos recursos y sin comparación exacta, devolver `comparison_status=missing_for_selected_revisions`, sus referencias/valores disponibles y diferencias null; excluir el ciclo del contraste agregado. Una comparación exacta da `available`; falta de cálculo o boleta da `no_calculation` o `no_bill` respectivamente (si faltan ambos, `no_calculation`). Estados de ausencia del contraste se derivan al leer, sin modificar comparaciones históricas. Un porcentaje null por facturado cero conserva una comparación `available`.

Devuelve ciclos cerrados por su fin efectivo, importes disponibles, conteos de completitud y pares comparables con referencias. Un reporte puede conservar su propia captura y extender las referencias protegidas que todavía necesita.
