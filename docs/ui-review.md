# Inventario y revisión inicial de interfaces

Revisión: 2026-11-03. Base de producto: [PRODUCT.md](../PRODUCT.md), [arquitectura](architecture.md), [hoja de ruta](implementation-roadmap.md) e historias de usuario en `specs/`.

## Alcance y evidencia

Se inventariaron las diez rutas existentes en `frontend/src/app/`, sus componentes y estados. La revisión visual utiliza Chromium sobre Next.js en desarrollo, en escritorio de 1440 × 1000 y móvil de 390 × 844, con capturas de página completa. Los escenarios adicionales se capturan en escritorio.

Los datos y sesiones son sintéticos y se interceptan exclusivamente en el contexto de Playwright. No se modifica la autenticación de la aplicación ni se envían solicitudes a una base real. No hay contenedores activos al revisar; Compose requiere configuración externa, incluido `POSTGRES_PASSWORD`. Esta evidencia permite evaluar presentación y estados del cliente, pero no acredita integración, seguridad en servidor, validez tarifaria ni aceptación funcional.

Las capturas y el resultado por escenario se generan en `frontend/test-results/ui-review/`, directorio local ignorado por Git. `results.json` registra ruta, escenario, tamaño, errores JavaScript, solicitudes sin fixture, desbordamiento y conexión HMR.

Resultado de la pasada completa: **41 capturas**, todas con HTTP 200 y conexión HMR, sin excepciones JavaScript no controladas ni solicitudes sin fixture. Una comprobación adicional de consola en consumo identificó el aviso React detallado abajo; no confundir ausencia de excepciones con consola limpia. No se editaron las interfaces de producto durante esta revisión.

Desbordamiento horizontal medido con ancho de ventana de 390 px:

| Vista | Exceso sobre el ancho de ventana |
| --- | ---: |
| Consumo | 147 px |
| Costos | 540 px |
| Administración de costos | 540 px |
| Usuarios | 198 px |
| Historial administrativo | 419 px |

Estas medidas corresponden a las muestras sintéticas de esta revisión; cambian según el contenido.

## Vistas existentes

| Ruta | Usuario y pregunta principal | Contenido existente | Mejora propuesta |
| --- | --- | --- | --- |
| `/` | Visitante o cuenta activa: ¿dónde comienzo? | Nombre y texto de plataforma; mensaje de incorporación futura de módulos. | Actualizar la orientación según las capacidades reales y ofrecer un camino claro a consulta o ingreso. |
| `/ingreso/` | Sin sesión: ¿cómo accedo? | Correo, contraseña, envío, error y espera por límite de intentos; con sesión, enlace a cuenta. | Dar identidad y contexto, alinear campos y aclarar recuperación mediante administración. |
| `/cuenta/` | Ambos perfiles: ¿cómo renuevo mi contraseña? | Identidad, perfil, contraseña actual/nueva/confirmación, renovación obligatoria y cierre de sesión. | Separar identidad, cambio de contraseña y salida; acercar las reglas al campo relevante y evitar duplicar acciones de salida. |
| `/consumption/` | Ambos perfiles: ¿cuánto se consumió y qué tan completos son los datos? | Siete categorías, período y zona, detalle/hora/día/mes/año, gráfico/tabla/ambos, procedencia, configuración y estados. | Priorizar período, categoría, calidad y resultado; llevar evidencia extensa a detalle consultable; resolver desbordamiento móvil. |
| `/costos/` | Ambos perfiles: ¿cuál es el costo disponible y cómo contrasta con la boleta? | Ciclos, revisiones, historial, gráfico, desglose, subtotal/costo completo, captura reproducible, boletas y contrastes. | Separar resumen financiero, historial y detalle; mejorar fechas, cifras y estados; resolver tabla móvil. |
| `/administracion/consumo/` | Administrador: ¿qué fuentes tiene cada categoría? | Zona, siete grupos de medidores, UUID y etiqueta, base del total, cambios previstos, guardado y conflicto. | Mejorar agrupación y lectura por categoría; explicar consecuencias sin exigir interpretar identificadores técnicos como navegación. |
| `/administracion/costos/` | Administrador: ¿cómo mantengo el suministro y los cálculos BT4.3? | Suministro, calendarios y cargos, nuevas revisiones, cálculo, historial, boletas y selección de contraste. | Dividir el trabajo en secciones manejables; reducir la longitud del formulario y mantener clara la revisión seleccionada. |
| `/administracion/usuarios/` | Administrador: ¿a quién doy acceso y con qué perfil? | Filtros, tabla, alta, edición, desactivación y restablecimiento de contraseña. | Separar lista y editor, destacar cuenta seleccionada y consecuencias de cambios; resolver tabla móvil. |
| `/administracion/historial/` | Administrador: ¿qué cambió, quién lo hizo y con qué resultado? | Filtros UTC, acción, resultado, UUID de actor/destino, evidencia y paginación. | Mejorar vocabulario y fechas, resumir identificadores sin perder acceso al valor completo, resolver tabla móvil. |
| `/reportes/` | Cuenta con permiso: ¿puedo generar un PDF? | Ruta protegida con aviso de generación todavía no disponible. | Conservar honestidad del estado; diseñar el flujo cuando exista la capacidad propietaria de PDF005. |

El historial de consumo vive en `/consumption/`; el historial financiero, las boletas, el contraste y las bases de reproducción viven dentro de costos. No son rutas adicionales. Notificaciones no tiene una vista implementada en este inventario. La observabilidad pertenece al entorno técnico externo, no a una pantalla funcional del Operador.

## Hallazgos compartidos

1. **P1 — Navegación y orientación.** Los enlaces están en una línea separada por puntos, sin indicación de ruta activa ni agrupación entre consulta y administración. Falta un encabezado de producto persistente fuera del inicio. Reportes tiene ruta, pero no un enlace en la navegación compartida. La conveniencia de incorporarlo depende de la capacidad real de PDF005.
2. **P1 — Adaptación móvil.** Las tablas de consumo, costos, cuentas y auditoría desbordan el ancho de la página. Hace falta una representación móvil adecuada o desplazamiento contenido dentro de cada tabla, preservando todos los campos necesarios.
3. **P1 — Densidad y jerarquía.** Las pantallas extensas mezclan filtros, resultados, operación administrativa y referencias técnicas. El primer paso debe quedar claro y el resultado principal necesita precedencia sobre detalles de auditoría o reproducción.
4. **P2 — Formularios.** Predomina el flujo de etiquetas y campos en línea, con alineaciones variables y agrupaciones extensas. Fechas con offset, zona IANA y UUID requieren ayuda contextual y controles apropiados, preservando la precisión del contrato.
5. **P2 — Lectura numérica.** El estilo global alinea todas las celdas a la izquierda y no establece cifras tabulares. Fechas ISO y cadenas técnicas ocupan mucho espacio. Mejorar presentación sin redondear ni alterar los valores contractuales.
6. **P2 — Gráficos.** Las etiquetas SVG de consumo usan tamaños nominales de 9–10 px que se reducen aún más al escalar el gráfico a móvil. Revisar escalas, etiquetas y uso de espacio conservando accesibilidad y equivalencia con la tabla.
7. **P2 — Inicio desactualizado.** El texto indica incorporación futura de funcionalidades que ya tienen vistas implementadas. La portada debe orientar según el estado confirmado de cada capacidad.
8. **P2 — Aviso React en consumo.** La consola informa que `QueryState` recibe `key` dentro de `<QueryState {...query} />` en `frontend/src/components/consumption/ConsumptionView.tsx`. React requiere pasar esa propiedad directamente. La página sigue renderizando, pero el aviso debe resolverse al trabajar esa vista. La comprobación de consola adicional está en `frontend/test-results/ui-review-console/results.json`.

Son fortalezas a preservar: etiquetas explícitas en formularios, comprobación de sesión antes de mostrar datos privados, estados diferenciados, distinción entre total medido/calculado, coherencia entre tabla y gráfico y separación entre subtotal disponible y costo completo. Estas observaciones provienen del código y de escenarios visuales sintéticos; no equivalen a validación integral.

El detector de Impeccable ejecutado sobre `frontend/src` no devolvió hallazgos (`[]`). Ese resultado no detecta ni invalida los problemas de composición y desbordamiento observados en el navegador. No se realizó una certificación de accesibilidad ni una evaluación completa de contraste, lectores de pantalla o rendimiento.

## Orden propuesto para mejorar poco a poco

1. Navegación y estructura compartida, acordando primero una imagen de referencia según la preferencia registrada.
2. Consumo: flujo principal de consulta, calidad, gráfico/tabla y móvil.
3. Costos de consulta: resumen, historial, desglose y contraste.
4. Fuentes de consumo y administración de costos, con atención a formularios largos y revisiones.
5. Usuarios, cuenta, ingreso e historial administrativo.
6. Inicio y reportes, ajustados al estado real de las capacidades.

Este orden es una propuesta de trabajo de interfaz. No cambia la funcionalidad seleccionada en Spec Kit, la propiedad de los módulos ni sus tareas o criterios de aceptación.

## Verificación visual para cambios futuros

Desde `frontend/`:

```sh
npm run dev -- --hostname 127.0.0.1
```

Servidor: `http://127.0.0.1:3000`. Next.js recompila los cambios mediante HMR. El navegador ordinario necesita un backend real para las vistas protegidas; los datos sintéticos de esta revisión solo existen dentro de Playwright.

En otra terminal, también desde `frontend/`:

```sh
npm run review:views -- test-results/ui-review-before
# Tras editar la interfaz y dejar que Next.js recompile:
npm run review:views -- test-results/ui-review-after
```

Para una pasada acotada, usar por ejemplo `UI_REVIEW_FILTER=consumption npm run review:views -- test-results/consumption-after`. `UI_REVIEW_URL` permite seleccionar otro servidor local; se rechazan destinos externos. Cada directorio debe ser distinto si se quiere conservar evidencia anterior.

El [script de revisión](../frontend/scripts/review-views.mjs) abre Chromium, recorre todas las rutas, aplica interacciones locales y guarda PNG y JSON. Se apoya en Playwright y el Chromium ya instalados. En entornos restringidos, tanto el servidor como Chromium pueden requerir autorización para ejecutarse fuera del sandbox.

Cada cambio debe revisarse abriendo las capturas anteriores y posteriores, al menos en escritorio y móvil, y comprobando desbordamientos, legibilidad, estados y comportamiento del flujo afectado. Un resultado HTTP 200 no acredita por sí solo que el contenido esperado se haya renderizado. El script confirma además que el formulario administrativo de costos se monta con la sesión sintética autorizada.

La batería incluye selección horaria, gráfico/tabla, cero medido, ausencia de medidor, datos vacíos/incompletos, fallos de consulta, renovación obligatoria, edición/restablecimiento de cuentas, creación de un segmento y cargo tarifario, corrección de boleta y apertura de evidencia reproducible. Las escrituras de API se rechazan en el entorno sintético; las mutaciones reales, concurrencia, cálculos y permisos de servidor se validan con las pruebas y dependencias propias de cada spec.

No se ha activado el selector interactivo `impeccable live`. La verificación visual disponible utiliza el servidor Next.js y capturas de Chromium; no requiere ese selector.
