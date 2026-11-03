# Referencia de dashboard: CopilotKit / Whole.Generative.UI.v5

**Objetivo:** orientar el rediseño del dashboard de ECS-EC a una composición visual muy próxima a la demo, conservando todas las reglas de dominio, seguridad, accesibilidad y despliegue del proyecto.

## Referencias, jerarquía de evidencia

1. **Video principal (prioridad alta):** https://github.com/user-attachments/assets/72b7b4f3-b6e7-460c-a932-5746fe3c8db3
2. **README de origen:** https://github.com/CopilotKit/CopilotKit — sección **What you can build**, video **Whole.Generative.UI.v5.mp4**.
3. **Referencia visual complementaria (no representa necesariamente un fotograma del video):** https://repository-images.githubusercontent.com/655515393/3299a492-753a-4726-ad71-ea5d268c6e79
4. **Referencia complementaria de dashboard con gráfico:** https://docs.copilotkit.ai/images/generative-ui/chat-plus-surface.png

**Estado de la inspección:** se verificó que el video está enlazado desde el README. No se pudo revisar directamente cada fotograma durante la creación de este brief; por tanto, las pautas que siguen son **hipótesis visuales derivadas de las referencias complementarias**, NO una transcripción exacta del video. El agente con acceso al navegador debe contrastarlas con el video antes de fijar valores y geometrías.

**CopilotKit ≠ GitHub Copilot CLI.** CopilotKit es una librería para aplicaciones que incorporan agentes; no debe instalarse en ECS-EC únicamente para reproducir su apariencia. El proyecto ya dispone de React, Next.js y CSS. NO integrar `@copilotkit/*`, AG-UI, A2UI, un runtime de IA ni un chat simulado, salvo que una especificación funcional independiente lo solicite.

## Protocolo obligatorio de extracción visual (antes de modificar componentes)

- Abrir el video con el MCP Playwright ya configurado, usando `browser_navigate`. Si la URL de asset no representa el video en un elemento accesible, abrir el README y ubicar la sección correspondiente.
- Mediante `browser_evaluate`, si hay un elemento `video`, leer su `duration`, pausar reproducción y posicionarlo en fotogramas representativos (ej. 10 %, 30 %, 50 %, 70 % y 90 %), esperando a que se haya completado el seek. Capturar con `browser_take_screenshot`. No asumir duración, contenido, fotogramas ni herramientas inexistentes.
- Si el browser no puede cargar o capturar el video, intentar obtener el MP4 mediante las herramientas locales permitidas y extraer fotogramas con ffmpeg **solo si ya está disponible**. No incorporar una dependencia audiovisual al frontend por esta tarea.
- Crear un inventario de lo **realmente observado**: estructura de la navegación, paneles laterales, ancho relativo de columnas, proporciones de tarjetas, colores dominantes, tipografía, espaciado, iconos, tipos de gráfico, estados interactivos y transiciones.
- Registrar el resultado en `docs/ui/copilotkit-frame-notes.md`: instante o porcentaje, composición visible, notas de jerarquía visual, colores/tamaños aproximados y evidencia/screenshot local si existe. Si el video no es accesible, anotar explícitamente el bloqueo y trabajar con referencias secundarias **etiquetadas como tales**. No declarar que se revisó visualmente el video si solo se abrió su URL.
- Las capturas con contenido de terceros pueden mantenerse como evidencia local y no es necesario incorporarlas al Git. Si se pretende versionarlas, revisar antes los derechos de uso y eliminar cualquier información privada.

## Dirección visual provisional para ECS-EC (por verificar con fotogramas)

- **Estética:** dashboard analítico claro, limpio, contemporáneo; superficies blancas sobre fondo gris muy tenue; acentos azul/violeta, secundarios turquesa/menta; títulos oscuros y metadatos discretos.
- **Composición:** shell de navegación bien estructurada, encabezado con título de página y período, resumen KPI en primera fila, gráficos prioritarios al centro, detalle tabular y filtros bien agrupados. Un panel lateral contextual puede inspirarse en la posición visual del asistente de la demo, pero **no simular un chat funcional** sin requerimientos.
- **Tarjetas:** esquinas redondeadas, bordes tenues, sombras discretas, espaciado consistente, números prominentes y microetiquetas. Las tarjetas deben ser útiles y no meros elementos decorativos.
- **Gráficas:** curva temporal de consumo/energía (con unidades y cobertura), comparación de demanda en punta/fuera de punta cuando esté disponible, distribución por categorías y costos BT4.3 en sus respectivas pantallas. Evitar instalar una librería solo para lograr un aspecto; reutilizar `EnergyChart`, `CostChart` y datos API existentes.
- **Tipografía:** sans serif legible, jerarquía clara, cifras tabulares, contraste suficiente, textos en español (`es-CL`), formatos de kWh, kW y CLP de acuerdo con contratos; fechas y zona explícitas.
- **Movimiento:** transiciones sutiles para revelar o filtrar contenido; respetar `prefers-reduced-motion`, no priorizar animación sobre precisión ni rendimiento.
- **Propuesta inicial de tokens (solo punto de partida a ajustar según el video):** fondo `#F6F8FC`, superficie `#FFFFFF`, texto `#1D2742`, acento `#716FF0`, secundario `#31BBAA`, borde `#E7EAF2`; radio 16–20 px; espacios de 8/12/16/24/32 px. **No presentar estos valores como extraídos del video.**
- **Adaptación:** a 1440 px preservar la jerarquía paneles/tarjetas; a 768 px apilar componentes secundarios; a 390 px priorizar KPIs, navegación accesible, gráficos legibles y tablas con desplazamiento controlado.

## Mapeo al dominio real (no inventar cifras)

| Zona del dashboard | Indicador / contenido de ECS-EC | Origen / cautela |
| --- | --- | --- |
| Encabezado | Edificio/periodo disponible, última lectura y estado | Solo si la API/contrato lo expone |
| KPIs | Energía acumulada (kWh), demanda máxima (kW), cobertura de mediciones | Consultas del módulo de consumo; sin datos = estado vacío, no cero |
| Gráfico principal | Serie temporal por intervalo y granularidad | Fuente del componente de consumo existente |
| Desglose | Categorías registradas RIC N.º 14 | Mostrar solo categorías y datos realmente disponibles |
| Costos | Estimación del período BT4.3 y componentes de costos | Respuestas del módulo costos; no recalcular tarifas en la UI |
| Contexto lateral | Filtros, explicación de unidades, estado de datos o acciones permitidas | Nunca presentar un bot inexistente como operativo |

## Plan de trabajo en iteraciones

1. **Comparar referencia y aplicación:** registrar fotogramas y capturas de pantallas actuales, identificando 5–10 diferencias visuales de mayor impacto.
2. **Fijar tokens y composición:** acordar o implementar una primera versión de variables CSS, shell, navegación, tipografía, tarjetas y layout sin alterar llamadas HTTP.
3. **Pantalla piloto:** rediseñar una única pantalla de consumo con datos reales, mocks sintéticos rotulados solo en una vista de desarrollo si hacen falta, estados completos y gráficos legibles.
4. **Validación visual:** capturar el resultado con Playwright MCP en 1440, 768 y 390 px; comparar lado a lado con la referencia y corregir densidad, proporciones, bordes, colores y jerarquía.
5. **Generalizar:** aplicar patrones visuales aprobados a costos, reportes y administración sin alterar permisos ni contratos.
6. **Regresión:** ejecutar `npm --prefix frontend run typecheck`, `npm --prefix frontend test`, `npm --prefix frontend run build` y, si el backend/fixtures lo permiten, E2E reales.

## Criterios de aceptación

- Se puede explicar qué aspectos fueron copiados visualmente de capturas reales, cuáles se adaptaron al dominio y cuáles son suposiciones pendientes.
- El resultado se reconoce como perteneciente a la misma familia estética por jerarquía, proporciones, componentes y ritmo visual, no solo por cambiar colores.
- Cada KPI y gráfico tiene etiquetas, unidades y estados honestos; no se revelan datos privados en el build estático.
- Se mantienen `output: "export"`, FastAPI, contratos, roles y accesibilidad.
- Se entregan capturas comparables y reporte de validación; no se declara similitud o pruebas que no hayan podido revisarse.
