# US2 — composición, fuentes y geometría

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

Las referencias se generan con ReportLab y DejaVuSans2.37 incrustada. pypdf comprueba
los bytes: una página210×297mm, tolerancia0,1mm, texto efectivo>=10pt, seis secciones,
ancho real de glifos, cajas coincidentes con el manifiesto y ausencia de solapamientos.
Cambiar manifiesto, reducir transformaciones o corromper el archivo impide publicarlo.

Las pruebas cubren nombres largos,0/0.000001/1000000000000kWh, doce ciclos reales,
CAT-01 mensual/anual mixta30=10medidos+20calculados, cambios de fuente o base sin
cambiar el modo y diagnóstico no numérico por cambio dentro de un intervalo.
El día DST real de25horas conserva25rectángulos/bloques y ambas01:00(-0400/-0500).
La etiqueta de horas repetidas complementa el espaciado de ticks, sin quitar datos.

Se revisaron digitalmente el PDF y las capturas desktop/móvil, con animaciones
finalizadas. La revisión visual se realizó en el mismo agente, no con un revisor
independiente. El detector de interfaz no devolvió hallazgos; se conserva el sistema
visual existente, sin cambios de DESIGN.md ni PRODUCT.md.

**Pendiente005:T037: impresión física A4 al100%.** La inspección digital y geométrica
no sustituye esa comprobación. Ejemplos: [anual](artifacts/anual.pdf),
[escritorio](artifacts/desktop.png) y [móvil](artifacts/mobile.png).
