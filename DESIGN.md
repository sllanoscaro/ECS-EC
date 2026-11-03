# Identidad visual de ECS-EC / Electro Conforma

## Autoridad y alcance

El usuario confirmó que los logos de `docs/Identidad Visual Electro Conforma/` son la identidad con la que presentará la propuesta y que sus colores deben conservarse en todos los diseños futuros. Este compromiso prevalece sobre la paleta provisional de la primera maqueta. El usuario aprobó integrar dashboard versión 5 y consumo versión 4. Su implementación local y límites se documentan en [ui-implementation.md](docs/ui-implementation.md); Costos sigue en revisión visual.

## Activos originales

- Logo principal para el panel expandido: [principal color](<docs/Identidad Visual Electro Conforma/electro-conforma_principal_color.svg>), con el nombre en dos líneas.
- Alternativa horizontal para espacios amplios: [línea color](<docs/Identidad Visual Electro Conforma/electro-conforma_linea_color.svg>).
- Símbolo compacto para navegación plegada: [icono color](<docs/Identidad Visual Electro Conforma/electro-conforma_icono_color.svg>).
- Icono de aplicación: [icono app](<docs/Identidad Visual Electro Conforma/electro-conforma_icono_app.svg>).
- Las variantes blancas originales están disponibles para fondos oscuros; las negras, para uso monocromático.

En la implementación usar los SVG originales. Mantener proporciones y colores, sin reconstruir el símbolo con texto o formas aproximadas ni sustituir su tipografía. Las imágenes generadas son referencias de composición; no reemplazan los activos oficiales.

## Paleta extraída de los SVG

| Color | Valor exacto | Procedencia | Aplicación propuesta |
| --- | --- | --- | --- |
| Verde profundo | `#0D4A37` | Versiones color e icono app | Identidad, énfasis, controles y texto de marca. |
| Verde | `#4F9A17` | Versiones color | Fondo de la sección activa en la navegación compartida. |
| Lima | `#A6E04B` | Versiones blancas e icono app | Acentos puntuales con texto oscuro; no texto pequeño sobre blanco. |
| Blanco | `#FFFFFF` | Versiones blancas e icono app | Superficies claras e identidad invertida según el activo. |
| Negro | `#111111` | Versiones negras | Texto y variante monocromática. |

Los valores originales son confirmados; los roles de interfaz de la última columna son una propuesta. Se permiten neutros de apoyo y tintes discretos para fondo, divisores y estados de interacción. Evitar introducir otro color de marca, degradados o una paleta distinta por pantalla. Los estados funcionales deben distinguirse con texto y símbolos, sin depender solo del color; cualquier color semántico adicional deberá justificarse por su función.

Comprobar contraste en la implementación. Conservar los colores del logo no obliga a usar el verde o el lima como texto pequeño sobre fondos claros.

## Continuidad entre superficies

Mantener la misma identidad en navegación, dashboard, ingreso, cuenta, consumo, costos y administración. Mostrar Electro Conforma como identidad de presentación y conservar ECS-EC como identificador del sistema. La variante compacta debe pertenecer a la misma familia que la marca expandida.

La sección activa usa fondo sólido `#4F9A17`, texto e icono blancos, por instrucción expresa del usuario. Aplicar en todas las vistas, sin banda lima lateral ni fondo verde pálido. Para conservar legibilidad con esa combinación, usar la etiqueta activa en negrita de 20 px como base y verificar contraste y foco al implementar; el estado activo también debe exponerse mediante `aria-current`.

## Colores estables por categoría

El usuario solicita que cada categoría tenga un color fijo en todos los gráficos. La correspondencia propuesta abajo se conserva por identificador, con independencia de orden, filtros, agrupación, representación, fuente medida/calculada o vista. Es una paleta de datos; los controles y la identidad mantienen los colores oficiales. Este criterio sustituye el verde único para todas las categorías de las primeras referencias.

| Identificador | Categoría | Color propuesto |
| --- | --- | --- |
| CAT-01 | Energía eléctrica total | Verde profundo `#0D4A37` |
| CAT-02 | HVAC y agua caliente sanitaria | Cobre `#A65E2E` |
| CAT-03 | Iluminación exterior | Violeta `#7A6EAB` |
| CAT-04 | Iluminación interior | Azul `#2876B7` |
| CAT-05 | Circuitos de enchufes | Magenta `#B54979` |
| CAT-06 | Sistema sanitario | Turquesa `#16857C` |
| CAT-07 | Ascensores | Gris azulado `#596579` |

Una sola categoría usa un único color en todas sus barras; no asignar colores diferentes a cada intervalo. El desglose del dashboard muestra el color de cada categoría junto a su nombre. El total conserva su color sin sumarlo de nuevo a las categorías parciales. Las magnitudes financieras no se convierten implícitamente en categorías de consumo por compartir nombres de conceptos.

Conservar etiquetas y marcadores distinguibles sin depender solo del color. Validar contraste, fondos y percepción de los colores en la implementación; los colores exactos de datos son una propuesta inicial, mientras que la asociación estable por categoría es un requisito confirmado. Advertencias y errores conservan su semántica independiente de la paleta de categorías.

## Advertencias, errores y contexto temporal

El usuario solicita destacar advertencias y errores con un color diferente del verde de marca. La referencia de consumo aplica amarillo/ámbar a datos incompletos: fondo `#FFF4CC`, borde `#D99B16`, texto `#6B4300`, icono triangular y causa explícita. Los valores de color son tokens propuestos para la implementación, sujetos a verificación de contraste. Los fallos que impiden consultar se proponen en rojo, con texto, icono y recuperación; ese estado aún no está representado en una maqueta. No colorear ceros válidos como advertencias ni depender solo del color.

Concentrar zona horaria y reloj actual en el pie derecho compartido de consumo y dashboard; retirar sus repeticiones en filtros, gráfico y encabezado de tabla. No confundir el reloj con fecha de actualización ni período consultado. Mantener accesibles las distinciones de offset cuando sean necesarias para interpretar horas repetidas.

Refinamiento solicitado para el reloj: todo el texto en el mismo gris secundario legible y peso normal, incluidas las cifras; sin icono de reloj. Dashboard versión 5 y consumo versión 4 lo representan.

En Consumo, el usuario solicita el aviso amarillo con todo su texto en peso regular, incluido «Datos incompletos:». La versión 4 retira además el apartado «Procedencia y configuración».

## Referencias vigentes

[Costos, primera referencia](.impeccable/mocks/costs-v1.png): consulta por ciclo, desglose y contraste de boleta con subtotal parcial explícito. Pendiente de revisión, con tarifas ilustrativas. El [brief de costos](docs/costs-reference.md) detalla su alcance.

[Dashboard y navegación, versión 5](.impeccable/mocks/dashboard-navigation-v5.png) y [consumo, versión 4](.impeccable/mocks/consumption-v4.png): referencias aprobadas e integradas localmente. Las imágenes conservan datos ilustrativos. Ambas incorporan la nueva navegación activa y colores por categoría. Los briefs de [dashboard](docs/dashboard-reference.md) y [consumo](docs/consumption-reference.md) conservan requisitos y límites.
