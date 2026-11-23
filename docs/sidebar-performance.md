# Revisión del movimiento del panel lateral

El usuario autorizó revisar los avisos `layout-transition` del panel lateral. El cambio conserva la identidad, la duración de 240 ms, los anchos visibles, el plegado mediante el botón y la expansión al activar un icono, además de la interacción móvil existente. No altera contenido ni reglas de las vistas.

## Medición y resultado

Se midió la exportación estática de producción en Chromium local, con un dashboard sintético de 80 intervalos y siete categorías; seis cambios de estado por escenario tras un ciclo de calentamiento. Se compararon escritorio1440px y móvil390px, CPU normal y limitación4×. Las respuestas se interceptan solo en el script de pruebas y no forman parte de la aplicación.

| Escritorio | Antes: tiempo de layout por cambio | Después | Antes: recálculos por cambio | Después |
| --- | ---: | ---: | ---: | ---: |
| CPU normal | 11,45 ms | 1,11 ms | 30,00 | 4,17 |
| CPU limitada4× | 25,57 ms | 4,75 ms | 16,50 | 4,17 |

Son promedios locales de tiempo acumulado por cambio, no tiempos por cuadro ni garantías para dispositivos reales. La segunda fila reduce ese trabajo aproximadamente81 %. No se registraron tareas largas en la comparación de producción. El peor intervalo entre cuadros con CPU limitada siguió alrededor de50ms; no se afirma haber eliminado toda pausa. La primera exploración sobre Next dev mostró sobrecarga adicional y no se usa como comparación de producción.

## Implementación

- Se retiraron las transiciones de `width` y `padding-left`. El fondo conserva un ancho fijo y anima `clip-path`; el borde y los iconos animan `transform`.
- El contenido adopta el ancho final y usa una traslación calculada antes de pintar. No se escala ni se captura como imagen. La inversión lee la posición visible actual y cancela la animación anterior.
- El ancho geométrico del `aside` es fijo; las comprobaciones usan su ancho visible tras el recorte, y lo comparan con la separación del contenido.
- Las animaciones se cancelan al cambiar de breakpoint y al desmontar. La preferencia de movimiento reducido omite el desplazamiento de escritorio. La apertura y cierre móvil mantienen `transform`, inercia, Escape y retorno de foco.

## Verificación

- 84 pruebas frontend y exportación estática con comprobación de tipos correctas.
- Cuatro recorridos de Dashboard/Consumo, escritorio/móvil, sin errores JavaScript ni desbordamiento. Incluyen teclado, plegado/expansión, Escape, foco, inversión y movimiento reducido.
- Perfil adicional en cuatro combinaciones de viewport/CPU, con seis cambios de estado cada una y comprobación de inversión rápida.
- Detector de Impeccable sobre `frontend/src/app/globals.css`: sin hallazgos. Se corrigieron los dos avisos; no se añadieron excepciones ni se deshabilitaron reglas.
- Revisión independiente de código y capturas de navegación: `disposition: ship`, sin correcciones materiales pendientes dentro del alcance revisado. Las capturas acreditan estados finales; la revisión del movimiento se apoya en código y mediciones locales, no en dispositivos reales.

Evidencia: `frontend/scripts/review-sidebar-performance.mjs`, `frontend/test-results/sidebar-performance/before/results.json`, `frontend/test-results/sidebar-performance/after/results.json` y `frontend/test-results/sidebar-interaction/results.json`. Las capturas muestran las variantes expandida, plegada y móvil. Para reproducir, servir `frontend/out/` localmente y usar `UI_REVIEW_URL` con el script. La limitación artificial de CPU no sustituye una prueba en teléfono o equipo de gama baja.
