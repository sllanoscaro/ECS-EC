# US4 — calidad, procedencia, coherencia y fallos

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

Se distinguen cero válido, ausencia, sin fuente y estado incompleto; los positivos
pequeños no se convierten en cero aparente. Los segmentos preservan fuente/base,
fechas, revisiones y modo, incluidos cambios dentro del mismo modo y diagnósticos.
La procedencia003 confiable se lee al corte, sin consultar el control privado del simulador.

`test_retained_total.py` incorpora realmente1200kWh, retira el original por el puerto
Retencion002 una vez vencido y verifica el total anual conservado y el gráfico mensual
sin puntos. Un intervalo anual sin contención mensual no se redistribuye ni prorratea.
La ausencia de evolución se explica en el PDF, sin sustituir el total por suma parcial.

El hash funcional conserva valores/revisiones/corte aunque una admisión extienda
metadatos operativos `retain_until` de la evidencia financiera. Esa exclusión no
modifica el DTO almacenado y no excluye ningún importe, cobertura, par ni revisión.
El contexto técnico, identidad nueva y emisión permanecen fuera de la captura funcional.

Fallos de captura/render/preflight e interrupción confirman resultado fallido y
`pdf.failed` atómicamente, sin BYTEA. El rollback no deja resultado/evento aislado;
reconciliar dos veces no duplica. Consultar o descargar no crea otro fallo del productor.
Los handles técnicos se liberan también si la publicación/reconciliación hace rollback.
