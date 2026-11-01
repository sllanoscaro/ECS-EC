# Feature Specification: Registro temporal y retención del consumo

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "La plataforma ECS-EC debe recibir datos dentro de un período
mínimo de 15 minutos, para todas las categorías especificadas en la spec-001. Se llevará
un registro en forma horaria, diaria, mensual y anual. El sistema deberá ser capaz de
mantener los registros durante un mínimo de 12 meses."

**Clarificación recibida**: Deben transcurrir como mínimo 15 minutos entre actualizaciones;
no se permiten actualizaciones más frecuentes.

**Especificación relacionada**: [spec-001: Consumo eléctrico por categorías](../001-visualizar-consumo-categorias/spec.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Respetar la separación mínima entre actualizaciones (Priority: P1)

Como persona responsable del monitoreo, quiero que cada categoría incorpore nuevos datos
con al menos 15 minutos de separación para respetar la frecuencia de actualización definida.

**Why this priority**: La recepción debe aplicar la regla temporal a las siete categorías
sin confundir las actualizaciones de categorías diferentes.

**Independent Test**: Preparar envíos para las siete categorías y controlar sus momentos
de recepción; verificar primeras actualizaciones, intentos anticipados y el límite de 15 minutos.

**Acceptance Scenarios**:

1. **Given** una categoría sin actualizaciones previas, **When** llega su primer envío válido,
   **Then** se acepta y queda registrada la fecha y hora de esa actualización.
2. **Given** una actualización aceptada a las 10:00, **When** llegan nuevos datos de la misma
   categoría a las 10:14:59, **Then** se rechazan por anticipación, se informa que puede
   actualizarse desde las 10:15 y no se modifican sus mediciones ni agregados.
3. **Given** esa actualización de las 10:00, **When** llegan datos válidos a las 10:15 o después,
   **Then** se aceptan y el siguiente intervalo mínimo se cuenta desde esa nueva aceptación.
4. **Given** siete categorías habilitadas, **When** las siete envían actualizaciones válidas
   al mismo instante y cada una cumple su propio intervalo mínimo, **Then** las siete se aceptan.
5. **Given** una categoría actualizada a las 10:00, **When** recibe un duplicado o un envío sin
   registros válidos nuevos a las 10:10, **Then** no incorpora datos ni reinicia el intervalo;
   un envío válido a las 10:15 sigue siendo admisible.
6. **Given** una categoría sin actualizaciones desde hace una hora, **When** recibe un envío
   válido con varias mediciones históricas no superpuestas, **Then** puede aceptarlas como
   una única actualización, sin exigir un envío por cada registro.
7. **Given** un envío con una categoría todavía no habilitada para actualizar y otra cuyo
   intervalo ya se cumplió, **When** se evalúan sus datos, **Then** se rechazan los nuevos
   datos anticipados de la primera y se aceptan los válidos de la segunda independientemente.

---

### User Story 2 - Consultar registros horarios, diarios, mensuales y anuales (Priority: P1)

Como persona encargada del edificio, quiero consultar el consumo de cada categoría por
hora, día, mes o año para analizarlo a distintas escalas en los gráficos y tablas existentes.

**Why this priority**: Es el nuevo registro histórico solicitado y amplía el detalle por
intervalo definido en la spec-001.

**Independent Test**: Preparar mediciones con sumas conocidas para períodos completos y
consultar las cuatro agrupaciones en las siete categorías.

**Acceptance Scenarios**:

1. **Given** cuatro mediciones contiguas de 1 kWh que cubren una hora, **When** se consulta
   la agrupación horaria, **Then** gráfico y tabla muestran un registro agregado de 4 kWh,
   identificado como completo y asociado a esa hora y categoría.
2. **Given** mediciones que cubren un día, un mes y un año completos, **When** se consulta
   cada agrupación, **Then** su consumo es la suma de la energía de sus mediciones válidas,
   sin promediarla ni sumar valores de otras categorías.
3. **Given** una categoría y un período elegidos, **When** se cambia entre hora, día, mes
   y año, **Then** se conserva la categoría y el período y ambas vistas usan los mismos
   bloques, consumos, unidades y estados de cobertura.
4. **Given** meses de distinta duración, un año bisiesto o cambios de horario estacional,
   **When** se generan sus registros, **Then** sus límites respetan el calendario y la zona
   horaria del edificio; las horas locales repetidas se distinguen mediante su desfase.
5. **Given** un consumo total recibido distinto de la suma de las categorías parciales,
   **When** se agrupan los datos, **Then** cada agrupación del total utiliza únicamente
   las mediciones recibidas de la categoría total.
6. **Given** bloques que cruzan los límites del período de consulta, **When** se muestra una
   agrupación, **Then** solo se incluyen bloques completos dentro de ese período y se
   informa la exclusión de los demás, sin prorratear ni cambiar silenciosamente el filtro.
7. **Given** una instalación sin medidor total y dos intervalos contiguos con totales
   calculados válidos de 20 y 30 kWh, **When** se agrupa la hora que ambos cubren,
   **Then** CAT-01 muestra 50 kWh calculados con su base identificada, sin volver a añadir
   las contribuciones parciales; un intervalo sin todas las lecturas requeridas no aporta
   un total y deja visible su falta de cobertura.

---

### User Story 3 - Conservar y consultar al menos doce meses (Priority: P1)

Como persona responsable del edificio, quiero conservar las mediciones y sus registros
agregados durante al menos 12 meses para consultar el historial sin perder su detalle.

**Why this priority**: La conservación mínima debe proteger tanto los datos recibidos como
las cuatro agrupaciones, sin depender de que se consulten frecuentemente.

**Independent Test**: Preparar registros con fechas de aceptación y actualización conocidas
y verificar su disponibilidad antes y en el límite de 12 meses mediante el avance controlado
de la fecha de evaluación, sin esperar un año real.

**Acceptance Scenarios**:

1. **Given** una medición aceptada el 2026-10-31 a las 12:00, **When** se consulta antes del
   2027-10-31 a las 12:00, **Then** conserva su valor, unidad, origen e intervalo y permanece
   disponible en el detalle y en los agregados correspondientes.
2. **Given** un registro que alcanza los 12 meses de conservación, **When** se evalúa su
   permanencia, **Then** no se ha eliminado antes del límite y puede seguir conservándose;
   cumplir el mínimo no obliga a borrarlo.
3. **Given** una medición histórica recibida con retraso, **When** se acepta, **Then** sus
   12 meses mínimos se cuentan desde su aceptación y no desde su antigüedad de medición.
4. **Given** un agregado al que se incorpora una medición nueva válida, **When** se actualiza,
   **Then** el agregado actualizado queda protegido durante al menos otros 12 meses desde
   esa incorporación; consultar o reenviar duplicados no cambia su fecha de conservación.
5. **Given** un período anual con datos solo desde el inicio de operación, **When** se consulta,
   **Then** se ofrece el registro anual disponible con su cobertura incompleta, sin inventar
   historia anterior ni presentarlo como un año completo.
6. **Given** una medición aceptada el 2028-02-29, **When** se calcula su aniversario de
   conservación, **Then** el límite corresponde al 2029-02-28 a la misma hora local.
7. **Given** un agregado todavía protegido y mediciones base que ya cumplieron su mínimo,
   **When** esas mediciones dejan de conservarse, **Then** el valor y la cobertura del
   agregado histórico protegido no se degradan por esa retirada.
8. **Given** un aniversario que cae en una hora local inexistente o repetida, **When** se
   determina el límite mínimo, **Then** se usa respectivamente el primer instante válido
   posterior o la ocurrencia posterior de la hora repetida, sin adelantar la conservación.
9. **Given** un agregado protegido cuyo detalle más antiguo ya no se conserva, **When**
   una actualización permitida aporta datos tardíos nuevos y reenvíos ya contabilizados,
   **Then** solo las mediciones nuevas incrementan el consumo y la cobertura, y las
   contribuciones anteriores se conservan.

---

### User Story 4 - Interpretar registros incompletos y datos tardíos (Priority: P2)

Como persona encargada del monitoreo, quiero reconocer los períodos sin datos, incompletos
o en curso para interpretar los registros históricos según la información realmente recibida.

**Why this priority**: Una suma parcial no representa el consumo completo de un período.

**Independent Test**: Preparar intervalos faltantes, ceros medidos, mediciones que cruzan
límites y datos tardíos; verificar las sumas y la cobertura de cada agrupación.

**Acceptance Scenarios**:

1. **Given** tres intervalos de 15 minutos y 1 kWh dentro de una hora ya terminada,
   **When** se consulta esa hora, **Then** muestra 3 kWh, cobertura del 75 % y estado
   incompleto; los 15 minutos faltantes no se sustituyen por cero.
2. **Given** un período sin mediciones, **When** se consulta, **Then** se indica "Sin datos"
   y no se inventa un consumo de 0 kWh; un período cubierto con ceros medidos sí muestra cero.
3. **Given** un día, mes o año aún no terminado, **When** se consulta, **Then** se identifica
   como en curso y se muestra su cobertura real respecto de la duración total del período.
4. **Given** un período incompleto y una actualización posterior permitida con datos faltantes,
   **When** estos se aceptan, **Then** se actualizan los agregados afectados, su cobertura
   y ambas vistas; reenviar lo mismo no aumenta de nuevo el consumo.
5. **Given** una medición que cruza un límite de una agrupación, **When** se calcula esa
   agrupación, **Then** se conserva el detalle original pero se excluye esa medición del
   agregado con aviso; no se reparte su energía mediante una estimación.
6. **Given** una actualización anticipada rechazada o registros inválidos, **When** se consulta
   el historial, **Then** no aparecen como mediciones aceptadas ni contribuyen a los agregados.

### Edge Cases

- El intervalo mínimo se aplica por categoría y entre aceptaciones de datos nuevos:
  14 minutos y 59 segundos no bastan; 15 minutos exactos sí.
- Fechas declaradas por la fuente, cambios de hora o reenvíos no pueden adelantar la
  siguiente actualización permitida; la separación se mide en tiempo real transcurrido.
- Dentro de una misma actualización puede haber varias mediciones; el intervalo mínimo
  limita las actualizaciones de recepción y no impone la duración de cada medición.
- La regla no establece un máximo entre envíos ni exige cuatro actualizaciones por hora.
  Un retraso de la fuente no se compensa inventando lecturas.
- Una hora repetida tiene dos bloques distintos, con límites y desfases identificables;
  un día puede tener una duración distinta de 24 horas.
- Un intervalo que termina justo al comenzar otro período solo pertenece al período
  anterior; los intervalos contiguos no se cuentan dos veces.
- Una medición puede ser utilizable en una agrupación amplia y cruzar un límite de una más
  fina; las diferencias se explican con los avisos y la cobertura de cada agrupación.
- Los períodos anteriores al inicio de operación, con datos retirados tras su mínimo o con
  exclusiones no se presentan como completos sin cobertura que lo respalde.
- Los agregados en kWh no se suman a sus propias mediciones base ni a otros niveles para
  calcular el mismo consumo: cada medición contribuye como máximo una vez a cada bloque.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La funcionalidad DEBE aplicarse a las siete categorías CAT-01 a CAT-07 de la
  spec-001, manteniendo sus nombres, agrupaciones, categorías presentes y reglas de origen
  medido o calculado de CAT-01. No se exige que existan los siete medidores físicos.
- **FR-002**: ECS-EC DEBE permitir una primera actualización válida por categoría y exigir
  al menos 15 minutos reales entre actualizaciones que incorporen mediciones nuevas a esa
  misma categoría. Las categorías DEBEN poder actualizarse simultáneamente; el rechazo
  temporal de una NO DEBE impedir aceptar datos válidos de las otras. La incorporación
  de nuevos totales calculados a CAT-01 también DEBE respetar esa separación mínima;
  su cálculo interno no autoriza actualizaciones más frecuentes.
- **FR-003**: La elegibilidad DEBE calcularse desde el instante de la última aceptación de
  datos nuevos registrado por la plataforma. No DEBE depender de la fecha declarada por
  la fuente ni de discontinuidades de la hora local.
- **FR-004**: Un envío con datos nuevos antes del límite DEBE rechazarse indicando el motivo
  y la próxima fecha y hora admisible. NO DEBE incorporarse ni alterar el detalle o los agregados;
  la fuente puede reenviarlo desde el límite permitido.
- **FR-005**: Un envío permitido DEBE poder contener varias mediciones. Si al menos una
  medición nueva es aceptada, constituye una actualización de la categoría; si solo contiene
  duplicados o rechazos, NO DEBE reiniciar el intervalo mínimo. Las validaciones y la
  protección frente a duplicados y superposiciones de la spec-001 siguen vigentes.
- **FR-006**: Cada medición aceptada DEBE conservar su instante de primera aceptación,
  además del origen, valor, unidad e intervalo definidos en la spec-001. Cada total
  calculado DEBE conservar su instante de primera incorporación, base y referencias a
  las contribuciones, distinguiéndolo de una recepción de medición física.
- **FR-007**: ECS-EC DEBE ofrecer registros por hora, día calendario, mes calendario y año
  calendario para cada categoría, consultables mediante los gráficos y tablas de la spec-001,
  además del detalle por intervalo.
- **FR-008**: Los límites de los registros DEBEN usar la zona horaria del edificio: horas
  identificadas por sus límites reales y desfase, días entre medianoches, meses entre sus
  primeros días y años entre el 1 de enero y el siguiente 1 de enero.
- **FR-009**: El consumo de cada bloque DEBE ser la suma en kWh de las mediciones válidas
  de esa categoría completamente contenidas en él. NO DEBE promediar energías, mezclar
  categorías ni duplicar contribuciones. Para CAT-01 DEBE agruparse su serie medida o
  calculada conforme a la spec-001, sin volver a sumar las categorías contribuyentes.
- **FR-010**: Una medición que cruce un límite de bloque DEBE conservarse en el detalle y
  excluirse de ese agregado con aviso. NO DEBE prorratearse ni imputarse arbitrariamente.
  Los intervalos DEBEN tratarse con inicio incluido y fin excluido para evitar doble conteo.
- **FR-011**: Cada agregado DEBE indicar categoría, granularidad, inicio y fin, zona horaria,
  consumo disponible en kWh, situación temporal y cobertura. La cobertura DEBE calcularse
  como duración cubierta por mediciones incluidas dividida por duración real del bloque,
  multiplicada por 100; un cero válido medido o calculado aporta cobertura.
- **FR-012**: La situación temporal DEBE distinguir períodos en curso y terminados.
  La cobertura DEBE distinguir completo (100 %), incompleto (mayor que 0 % y menor que 100 %)
  y sin datos (0 %). Sin datos NO DEBE presentarse como consumo cero ni rellenarse con
  estimaciones. Un período en curso NO DEBE presentarse como terminado.
- **FR-013**: Al elegir agrupación, gráfico y tabla DEBEN conservar categoría y período y
  representar los mismos bloques, valores y cobertura. Solo DEBEN mostrarse bloques
  completamente incluidos en el filtro; las exclusiones DEBEN explicarse sin cambiarlo.
- **FR-014**: La aceptación de datos tardíos válidos, cuando cumpla el intervalo mínimo,
  DEBE actualizar las agrupaciones afectadas sin duplicaciones. La siguiente consulta
  posterior a la aceptación DEBE reflejar las mediciones aceptadas y su nueva cobertura.
- **FR-015**: Las mediciones originales DEBEN conservarse y ser consultables durante al menos
  12 meses calendario desde su primera aceptación, aunque correspondan a períodos anteriores.
  Los totales calculados DEBEN conservarse con su base y referencias durante al menos
  12 meses calendario desde su primera incorporación, sin presentarlos como lecturas físicas.
- **FR-016**: Los registros horarios, diarios, mensuales y anuales DEBEN conservarse y ser
  consultables durante al menos 12 meses calendario desde su creación o última incorporación
  de mediciones nuevas, la que sea posterior. Su creación corresponde a la primera aceptación
  de mediciones que contribuyan a ese bloque. Consultas, duplicados y rechazos NO DEBEN
  reiniciar ese plazo ni acortarlo.
- **FR-017**: El cómputo de 12 meses DEBE usar el aniversario en la zona horaria del edificio.
  Si el día no existe en el mes de destino, DEBE usarse su último día válido; una hora
  inexistente se traslada al primer instante local válido posterior y una hora repetida
  usa la ocurrencia posterior, para no adelantar el límite.
- **FR-018**: Ningún registro protegido DEBE eliminarse o quedar inaccesible antes de su
  límite de conservación. Superarlo NO DEBE obligar a eliminarlo. La retirada de mediciones
  base cuyo plazo ya venció NO DEBE alterar un agregado histórico todavía protegido;
  futuras incorporaciones DEBEN conservar sus contribuciones previas sin duplicar reenvíos.
- **FR-019**: Las consultas de períodos sin historia suficiente DEBEN indicar su cobertura
  incompleta o ausencia de datos; NO DEBEN reconstruir consumos inexistentes ni afirmar
  una conservación de 12 meses de mediciones anteriores al inicio de operación.

### Key Entities *(include if feature involves data)*

- **Categoría de consumo**: Una de las siete categorías de la spec-001, con su presencia
  de medidor configurada, procedencia medida o calculada cuando corresponda y sus propios
  instantes de última actualización aceptada y próxima actualización admisible.
- **Actualización de categoría**: Recepción de una o varias mediciones de una categoría
  o incorporación de nuevos totales calculados a CAT-01; identifica el instante de
  incorporación de datos nuevos y el resultado de cada registro.
- **Medición conservada**: Medición original de la spec-001 con fecha de primera aceptación
  y límite mínimo de conservación, independientemente de la fecha del consumo.
- **Total calculado conservado**: Resultado derivado de CAT-01 con fecha de primera
  incorporación, base y referencias a sus contribuciones y límite mínimo de conservación.
- **Registro agregado**: Consumo de una categoría en un bloque horario, diario, mensual
  o anual, con límites, cobertura, situación temporal y última incorporación de datos.
- **Plazo de conservación**: Intervalo mínimo de 12 meses calendario que protege la consulta
  del registro; superar su límite permite, pero no exige, dejar de conservarlo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En las siete categorías, el 100 % de los intentos de incorporar datos nuevos
  antes de 15 minutos desde la última actualización se rechaza sin modificar registros;
  los intentos válidos desde los 15 minutos se aceptan, incluidos los siete simultáneos.
- **SC-002**: Para series completas de valores conocidos, el 100 % de los registros horarios,
  diarios, mensuales y anuales coincide con la suma esperada de cada categoría y con sus
  representaciones en gráfico y tabla, incluidos meses de distinta duración y años bisiestos.
- **SC-003**: El 100 % de los escenarios de datos faltantes, ceros medidos, períodos en curso,
  límites cruzados y datos tardíos muestra el consumo y la cobertura esperados, sin duplicados
  ni estimaciones presentadas como mediciones.
- **SC-004**: Con un historial de al menos 12 meses para las siete categorías y avance controlado
  de la fecha de evaluación, el 100 % de las mediciones y agregados protegidos permanece
  consultable hasta su límite mínimo, incluidos registros tardíos y el aniversario bisiesto.
- **SC-005**: En al menos 9 de 10 tareas de evaluación con personas representativas del
  monitoreo, se consulta sin ayuda una categoría y agrupación asignadas y se identifica su
  consumo, período y cobertura en ambas vistas en un máximo de 60 segundos por tarea.

## Assumptions

- **Relación con spec-001**: Esta especificación amplía la
  [spec-001](../001-visualizar-consumo-categorias/spec.md). Sustituye su supuesto de ausencia
  de agregaciones por los cuatro registros solicitados y concreta la recepción y conservación.
  Las reglas del detalle, las unidades y los estados de consulta de la spec-001 siguen vigentes;
  en vistas agrupadas la correspondencia entre gráfico y tabla se aplica a los bloques agregados.
- **Categorías**: Se conservan energía eléctrica total; HVAC y agua caliente sanitaria;
  iluminación exterior; iluminación interior; circuitos de enchufes; sistema sanitario
  (agua potable y alcantarillado); y ascensores. No se añaden ni se subdividen categorías.
  Sus medidores pueden no estar presentes. CAT-01 conserva el origen medido o calculado,
  la base de categorías presentes y el tratamiento de lecturas faltantes de la spec-001.
  La cobertura temporal del total calculado no acredita que se midan todas las cargas del
  edificio; el alcance de su base debe seguir identificado en el historial.
- **Frecuencia confirmada**: La persona solicitante aclaró que el intervalo mínimo es de
  15 minutos, con prohibición de actualizaciones más frecuentes. Se aplica por categoría
  a la incorporación de mediciones nuevas, no a las consultas ni a la duración medida.
  No se fija un intervalo máximo ni se garantiza una actualización cada 15 minutos.
- **Envíos anticipados**: Se rechazan con información para reintentar; no se almacenan como
  mediciones aceptadas ni se incorporan más tarde automáticamente. La fuente puede agrupar
  mediciones pendientes en una actualización posterior permitida.
- **Datos y calendario**: Se mantiene el consumo por intervalo de la spec-001. La duración
  de sus mediciones no se deduce de la frecuencia de envío; las fuentes deben proporcionar
  intervalos compatibles con la precisión de agrupación deseada. Los cruces de límites
  reciben el tratamiento explícito de FR-010. La zona horaria concreta sigue siendo una
  dependencia que debe confirmarse con el edificio.
- **Conservación mínima**: Se protegen tanto las mediciones originales como los cuatro tipos
  de registros agregados. Doce meses significa meses calendario, no 365 días fijos.
  No se exige eliminación automática al terminar el mínimo ni una política para períodos mayores.
- **Dependencias y gobierno**: El plan debe verificar la compatibilidad de las fuentes con
  el intervalo mínimo, el reenvío de datos pendientes y la disponibilidad de sus referencias
  temporales. Aplican las restricciones de arquitectura y documentación de la constitución v1.0.0.
- **Límites de alcance**: No se incluyen nuevas categorías, alertas externas, predicciones,
  costos, control de equipos, autenticación nueva ni un mecanismo concreto de adquisición.
