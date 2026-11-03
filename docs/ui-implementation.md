# Integración local de dashboard y consumo

El usuario aprobó integrar las referencias [dashboard versión 5](../.impeccable/mocks/dashboard-navigation-v5.png) y [consumo versión 4](../.impeccable/mocks/consumption-v4.png). Se implementaron en `/` y `/consumption/`, manteniendo los activos y criterios de [DESIGN.md](../DESIGN.md).

## Cambios

- Panel lateral compartido con permisos actuales, ruta activa en verde `#4F9A17` e icono/texto blancos, plegado de escritorio y menú móvil accesible por teclado. Login sin retorno explícito abre el dashboard; la renovación obligatoria sigue abriendo cuenta.
- Logos SVG originales en `frontend/public/brand/`, copiados de `docs/Identidad Visual Electro Conforma/`. No se rasterizan controles ni texto de la interfaz.
- Tipografía Geist regular autoalojada, distribuida en el paquete Next instalado; licencia SIL OFL y copyright de sus metadatos en `frontend/public/fonts/LICENSE-Geist.txt`. La negrita utiliza síntesis del navegador.
- Dashboard diario autenticado con resumen, serie de quince minutos, categorías y reloj del edificio. El servidor calcula energía y cobertura con cantidades exactas; el navegador utiliza los decimales únicamente para etiquetas y proporciones gráficas. El [contrato de dashboard001](../specs/001-visualizar-consumo-categorias/contracts/dashboard.md) explica límites, fórmulas y errores.
- Refresco cada 60 segundos tras terminar una consulta; el próximo horario no promete llegada de lecturas. Las consultas automáticas llevan actividad de sesión `background`.
- Consumo con controles nativos de fecha/hora, gráfico y tabla simultáneos, datos incompletos en ámbar sin negrita y errores en rojo. El panel «Procedencia y configuración» se retiró. La evidencia exacta de origen, unidad, instante, revisión y base calculada permanece en los detalles de fila.
- Zona y reloj se muestran una vez en el pie. El offset del reloj actual no se reutiliza para interpretar fechas históricas; las horas repetidas ofrecen selección explícita de offset y las inexistentes se rechazan sin cambiar la consulta válida.
- Colores de categorías centralizados en `frontend/src/lib/visual.ts`; se conserva el cero real, el vacío y el marcador de valores positivos inferiores a un píxel. La tabla móvil conserva columnas y valores, sin desbordar la página.

Los DTO y consultas agrupadas existentes siguen disponibles. El selector principal se retiró por petición del usuario; un enlace explícito como `/consumption/?escala=hour` conserva la consulta agrupada (hour/day/month/year) sin añadir el control eliminado al panel. No se modifica el período inicial de historia definido por el catálogo.

## Verificación

- Frontend: 55 pruebas, comprobación de tipos y exportación estática de Next.js.
- Backend: 74 pruebas unitarias de consumo y siete pruebas de API/contrato sobre PostgreSQL18 temporal, incluyendo el dashboard nuevo, identidad real y lectura sin cambios de conservación.
- Chromium: diez escenarios de dashboard/consumo, con escritorio1440px y móvil390px, variantes sin datos/sin medidor/incompletas/error y consulta agrupada. Sin excepciones JavaScript ni desbordamiento de página en las capturas. Comprobados plegado/expansión de escritorio, apertura/Escape en móvil y colores calculados del enlace activo.
- Detector de Impeccable: sin hallazgos deterministas. No sustituye la inspección visual ni acredita accesibilidad completa.

Capturas locales y resultados: `frontend/test-results/ui-implemented-final/`. Los datos de esas capturas están interceptados exclusivamente dentro de Playwright; la aplicación de producción no incluye fixtures. La consulta HTTP nueva se validó separadamente con PostgreSQL e identidad reales. Esto no acredita una validación visual integral sobre una instalación real ni aceptación con personas/VPS.

Para reproducir la revisión, iniciar `npm run dev -- --hostname 127.0.0.1` desde `frontend/` y ejecutar en otra terminal:

```sh
UI_REVIEW_FILTER='^(inicio|consumption)-' npm run review:views -- test-results/ui-review-new
```

La vista normal requiere la API del monolito autenticada. Next dev por sí solo sirve la interfaz, pero no reemplaza FastAPI. El despliegue conserva la exportación estática servida por Uvicorn y no añade un servidor Node de producción. No se cambiaron la funcionalidad seleccionada por Spec Kit, tareas/checklists, módulos de costos ni su maqueta pendiente.
