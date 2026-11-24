# Apertura offline y revisión pendiente

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

Los tres PDF descargados por el E2E se abrieron dentro de la imagen final con
`docker run --network none --read-only`, mediante pypdf, sin conexión al monolito,
PostgreSQL, fuentes remotas o visores. Se verificaron una página, fuente incrustada,
seis secciones y ausencia de anotaciones/acciones externas necesarias. También se
renderizó localmente el anual con `pdftoppm` para revisión digital.

Inventario de bytes/hash: [offline.json](artifacts/offline.json). Son archivos sintéticos
de referencia, generados por la aplicación; nunca son una respuesta PDF pregrabada.

**005:T059 permanece pendiente en su componente de revisión física ligado aT037.**
La apertura sin red sí se comprobó; no se acredita una impresión que no se realizó.
