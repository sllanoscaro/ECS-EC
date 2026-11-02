# Contrato de interfaz: Costos BT4.3

Exportación estática Next; datos privados por API autenticada del mismo origen. Selección de ciclo/cálculo/boleta mediante parámetros de consulta; ninguna identidad dinámica privada se incluye en el build.

## Consulta `/costos/`

Operador y Administrador consultan período, suministro, ciclo real, zona y corte. Gráfico y tabla usan idénticas filas de la respuesta; no distribuyen cargos mensuales entre horas ni categorías. Mostrar costo calculado, importe facturado comparable y total a pagar como magnitudes diferentes cuando corresponda.

Detalle de cálculo: energía física del tablero, regla/base/unidad/precio/importe por cargo, perfil utilizado, máximos/históricos y redondeo. CAT-01 calculada se identifica como base general ausente. Cobertura y ciclo en curso se presentan separadamente; una suma disponible parcial nunca aparece como costo BT4.3 completo.

Contraste: columnas calculado, facturado y diferencia; conceptos alineados usan misma moneda/base tributaria. Créditos y exclusiones mantienen signo y explicación. Facturado cero muestra porcentaje «No aplica», no infinito. Sin boleta conserva costo y muestra «Sin boleta registrada».

Mostrar las revisiones seleccionadas de cálculo y boleta. Si existe boleta pero falta comparación del par exacto, mostrar «Contraste pendiente para estas revisiones» (`missing_for_selected_revisions`) y diferencias ausentes; la comparación anterior queda accesible con sus referencias históricas. No sustituirla por el contraste actual ni generar comparaciones durante la consulta.

## Administración `/administracion/costos/`

Solo Administrador registra suministro/perfiles/boletas y recálculos. Formularios por campos tipados, fuentes/vigencias y confirmación de nueva revisión; mantener entradas ante validación y solicitar revisión actual ante conflicto. No hay selector de tarifa distinta de BT4.3, upload/OCR de boleta ni ajuste automático para forzar coincidencia.

**Calcular/Recalcular**: `CalculationForm.tsx` permite elegir suministro/ciclo, revisar límites/zona y aportar mes/fuente cuando la política documentada lo requiere. El recálculo muestra la revisión anterior y exige motivo. Confirmar invoca POST `/costs/calculations` y abre el resultado persistido con su revisión, corte y limitaciones. No genera revisiones al filtrar o abrir una consulta. Este flujo pertenece a US1 y usa el núcleo de perfil preparado con fixtures sintéticos antes del editor completo de US3.

**Crear/Actualizar contraste**: `ComparisonActions.tsx` permite seleccionar revisiones compatibles de cálculo y boleta, revisar sus referencias y confirmar POST `/costs/comparisons`. Muestra la comparación persistida, sus exclusiones y versiones. Guardar/corregir una boleta no crea el contraste automáticamente: conserva el anterior y ofrece crear el del nuevo par explícitamente. Una selección histórica permanece identificada como histórica aunque se compare hoy.

Ambas acciones conservan entradas ante error, impiden envíos duplicados mientras hay una solicitud en curso y reutilizan `Idempotency-Key` al reintentar la misma operación; cambiar cuerpo o confirmar una operación nueva usa otra clave. Tras recargar, recuperan resultados mediante GET y referencias estables. El Operador consulta sin estos controles y el servidor deniega las mutaciones.

**Suministro**: al abrir el editor, GET `/costs/supply` obtiene configuración/ETag; 404 habilita alta con `If-None-Match: *`. Una edición usa `If-Match` del ETag leído; 412 conserva entradas, informa del conflicto y exige revisar el estado actual antes de otra confirmación. GET/PUT recuperan la revisión vigente tras recarga.

**Perfil**: el editor muestra el calendario completo de la revisión y sus segmentos. Crear una revisión copia el calendario elegido para que puedan cerrarse vigencias abiertas o corregirse segmentos anteriores sin modificar la revisión original. Distinguir borrador guardado y revisión publicada seleccionada; enviar `expected_previous_version_id` obtenido de GET perfiles. Un 409 exige revisar la última revisión antes de confirmar otra publicación.

El núcleo de validación/perfil ya existe para aceptar US1 con datos sintéticos; US3 entrega su administración completa. La interfaz no sustituye la autorización de servidor.

## Estados y comprensión

Distinguir espera, lista vacía, período sin registros, fuente ausente, resultado limitado, error y datos disponibles. Errores no sustituyen el último dato válido por una fila de ceros. Controles con etiquetas, foco/teclado y mensajes funcionales; tablas acompañan gráficos y conservan unidades/períodos.

SC-006 requiere diez tareas con personas representativas: identificar cálculo, facturado comparable, período y diferencia; nueve sin ayuda en <=2 minutos. Una suite de interfaz no reemplaza esos resultados humanos.
