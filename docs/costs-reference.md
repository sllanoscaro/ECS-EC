# Referencia propuesta: consulta de costos

Estado: primera propuesta visual, pendiente de revisión del usuario. Modo: **Operate**. No se modificaron las interfaces ni las reglas de cálculo.

## Objetivo y alcance

Consultar un ciclo real del suministro general BT4.3 y su revisión persistida; entender qué componentes están disponibles y contrastar conceptos compatibles con una boleta. Corresponde a `/costos/`, con los permisos de consulta existentes. La configuración de suministro, calendarios y cargos, el cálculo/recálculo y la entrada/corrección de boletas permanecen en el ámbito administrativo; no se añaden a esta pantalla de consulta.

Fuentes: [historias y requisitos004](../specs/004-costos-tarifa-bt43/spec.md), [arquitectura](architecture.md), [hoja de ruta](implementation-roadmap.md), los componentes de `frontend/src/components/costs/` y la [revisión inicial](ui-review.md). Conserva la identidad y las reglas compartidas de [DESIGN.md](../DESIGN.md).

## Composición

1. Selección compacta del ciclo de consumo real y revisión; estado temporal explícito. No reemplazar el ciclo de la boleta por el mes calendario de emisión.
2. Advertencia amarilla concisa cuando falta evidencia para completar el cálculo.
3. Resumen con subtotal disponible y costo completo; la falta de un total completo no se representa como cero.
4. Desglose a la izquierda, con concepto, base, precio, importe y pequeñas barras proporcionales integradas en la tabla. Los conceptos no calculables no tienen barras ficticias.
5. Contraste con boleta a la derecha: revisiones elegidas, base compatible, importes comparables y diferencia; el total a pagar del documento queda separado.
6. Bases de cálculo y procedencia en detalle desplegable; historial por ciclos debajo, con acceso a revisiones conservadas.

La navegación activa usa fondo `#4F9A17`, texto e icono blancos. El reloj del pie es gris, sin icono ni negrita. Las barras financieras representan conceptos del suministro general y utilizan un color uniforme: no corresponden a las siete categorías de energía, ni introducen una asignación distinta a los colores de esas categorías.

## Artefactos y muestra

- [Imagen de referencia](../.impeccable/mocks/costs-v1.png).
- [Prompt exacto y procedencia](../.impeccable/mocks/costs-v1.json), generada con la herramienta integrada `image_gen` tomando la referencia de consumo como sistema visual.

Datos y tarifas son exclusivamente ilustrativos, sin validez comercial o normativa. El ejemplo muestra un ciclo cerrado del 1 de octubre al 1 de noviembre de 2026, cálculo revisión 3, incompleto por falta de antecedentes de demanda. Ejecución completada, ciclo cerrado y suficiencia parcial son estados independientes.

Los cargos disponibles de energía, transmisión y fijo suman `100.000 + 8.000 + 2.000 = 110.000 CLP`. Demanda e impuestos no se presentan como calculables ni se incorporan como ceros. El costo completo permanece no disponible.

El contraste ilustrativo utiliza solamente los tres conceptos netos compatibles: calculado `110.000 CLP`, facturado `108.000 CLP`, diferencia calculado menos facturado `+2.000 CLP`, porcentaje mostrado `+1,85 %`. El documento tiene `130.520 CLP` a pagar, incluyendo impuestos y deuda anterior ajenos a esa base comparable. Esa comparación parcial no acredita que el costo completo coincida o difiera en la misma cantidad.

## Preservar al implementar

- BT4.3 requiere la medición física general CAT-01; no sustituirla por la suma calculada de categorías ni volver a cobrar las parciales.
- Leer las revisiones persistidas y el par exacto de cálculo/boleta. Cambiar filtros o abrir la vista no calcula, modifica tarifas ni crea contrastes automáticamente.
- No prorratear ciclos, mezclar bases tributarias, aplicar impuestos dos veces ni confundir energía en kWh con demanda en kW.
- Mantener conceptos netos e impuestos identificables. Un subtotal comparable y un subtotal disponible no son necesariamente iguales; solo coinciden en esta muestra.
- No equiparar un porcentaje de diferencia con ahorro o fallo del sistema. Si el facturado comparable es cero, el porcentaje no aplica.
- Conservar por separado fallos de consulta, ausencia de boleta, contraste pendiente, ciclo en curso, insuficiencia de evidencia y ejecución fallida.
- Mantener accesibles suministro y perfil, máximos históricos, reglas, fuentes documentales, corte, conservación y diferencias del punto de medición en el detalle de procedencia. El reloj actual no reemplaza el corte del cálculo.
- Al implementar, conservar acceso al historial completo y sus filtros/paginación según contratos. Las tres filas de la maqueta son una muestra, no un límite de conservación o consulta. La selección de revisiones históricas y los desplegables requieren diseño de interacción sobre las capacidades reales.

Faltan revisar la adaptación móvil, los detalles desplegados y los demás estados. Esta referencia no constituye pruebas funcionales, validación tarifaria ni aceptación de la spec004; su siguiente paso es recibir retroalimentación visual.
