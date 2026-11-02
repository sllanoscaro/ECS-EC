# Contrato de interfaz: historial agrupado

Ampliación de [UI 001](../../001-visualizar-consumo-categorias/contracts/ui.md) en
`/consumption/`. [HTTP](http.md), [modelo](../data-model.md). Frontend estático,
datos privados mediante API autenticada, español y zona del edificio.

## Selección y correspondencia

Añadir selector `Detalle | Hora | Día | Mes | Año`. El estado inicial conserva Detalle
de 001; las cuatro opciones nuevas usan el GET agrupado. Cambiar agrupación, categoría
o representación conserva inicio/fin y zona, salvo edición explícita del período.
El período inicial global sigue viniendo del catálogo 001, no de cada serie.

Una respuesta inmutable alimenta gráfico y tabla. La clave de petición incluye categoría,
inicio, fin, zona y granularidad; usar generación/abort y descartar respuestas antiguas,
incluso si llegan después de error/reintento. Una nueva selección válida invalida los
valores visibles de la anterior; el borrador inválido conserva la última consulta válida.

Encabezado común identifica categoría, agrupación, período exacto, kWh, zona/offsets y
corte. Enumerar los bloques recibidos sin reagrupar ni calcular energía en navegador.
Gráfico de barras independientes con valor exacto accesible y tabla con límites,
consumo disponible, cobertura, estado temporal y procedencia. La tabla y tooltip usan
el mismo formateador Decimal de 001; no pasar cifras de negocio por `Number`.
Las dos ocurrencias de una hora repetida muestran offset y límites distintos.

## Estados, ausencia y cobertura

| Dato / estado | Presentación |
| --- | --- |
| Carga | Indicador vinculado a la selección actual, sin cifras de otra consulta. |
| Bloque completo | Consumo y cobertura del 100 %, según `coverage_state` exacto. |
| Bloque incompleto | Consumo disponible, porcentaje y texto de falta de cobertura; no escalarlo a consumo total. |
| Bloque sin datos | Texto “Sin datos”, cobertura 0 %, consumo “—”; hueco en gráfico sin barra de cero. |
| Cero medido/calculado | `0 kWh` visible con su cobertura real; marcador de cero distinguible del hueco. |
| Período en curso | Etiqueta “En curso” además de cobertura respecto de la duración total del bloque. |
| Período futuro | Etiqueta “Aún no iniciado” para `not_started`; mantener bloque/filtro, energía ausente y cobertura cero si no hay contribuciones. |
| Sin medidor | Conservar estado 001, categorías navegables y bloques sin energía si corresponden. |
| Sin bloques contenidos | Explicar que ningún bloque cabe completo en el filtro; mantenerlo sin ampliarlo. |
| Error | Mensaje saneado y Reintentar para selección vigente; otra categoría sigue consultable. |

El texto de porcentaje sigue la clasificación exacta del servidor: si redondea a 100
pero `coverage_state=incomplete`, mostrar “<100 %” y detalle de duración faltante.
No etiquetar completo por redondeo. Estado se comunica con texto, además de color.
La situación temporal usa el corte de la respuesta: antes del inicio es “Aún no iniciado”,
exactamente desde el inicio es “En curso” y desde el fin es “Terminado”. Ambas vistas
aplican esas mismas fronteras; la cobertura se presenta independientemente del estado.

Avisar bloques descartados por extremos del filtro y mediciones excluidas por cruce
de límites. Explicar por qué hora y día pueden sumar valores distintos sin introducir
prorrateos. Señalar inicio de operación, ausencia de historia y detalle retirado cuando
la evidencia lo indique; conservar valor/cobertura histórica protegidos del agregado.

## Procedencia CAT-01

Mantener “Total medido” o “Total calculado de las categorías presentes”, con base/fuentes
y alcance identificables por segmento cuando cambian. No volver a sumar parciales,
reconstruir con base actual ni presentar calculado como lectura física.
La cobertura temporal completa de una base parcial no implica todas las cargas del edificio.

Diagnósticos de faltantes, cambio de configuración y pendiente de incorporación conservan
sus mensajes 001. Pendiente no tiene valor numérico hasta su incorporación; la acción
Actualizar consulta el estado confirmado sin adelantar el trabajo interno.

## Acceso y verificación

Sesión/expiración/permisos provienen de 006. Limpiar datos al cerrar/vencer sesión;
sin localStorage privado ni API/build público con historial. No crear controles de
edición de lecturas, reloj, recepción o purga en esta pantalla.

Controles y reintento accesibles por teclado, tabla semántica, nombre/descripción de
gráfico, valores exactos por foco/tooltip y avisos legibles. Reutilizar marcadores 001
para un solo bloque, todos ceros y positivos inferiores a un píxel.

Playwright compara valores/límites/estados de ambas vistas contra la respuesta real,
incluye carrera de selección y navegador en otra zona. SC-005 requiere diez tareas
con personas representativas y >=9 correctas sin ayuda en <=60 segundos, identificando
categoría, agrupación, consumo, período y cobertura en ambas vistas. No acreditarlo
con pruebas automatizadas.
