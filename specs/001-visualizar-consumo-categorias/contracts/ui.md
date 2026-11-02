# Contrato de interfaz: Consumo

[Spec](../spec.md), [HTTP](http.md), [modelo](../data-model.md).
Páginas estáticas, datos privados por API autenticada; interfaz en español.

Estado de ejecución 2026-11-02: páginas/contenedor, consulta y administración conectados
a los proveedores reales 001/002/006. [Evidencia y escenarios pendientes](../validation/increment-2026-11-02.md).
La ruta administrativa implementada es `/administracion/consumo/`, integrada con las
páginas españolas de 006; sustituye la ruta de diseño `/administration/consumption/`.

## Consulta /consumption/

1. Ofrecer siete categorías con nombres del catálogo, seleccionables aunque carezcan de
   medidor/datos. Selección inicial CAT-01; no deducir instalación del número de lecturas.
2. Mostrar selector de categoría, inicio/fin en la zona del edificio, acción Consultar,
   Actualizar/Reintentar y gráfico/tabla. Período inicial global del catálogo; conservar
   período al cambiar categoría o representación. No cambiarlo a la extensión de cada serie.
3. Encabezado común: categoría, energía eléctrica en kWh, inicio/fin de consulta, zona IANA
   y offsets. Ambas vistas identifican intervalos, incluido el extremo final exclusivo.
4. CAT-01: "Total medido" o "Total calculado de las categorías presentes" y base enumerada.
   Si cambia origen/base dentro del período, mostrarlo por segmento/fila. Base parcial
   advierte que no garantiza cubrir todas las cargas del edificio; no conciliación automática.
5. SVG de barras/segmentos independientes con cada intervalo y su valor exacto accesible
   mediante foco/tooltip. Tabla HTML con inicio, fin, kWh y procedencia; detalle de origen
   o contribuciones sin ocultar el valor principal. Mismos registros/orden/valores del objeto
   de respuesta. Un único intervalo es visible. No unir ni rellenar huecos.

La tabla tiene encabezados semánticos y el gráfico nombre/descripción accesibles; selección
y reintento operables por teclado. Estado/avisos usan texto, además de color. Un único
formateador decimal sirve tabla, tooltip y etiqueta accesible; no `Number(value).toFixed`.
Proyección con `decimal.js` y coordenadas acotadas, sin recalcular totales de negocio.
Si un positivo tiene altura inferior al píxel, mostrar marcador de positivo y cifra exacta;
el cero tiene marca propia. Si todos los valores son cero, mantener escala/intervalos visibles.
Instantes conservan microsegundos textuales, aunque la proyección geométrica sea aproximada.
Presentar íntegramente el mínimo `0.000000000000001 kWh`, el máximo individual y el total
de seis máximos sin aplicarles el mismo techo. Los valores exactos siguen siendo cadenas.

## Período y estados

El formulario conserva borrador separado de última selección válida. Inicio >=fin, fecha
inexistente u offset inválido muestran corrección sin perder la consulta válida. Una hora
repetida exige seleccionar/describir su offset; no convertirla silenciosamente. No cambiar
la zona del edificio por la del navegador. Mostrar aviso si se excluyen intervalos cruzados.

| Estado | Presentación común a ambas vistas |
| --- | --- |
| Carga | Indicador vinculado a categoría/período actuales; sin cifras de otra petición. |
| Disponible | Datos recibidos o calculados incorporados; cero explícito sigue siendo dato. |
| Sin medidor | Categoría parcial sin fuente en todo el período; sin ceros ni filas ficticias. |
| Sin datos | Fuente sin lecturas contenidas o CAT-01 sin base, con motivo; mantener categorías navegables. |
| Datos incompletos | Aviso de faltantes, incorporación pendiente o cambio de configuración calculada; cada motivo tiene texto propio. Filas válidas separadas de diagnóstico, sin valores inventados. |
| Error | Mensaje saneado y Reintentar para la selección actual; otra categoría sigue consultable. |

La ausencia de lecturas de CAT-01 física se presenta como "Sin datos", sin suma sustituta.
Una base vacía muestra "Sin datos: no hay categorías presentes para calcular el total".
Los huecos conocidos se ven como espacios temporales; la tabla solo contiene datos válidos.
Un diagnóstico `calculation_configuration_changed` muestra "Cambió la configuración de
cálculo dentro del intervalo", con modo/base y fuentes por segmento; no inventa categorías
faltantes ni fecha de próxima incorporación. Las parciales válidas siguen consultables.

Cada petición se asocia a clave categoría/inicio/fin/zona y una generación. Al cambiar una
selección válida, invalidar resultados actuales inmediatamente, abortar solicitud anterior
y descartar toda respuesta con clave/generación antigua, incluso tras error/reintento.
Alternar gráfico/tabla usa la misma respuesta. No guardar datos privados en localStorage
ni mantenerlos tras cierre/vencimiento de sesión. 401/403 usan el flujo común de 006.

## Administración /administracion/consumo/

Solo Administrador técnico con permiso actual; navegación y protección del layout son
de 006, formulario de consumo de 001. Listar siete categorías fijas con presencia y
origen/etiqueta; zona y vigencia inicial explícitas, base CAT-01 derivada y revisable.
No exigir medidor total ni siete medidores. En modificaciones usar vigencia de servidor
y revisión esperada, mostrar efectos futuros sin cambiar historia; conflicto pide recargar.
Explicar qué categorías cambian realmente de fuente/presencia o base; una etiqueta o un
cambio ajeno no invalida las lecturas de otra categoría. La comprobación de historia para
modificar es atómica con recepción; si no está disponible, mostrar el error y conservar
la configuración. Revisiones globales y de categoría son datos de servidor, no editables.
No mostrar destinos/credenciales SFTP ni permitir modificar mediciones. Operador no puede
leer ni escribir esta configuración mediante navegación o URL/API directa.

## Validación

Playwright verifica identidad de intervalos/cifras contra fixtures, transiciones de estado,
carreras A→B, reintento, teclado y zona distinta del navegador. Diez tareas con personas
representativas evalúan SC-005: al menos nueve sin ayuda en <=60 s; un test automatizado
no acredita ese criterio. Acceso externo/VPS y servicios locales siguen la guía de
[quickstart](../quickstart.md), con resultados pendientes hasta ejecución real.
