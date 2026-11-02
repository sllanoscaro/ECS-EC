# Base 001 y reglas puras verificadas

Fecha: 2026-11-02. Fixtures sintéticos en
`backend/tests/fixtures/consumption/scenarios.json`: zona America/Santiago,
UUID ficticios, siete categorías, tres intervalos por categoría, unidades mixtas y huecos.
No se atribuyen a la instalación física. Pruebas previas a implementación observaron
la ausencia de los módulos 001; después se ejecutaron las verificaciones siguientes.
Las omisiones por proveedor 002 ausente nunca se contabilizan como aceptación.

## Configuración propia con PostgreSQL real

`backend/tests/integration/consumption/test_configuration.py` verifica:

- Bootstrap histórico, siete estados únicos y fuentes con referencias protegidas.
- Revisión esperada, no-op sin evento/revisión nuevos y un solo ganador concurrente.
- Vigencia al aplicar, snapshots previos inmutables, etiquetas conservadas por revisión.
- Revisiones por categoría: etiqueta/cambio ajeno estable, cambio propio/restauración
  incremental; CAT-01 física independiente de parciales y calculada sensible a base/fuentes.
- Puerto de límites aislado con respuestas vacías reales, máximos físicos/calculados,
  historia retirada, fallo y claves incompletas. Ausencia/fallo impide modificaciones.
- Zona protegida con historia, cambio permitido sin ella y rechazo de UoW REPEATABLE READ
  para escrituras coordinadas. La lectura de límites usa READ COMMITTED después de locks.
- Rollback del contexto/fuentes/revisión/auditoría y del primer evento ya insertado cuando
  falla el segundo; FK RESTRICT impide borrar referencias históricas por cascada.

El doble de límites no implementa recepción ni tablas 002. La carrera conjunta con
recepción y la conservación efectiva tras retirar mediciones requieren T018.

## Validación y candidatos sin IO

Pruebas unitarias de `MeasurementValidator.normalize` y `TotalCalculator.evaluate`:

- Wh×0.001, kWh×1 y MWh×1000 exactos; originales y referencias conservados.
- Equivalencia de cero, q y M en las tres unidades, ceros finales y exponentes.
- `0 <= E < 10^30`, quantum exacto `10^-15`; negativos, float, booleanos, no finitos,
  unidades incompatibles, valores exteriores/no múltiplos rechazados sin redondear.
- Microsegundos, offsets obligatorios, rechazo por registro de desbordes UTC en fechas extremas,
  intervalo `[start,end)`, cambio exactamente en
  inicio/fin y cruce de revisión global ajena frente a cambio de fuente propia.
- 12+8=20, cero con base válida, base vacía sin cero y medidor total sin suma sustituta.
- Faltantes, fuentes/revisiones erróneas, duplicación de contribuciones y subintervalos
  desalineados no producen total numérico.
- Seis valores M producen exactamente
  `5999999999999999999999999999999.999999999999994 kWh` bajo contexto 50 estricto.
- Cambio de firma calculada conserva segmentos y revisiones, sin energía, base única,
  contribuciones o categorías faltantes fingidas. Cambio global cosmético permite el total.

Estos candidatos no son incorporaciones. No hay scheduler, límites de 15 minutos, aceptación
ni deduplicación persistente 001: esas capacidades siguen perteneciendo a 002.

## Contratos entregados para 002

`consumption/ports.py` declara normalización/evaluación y los métodos de MeasurementStore,
incluido `read_reconfiguration_bounds`. Reception conserva la firma de intento y
`read_attempt` del [contrato 002](../../002-registro-retencion-consumo/contracts/integrations.md).
Las pruebas de contrato actuales verifican tipos/referencias/invariantes aislados.
Los métodos de recepción/lectura no tienen proveedor instalado y sus resultados funcionales
todavía deben comprobarse en T018.

`lock_configuration` coordina contexto → categorías ordenadas en la UoW de escritura;
002 debe usarlo antes de leer historia/reloj/límites. `read_revisions` y
`configuration_segments` resuelven historia sin mutarla. Los segmentos internos incluyen
revisiones de las categorías de base para comprobar aportes; ese dato se excluye de la
proyección HTTP. Un segmento reconstruido solo desde JSON web debe rehidratar esas
revisiones desde configuración antes de evaluar: la falta de ellas falla explícitamente.
