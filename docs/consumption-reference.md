# Referencia propuesta: consulta de consumo

Estado: cuarta propuesta visual aprobada para integración por el usuario. Modo de la superficie: **Operate**. Implementada localmente en `/consumption/`; ver [ui-implementation.md](ui-implementation.md) para alcance y evidencia, sin declaración de aceptación integral.

## Objetivo

Facilitar la consulta de una categoría durante un período explícito, con los mismos datos en gráfico y tabla y una distinción visible entre cero medido, ausencia e incompletitud. Conserva la identidad de Electro Conforma documentada en [DESIGN.md](../DESIGN.md) y el panel plegable de la [referencia del dashboard](dashboard-reference.md).

## Propuesta

- Filtros en una sola fila: categoría, «Desde», «Hasta» y «Consultar». Por solicitud del usuario, se retiran «(exclusivo)», el selector de agrupación y la frase «Los filtros se aplican al gráfico y a la tabla».
- Mantener las siete categorías seleccionables, incluso sin medidor. La imagen muestra CAT-01 seleccionada; no muestra el desplegable abierto.
- Los intervalos de quince minutos del ejemplo son lecturas de detalle, no una agrupación nueva ni garantía de frecuencia de adquisición. La retirada del selector corresponde a esta propuesta de interfaz; no elimina las consultas agrupadas existentes en el código o los requisitos de historial002. El rango de fechas selecciona el período y no determina por sí solo la escala de agregación. Su acceso debe resolverse al planificar la implementación, sin borrar capacidades de otra spec.
- Advertencia amarilla/ámbar de una sola línea: «Datos incompletos: Falta una lectura entre las 10:00 y las 10:15.». Se retira «Los intervalos sin datos no se interpretan como cero» y la anotación resaltada «Sin datos» con su corchete sobre el gráfico. Se conserva el hueco real y la leyenda neutral que diferencia ausencia de cero medido.
- Zona horaria una sola vez en el pie, a la derecha, junto a «Hora actual». El reloj representa el presente en la zona del edificio, no la hora del último dato ni el período histórico consultado. La hora de la imagen es ilustrativa. Esta disposición se comparte con el dashboard.
- Gráfico y tabla visibles juntos; se retiran el selector de representación, la etiqueta «Total medido» del encabezado y la frase «Detalle de lecturas…». La columna «Origen» conserva la identificación medida/calculada de las filas.
- Reloj del pie gris, regular y sin icono. Sección activa del panel lateral con fondo `#4F9A17`, texto e icono blancos. Ambas reglas se comparten con las demás vistas.
- Cada categoría conserva un color fijo según [DESIGN.md](../DESIGN.md). CAT-01 se muestra en verde profundo `#0D4A37`, igual que el total del dashboard.
- Por solicitud del usuario, se elimina por completo el apartado «Procedencia y configuración». La tabla pasa directamente debajo del gráfico. Los detalles de fila se conservan; su contenido debe mantener la evidencia necesaria al implementar, sin restituir el apartado eliminado.
- El texto completo del aviso amarillo, incluido «Datos incompletos:», usa peso regular, sin negrita. Se mantienen fondo amarillo, borde ámbar e icono triangular.

## Artefactos

- [Imagen actual, versión 4](../.impeccable/mocks/consumption-v4.png) y [prompt exacto](../.impeccable/mocks/consumption-v4.json), editada con la herramienta integrada `image_gen`.
- Versión anterior conservada: [imagen 3](../.impeccable/mocks/consumption-v3.png) y [prompt](../.impeccable/mocks/consumption-v3.json).
- Versión anterior conservada: [imagen 2](../.impeccable/mocks/consumption-v2.png) y [prompt](../.impeccable/mocks/consumption-v2.json).
- Primera propuesta conservada: [imagen](../.impeccable/mocks/consumption-v1.png) y [prompt](../.impeccable/mocks/consumption-v1.json).

La muestra comprende 2 de noviembre de 2026, de 08:00 a 12:00, en America/Santiago, UTC−03:00. Tiene quince lecturas válidas, incluyendo un cero a las 08:30, y un vacío entre 10:00 y 10:15. Todos los datos son ilustrativos. La maqueta enseña solo cuatro filas para evaluar densidad y jerarquía: «Vista parcial de la tabla» es una anotación de la propuesta, no una nueva regla de paginación.

## Reglas a preservar al implementar

Referencias: [historias de consumo001](../specs/001-visualizar-consumo-categorias/spec.md), [historial002](../specs/002-registro-retencion-consumo/spec.md), [arquitectura](architecture.md) y [hoja de ruta](implementation-roadmap.md).

Los filtros deben conservar su precisión y límites `[inicio,fin)`. Un control de fecha legible debe seguir resolviendo zona y offset de forma explícita, incluidas horas repetidas o inexistentes. No forzar períodos diarios ni intervalos de quince minutos si los datos reales tienen otro alcance. El período inicial documentado cubre la historia disponible del edificio; el ejemplo acotado no reemplaza esa regla.

La etiqueta visible «Hasta» no cambia el contrato de fin excluido. La zona se concentra visualmente en el pie, pero los detalles de horas repetidas deben permitir distinguir offsets y los nombres accesibles deben conservar el contexto temporal. El reloj actual calcula su offset según su propia fecha; no se reutiliza su offset para interpretar mediciones históricas.

No generar filas cero para vacíos, unir huecos, prorratear intervalos excluidos ni redondear datos contractuales de forma destructiva. Gráfico y tabla deben partir de la misma respuesta. No presentar energía disponible como total completo ni inventar cobertura o totales que no provea o permita derivar el contrato.

Falta definir y revisar la adaptación móvil, el detalle de fila y los estados de carga, error/reintento, sin datos, sin medidor, total calculado y procedencia mixta. La revisión de imagen no acredita validación de esos estados ni implementación o aceptación funcional. Las mejoras futuras deberán comprobarse en navegador con las fuentes y pruebas de sus módulos propietarios.

Refinamiento de Consumo: el botón «Actualizar» usa el icono y el estilo del dashboard, y queda deshabilitado durante la consulta. Las opciones de categoría muestran identificador y nombre, sin sufijos de disponibilidad. El tooltip flota sobre el gráfico y presenta energía con un decimal seguida de la hora local de fin (HH:MM:SS), sin añadir una medición bajo el gráfico. Las cifras visibles de energía y de la escala usan un decimal; la escala reserva ancho para sus etiquetas y usa notación científica con un decimal ante magnitudes extremas. No se alteran los valores de origen ni la geometría. La tabla presenta separadores con la fecha local al cambiar de día (según el inicio del intervalo); Inicio y Fin muestran sólo HH:MM. Los títulos de celda y los detalles de procedencia conservan instantes completos, offsets y valores originales.

Los filtros mantienen un borrador local: cambiar categoría o fechas no modifica la consulta mostrada hasta pulsar «Consultar». «Actualizar» repite la selección ya aplicada. Desde/Hasta muestran precisión de minutos; los límites exactos originales se conservan si no se editan, y editar un límite fija sus segundos a cero con resolución explícita de horas repetidas. Se retira «Corte» del panel de valores. Cada respuesta nueva vuelve a dibujar la serie con la animación del dashboard y su alternativa de movimiento reducido.

La franja común de métricas muestra máximo, media aritmética por intervalo (por bloque en consultas agrupadas), mínimo, suma del consumo registrado y cantidad de intervalos/bloques con datos. Todas proceden de los mismos valores de gráfico/tabla y se recalculan sólo para la selección aplicada. Ceros válidos participan; valores nulos no se sustituyen por cero ni entran en el divisor de la media. Sin valores se muestran guiones y cuenta cero. La suma describe únicamente evidencia disponible, sin extrapolar huecos; la media no se pondera por duración y no implica potencia promedio. Los cálculos decimales conservan todos los dígitos de origen y margen para acarreos antes de redondear la presentación a un decimal.

Refinamiento de textos: título «Consumo energético», introducción «En esta sección, puedes consultar el registro histórico del consumo eléctrico del edificio» y gráfico «Consumo energético en el intervalo solicitado». Se elimina la explicación visible bajo las métricas y se ordenan máximo, mínimo, media, consumo acumulado e intervalos con datos. Las reglas de cálculo anteriores permanecen vigentes. El detalle de Origen muestra fecha y hora local legibles sin huso horario; los elementos `time` conservan el instante original, offset y fracciones en sus atributos.
