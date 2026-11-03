---
name: ecs-energy-ui
description: "Diseñar y mejorar pantallas, dashboards, navegación y componentes React/Next.js de ECS-EC. Usar al trabajar en experiencia de usuario, diseño visual, tablas, gráficos, tarjetas KPI o formularios de consumo eléctrico, costos BT4.3 y administración."
---

# Diseño de interfaces de ECS-EC

## Objetivo

Crear interfaces coherentes, legibles y accesibles para el monitoreo energético de edificios, respetando el MVP, las especificaciones y los contratos existentes. Trabajar únicamente en la UI solicitada: no completar funcionalidades de backend pendientes por iniciativa propia.

## Antes de diseñar

1. Leer `AGENTS.md`, `docs/architecture.md`, `docs/implementation-roadmap.md` y la spec propietaria del área que se va a modificar.
2. Inspeccionar `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx`, `frontend/src/components/identity/Navigation.tsx` y los componentes existentes de la pantalla objetivo.
3. Verificar si la pantalla es pública, de operador o de administrador técnico, y cuáles acciones/estados dependen de permisos o de la API.
4. Cuando una API de Next.js, React o una librería resulte dudosa, consultar Context7 para la versión instalada, sin ignorar la restricción de exportación estática.

## Proceso de diseño

1. Inventariar la pantalla actual: jerarquía, tareas frecuentes, navegación, densidad de información, problemas de responsive y accesibilidad.
2. Proponer una dirección visual concreta antes de hacer un rediseño extenso: jerarquía tipográfica, espaciado, paleta sobria, superficies, bordes, foco y densidad de datos. No inventar una identidad de marca aprobada.
3. Definir tokens CSS reutilizables (color, texto, spacing, radio, sombras, estados) y patrones compartidos para contenedores, encabezados, filtros, tarjetas KPI, formularios, tablas y avisos. Preservar el estilo de la aplicación cuando exista una decisión previa.
4. Implementar de forma incremental en TypeScript y React con HTML semántico. Mantener formularios y componentes de navegación accesibles, sin depender exclusivamente del color.
5. Para dashboards, priorizar el recorrido «resumen → tendencia → desglose → detalle» y mostrar contexto del período, categorías y unidades; no decorar por decorar.
6. Para gráficos, incluir rótulos, ejes/unidades, leyenda accesible, interpretación textual cuando sea necesario y alternativa tabular. Evitar representar series parciales o sin mediciones como valores cero.
7. Prever carga, ausencia de datos, cobertura incompleta, errores, permisos insuficientes y sesiones vencidas. Evitar flash de información privada en la exportación estática.
8. Revisar 390 px, 768 px y 1440 px: navegación, scroll horizontal de tablas, superposición de elementos, legibilidad de gráficos y foco por teclado.
9. Verificar con la skill `/ecs-ui-validation` si está disponible, además de las pruebas del repositorio.

## Reglas de dominio

- Los datos de energía se expresan en Wh/kWh según el contrato; la demanda/potencia en W/kW según contrato. Nunca intercambiar energía y potencia en rótulos.
- Mostrar zona horaria, fecha y período con claridad; respetar el tratamiento de UTC y `America/Santiago` configurado para el entorno, sin suponer que la zona local del navegador es la del edificio.
- Distinguir medición observada, estimación, dato pendiente y dato sin cobertura.
- El RIC N.º 14 y las categorías de consumo requieren trazabilidad; un estado visual no demuestra por sí solo cumplimiento normativo.
- Los importes y proyecciones BT4.3 son estimaciones o cálculos del backend según sus contratos; no inventar tarifas ni cifras.

## Entrega

Al terminar, informar las pantallas/components modificados, las decisiones visuales, cómo se preservaron los contratos, qué se probó y las limitaciones pendientes. Si la tarea pide solo evaluación, entregar un diagnóstico priorizado sin modificar archivos.
