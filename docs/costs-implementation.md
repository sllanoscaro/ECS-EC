# Integración de Costos

Modo: **Operate**. El usuario aprobó la [propuesta versión 2](../.impeccable/mocks/costs-v2.png) y pidió integrarla en el código. Extensión de la identidad existente; no crea una dirección visual nueva. Referencias de autoridad: [DESIGN.md](../DESIGN.md), los estilos y activos compartidos y la implementación de Dashboard y Consumo.

## Contrato de la superficie

- **Forma y composición:** navegación compartida, filtros compactos de ciclo/revisión, resumen de tres columnas, gráfico circular con leyenda y tabla exacta como foco; debajo, desglose y contraste de boleta. Historial y procedencia desplegables. Se hereda la estructura aprobada sin ronda de conceptos nueva.
- **Tipografía y material:** Geist autoalojada, fondo claro, paneles blancos con borde fino, colores de marca y colores estables por categoría. Sin imágenes dentro de la interfaz: logo SVG original y gráfico SVG semántico. No hay activos raster que reproducir.
- **Primer viewport:** seleccionar un ciclo y reconocer el cargo de energía, el costo completo o subtotal disponible y su reparto estimado. Los valores completos de cada categoría acompañan al gráfico.
- **Interacción:** los selectores son borradores hasta «Consultar»; cada consulta abre una revisión persistida, sin crear cálculos ni contrastes. «Actualizar» vuelve a consultar la revisión activa. Historial conserva filtros, paginación y acceso a contrastes históricos. La navegación y sus animaciones existentes se conservan.
- **Adaptación:** móvil apila filtros, resumen y paneles; tabla de categorías mantiene nombre, porcentaje y CLP. Los controles y textos son HTML accesible; el gráfico tiene alternativa tabular. La cabecera y tipografía heredan sus dimensiones del código existente, aunque la imagen generada las comprima.

## Reparto estimado autorizado

`GET /api/v1/costs/calculations/{calculation_id}/distribution` requiere `costs.read` y `consumption.read`, devuelve `no-store` y no modifica datos. La consulta usa una transacción `REPEATABLE READ READ ONLY` y el puerto existente `read_report_snapshot` de consumo001/002. No añade fuentes, almacenamiento de consumo ni un motor tarifario alternativo.

El servidor reparte únicamente los componentes netos de energía disponibles. Demanda, transmisión, cargo fijo, servicio público, otros cargos e impuestos permanecen fuera. Los importes proporcionales se redondean mediante restos mayores a la precisión decimal del cargo presentado, conservando exactamente su suma; los porcentajes conservan 100,00 %. Los empates se resuelven por orden de categoría. No se asume ninguna tarifa real ni tasa tributaria en la aplicación.

La base general debe coincidir en identidades/revisiones con las mediciones físicas capturadas del cálculo y cubrir el ciclo entero. Cada categoría medida requiere cobertura completa sin diagnósticos, cruces ni detalle retirado. Las categorías sin medidor mantienen su ausencia y el remanente del suministro general se muestra como «Sin asignar», sin normalizar artificialmente los parciales al 100 %. Un cero medido se conserva. Base general cero, parciales superiores al total, energía con impuestos incluidos o evidencia incompleta no producen porcentajes ni importes ficticios.

Esta estimación es una consulta transitoria de las categorías disponibles del mismo ciclo; tiene su propio corte visible y puede cambiar al actualizar. No se incorpora al snapshot financiero, ni se ofrece como reproducción histórica o cargo facturado por categoría. Los cálculos y contrastes persistidos conservan su significado. La ampliación responde a la petición expresa del usuario y no acredita cierre de tareas de Spec Kit ni validación tarifaria.

La [preparación operativa de la demo](costs-demo.md) documenta la posterior habilitación del suministro, perfil ilustrativo, medición física simulada, primer cálculo y boleta. La ausencia inicial de esa configuración era una limitación de la instalación, adicional a las pruebas aisladas descritas abajo. La consulta vacía ahora diagnostica requisitos mediante `GET /costs/readiness` y ofrece acciones según permisos.

## Verificación local

- Backend: 37 pruebas unitarias de costos y 21 pruebas de API/integración sobre PostgreSQL18 temporal aislado. Incluyen reparto exacto, ceros, falta de cobertura, ausencia de medidor, residuo, discrepancias y consulta autorizada sin cambios en cálculos ni conservación.
- Frontend: 84 pruebas, comprobación de tipos y exportación estática de Next.js. Se corrigió la expectativa desactualizada del título de Dashboard en una prueba existente; no se cambió ese título.
- Chromium: 16 escenarios de escritorio de 1440 px y móvil de 390 px, sin errores ni desbordamiento horizontal, con muestra completa, incompleta, vacía, fallos, sin medidor, contraste pendiente e histórico. Fuentes: `frontend/scripts/review-costs.mjs` y `frontend/test-results/costs-integrated/results.json`. Datos interceptados exclusivamente en el navegador; la API se prueba aparte con datos reales de prueba.

La revisión visual independiente comparó la comp aprobada con las capturas completa de escritorio y móvil, incompleta de escritorio, sin medidor y desplegables en móvil: `disposition: ship`, sin `material_fixes`. El resultado comprende la integración visual local como extensión de la identidad existente, sin nuevos tokens.

Las capturas usan fixtures solo en el navegador; las pruebas de API sobre PostgreSQL constituyen evidencia separada. Estos resultados no acreditan instalación ni validación con tarifas reales, personas o VPS, ni aceptación total de la spec004.
