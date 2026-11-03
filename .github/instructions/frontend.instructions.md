---
applyTo: "frontend/**/*.{ts,tsx,css}"
---

# Reglas para las interfaces de ECS-EC

Estas instrucciones complementan `AGENTS.md`, `docs/architecture.md`, `docs/implementation-roadmap.md` y la constitución de Spec Kit. No reemplazan contratos de las specs.

- Trabajar con el stack real de `frontend/package.json`: Next.js 16 App Router, React 19, TypeScript y CSS. Revisar Context7 y la documentación instalada antes de aplicar patrones sujetos a versión.
- Mantener `output: "export"` en `frontend/next.config.ts`; FastAPI sirve los archivos exportados. No introducir SSR dinámico, Server Actions, rutas de API de Next para funcionalidades privadas ni un servidor Node obligatorio en producción.
- Los datos privados se consultan en tiempo de ejecución mediante la API FastAPI autenticada. No incluir mediciones, información financiera, sesiones ni datos de usuarios reales en HTML estático o assets públicos.
- Preservar contratos de API, permisos, flujos de sesión/CSRF y propiedad de módulos. Ocultar un botón según rol mejora la experiencia, pero nunca reemplaza la autorización del servidor.
- Para cambios de diseño, preferir tokens CSS y componentes compartidos frente a estilos dispersos. Introducir librerías visuales solo si aportan un beneficio claro y tras revisar el impacto de dependencias.
- Toda vista debe tener estructura semántica, etiquetas accesibles, navegación por teclado, foco visible y diseño adaptable a móvil, tablet y escritorio.
- Implementar y revisar estados de carga, vacío, error, sin permisos y cobertura incompleta donde correspondan; no mostrar ausencia de datos como consumo cero.
- Mostrar unidades explícitas (kWh para energía, kW para potencia, CLP para costos cuando corresponda), periodos, zona horaria y alcance del cálculo. Usar formato de lectura `es-CL` sin alterar los valores numéricos ni la precisión de los contratos.
- Las estimaciones BT4.3 y la distinción entre horario punta/fuera de punta deben respetar las reglas de dominio y respuestas del backend; la UI no crea fórmulas tarifarias alternativas.
- No inventar datos de producción para maquillar una pantalla. Si se usa una maqueta, rotular datos sintéticos y mantenerla separada del flujo autenticado.
- Acompañar los cambios visuales con pruebas pertinentes de componentes o E2E. Antes de cerrar, ejecutar `npm --prefix frontend run typecheck`, `npm --prefix frontend test` y `npm --prefix frontend run build`, o informar expresamente qué no se pudo ejecutar.
