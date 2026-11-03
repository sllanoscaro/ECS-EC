---
name: ecs-dashboard-reference
description: "Replicar la dirección visual del video Whole.Generative.UI.v5 de CopilotKit en el dashboard energético de ECS-EC; usar cuando pidan un dashboard parecido a la referencia, rediseño estético, comparación visual, tarjetas KPI, layout, sidebars, gráficos o iteraciones Playwright."
---

# Rediseño visual guiado por referencia

El objetivo es obtener **alta similitud visual** con el video enlazado en `docs/ui/copilotkit-dashboard-reference.md`, sin suponer que ECS-EC deba usar el framework CopilotKit ni integrar nuevas capacidades de IA.

## Procedimiento obligatorio

1. Leer `AGENTS.md`, `docs/architecture.md`, `docs/implementation-roadmap.md`, `docs/ui/copilotkit-dashboard-reference.md` y las instrucciones de `frontend.instructions.md`. Aplicar las skills `ecs-energy-ui` y `ecs-ui-validation` cuando estén disponibles.
2. Revisar el frontend **real** de la rama y el estado actual de sus pantallas; no inferir la UI local a partir de capturas antiguas o de la rama `main`. Consultar las specs propietarias de cualquier funcionalidad afectada.
3. **Inspeccionar la referencia antes de diseñar.** Abrir el video enlazado con Playwright MCP. Si el video se presenta en un elemento HTML `video`, usar `browser_evaluate` para consultar duración y buscar fotogramas representativos; después tomar capturas con `browser_take_screenshot`. Alternativamente extraer imágenes de un MP4 obtenido legítimamente con ffmpeg disponible. Consultar `docs/ui/copilotkit-dashboard-reference.md` para fallback y evidencia.
4. Registrar composición observada de navegación, colores, tipografía, espaciado, tarjetas, gráficos, panel contextual, interacciones y movimientos. Etiquetar por separado lo inferido de fotografías complementarias. Documentar la inspección en `docs/ui/copilotkit-frame-notes.md`.
5. Priorizar **semejanza estructural real** sobre una paleta parecida: shell, densidad, anchos, agrupación, jerarquía y apariencia de tarjetas/gráficos. Crear tokens de diseño CSS y componentes compartidos; no improvisar estilos aislados para cada pantalla.
6. Diseñar primero un dashboard piloto que respete consumo real (kWh), demanda máxima (kW), periodos, cobertura, permisos, estados de consulta y rutas existentes. Reutilizar componentes del módulo, sin cambiar el backend o sus APIs ni añadir datos de demostración a producción.
7. Ejecutar una ronda de comparación visual lado a lado: screenshots en **1440 × 900**, **768 × 1024** y **390 × 844**, en condiciones equivalentes de contenido y sesión. Identificar las cinco diferencias más notorias respecto de la referencia y corregirlas. Repetir al menos una vez si el entorno lo permite.
8. Verificar accesibilidad, foco, contraste, responsive, `prefers-reduced-motion`, `typecheck`, tests y build. E2E auténticos solo con backend y fixtures legítimos; indicar explícitamente qué no se pudo comprobar.
9. Antes de finalizar describir evidencia visual concreta (timestamps o screenshots), cambios realizados y problemas pendientes. No afirmar haber visto el video, validado mediante Playwright o alcanzado similitud exacta sin evidencias.

## Restricciones inviolables

- Mantener Next.js App Router exportado estáticamente (`output: "export"`) y servirse en FastAPI. No SSR dinámico ni Server Actions.
- Mantener identidad, autorización, CSRF, rutas, esquemas de API, valores decimales y medidas de privacidad.
- Usar Context7 si hace falta documentación de React/Next.js o bibliotecas, evitando nuevas dependencias no justificadas.
- Las referencias de CopilotKit son de **diseño**; no instalar `@copilotkit/*`, runtime de agentes, AG-UI ni un chat falso por el solo parecido visual.
- Si el video no está disponible, ser transparente y diseñar sobre las referencias secundarias señaladas; no atribuirles contenido no examinado del video.
- Si el usuario solicita únicamente un plan o preparación, no implementar pantallas de forma anticipada.

## Cierre requerido

Mostrar: qué se inspeccionó; decisiones estéticas derivadas; rutas y componentes cambiados; capturas comparadas; pruebas ejecutadas/no ejecutadas; pasos siguientes para aproximarse mejor a la referencia.
