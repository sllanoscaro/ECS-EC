# Feature Specification: Análisis de costos eléctricos con tarifa BT4.3

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "ECS-EC debe implementar una sección para el análisis y
visualización de costos según el uso de energía eléctrica del edificio. El costo se
calcula con las mediciones del tablero general bajo una única tarifa tipo BT4.3.
La información se podrá contrastar con la boleta de luz mensual del edificio."

**Especificaciones relacionadas**:
[spec-001: categorías y visualización](../001-visualizar-consumo-categorias/spec.md),
[spec-002: historial y conservación](../002-registro-retencion-consumo/spec.md) y
[spec-003: datos de prueba PAS600](../003-simulador-pas600-sftp/spec.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el costo desglosado del suministro general (Priority: P1)

Como persona responsable del edificio, quiero conocer el costo calculado de su suministro
general con BT4.3 y revisar sus componentes para entender el efecto del consumo y la demanda.

**Why this priority**: Es el resultado principal solicitado y debe utilizar la medición
general que corresponde al suministro del edificio.

**Independent Test**: Preparar mediciones del tablero general, históricos y un perfil BT4.3
de prueba con resultados conocidos; comprobar el desglose y su representación gráfica y tabular.

**Acceptance Scenarios**:

1. **Given** mediciones del tablero general identificadas como CAT-01 y consumos de las otras
   seis categorías, **When** se calcula un período, **Then** solo las primeras determinan
   sus cantidades medidas y los consumos parciales no se suman al total ni se cobran de nuevo.
2. **Given** un consumo de prueba de 1.000 kWh y un precio neto de prueba de 100 CLP/kWh,
   **When** se calcula el componente de energía, **Then** resulta 100.000 CLP netos y se
   identifica separadamente de los demás cargos BT4.3 y de los impuestos.
3. **Given** bloques válidos completos de 15 minutos, incluido uno de 10 kWh, **When** se
   obtienen sus demandas, **Then** ese bloque representa 40 kW medios y puede intervenir
   en el máximo correspondiente; no se usa la energía mensual como si fuera potencia.
4. **Given** máximos mensuales de 60 y 50 kW como los dos mayores del historial aplicable
   de 12 meses, **When** se obtiene la base de potencia suministrada, **Then** resulta
   55 kW y quedan identificados los meses y valores utilizados.
5. **Given** un período con consumo medido cero y perfil e históricos completos,
   **When** se calcula el costo, **Then** el componente de energía es cero y los cargos
   fijos o históricos aplicables conservan su valor según el perfil.
6. **Given** un cálculo disponible, **When** se consulta el gráfico y la tabla de costos,
   **Then** coinciden período, conceptos, importes, moneda, impuestos y estado del cálculo.
7. **Given** un período con horas punta y otro sin ellas, **When** se calculan sus cargos de
   punta, **Then** se utiliza respectivamente la demanda leída en punta del período o los
   antecedentes de punta exigidos por el perfil, con su calendario y procedencia visibles;
   en este último caso, si los dos mayores máximos mensuales de punta aplicables son 30 y
   20 kW, la base de facturación de prueba resulta 25 kW.
8. **Given** una instalación sin medidor total con un total calculado disponible en CAT-01,
   **When** se solicita el análisis BT4.3, **Then** se identifica que falta la medición
   general requerida, no se usa el total calculado como base de consumo del suministro
   y no se presenta un costo energético completo ni un consumo cero por esa ausencia.
9. **Given** un ciclo que cruza meses con distinta condición de punta, **When** se calcula,
   **Then** el mes de referencia de demanda procede de la regla documentada del perfil o
   de evidencia explícita validada; se muestran mes, fuente y versión de política. Si no
   puede resolverse, solo los cargos dependientes permanecen no calculables.
10. **Given** un Administrador con suministro y perfil preparados, **When** confirma en la
    interfaz web un cálculo o un recálculo con motivo, **Then** se abre la nueva revisión
    persistida; reintentar la misma operación no la duplica y el Operador no puede ejecutarla.

---

### User Story 2 - Contrastar el cálculo con la boleta mensual (Priority: P1)

Como persona responsable del edificio, quiero registrar los datos de su boleta y compararlos
con el cálculo del mismo período para reconocer diferencias en consumo, demanda e importes.

**Why this priority**: El contraste necesita fechas, conceptos y bases comparables para que
una diferencia de período o de impuestos no parezca un error de medición.

**Independent Test**: Registrar una boleta de prueba cuyo ciclo no coincida con un mes calendario
y comparar sus datos con un cálculo conocido del mismo intervalo y suministro.

**Acceptance Scenarios**:

1. **Given** una boleta cuyo ciclo abarca partes de dos meses, **When** se registra para
   comparar, **Then** el cálculo de referencia utiliza sus límites de consumo registrados
   y no el mes calendario de emisión.
2. **Given** importes y cantidades comparables registrados en la boleta, **When** se abre
   el contraste, **Then** se muestran valores calculados, facturados y diferencias por
   concepto, sin modificar las mediciones ni adaptar automáticamente las tarifas para igualarlos.
3. **Given** un importe calculado de 105 CLP y facturado de 100 CLP, **When** se compara,
   **Then** la diferencia calculado menos facturado es 5 CLP y 5 %; si el facturado es cero,
   la diferencia monetaria se muestra y el porcentaje indica que no aplica.
4. **Given** una boleta con deuda anterior, intereses o ajustes ajenos al costo calculado,
   **When** se compara, **Then** esos conceptos se identifican separadamente y se diferencia
   el subtotal comparable del total a pagar.
5. **Given** una boleta con conceptos netos y otros con impuestos incluidos, **When** se
   compara, **Then** solo se confrontan importes con la misma base tributaria y no se
   vuelve a aplicar un impuesto ya incluido.
6. **Given** una boleta ya registrada, **When** se vuelve a ingresar su identificador o llega
   una corrección para ese ciclo, **Then** se detecta la repetición o se registra una nueva
   revisión explícita, conservando la procedencia y la versión comparada anteriormente.
7. **Given** un período sin boleta registrada, **When** se consulta, **Then** el cálculo
   permanece disponible y se indica que todavía no existe contraste con una boleta.
8. **Given** revisiones compatibles de cálculo y boleta, **When** el Administrador las
   selecciona y confirma el contraste en la web, **Then** se persiste y muestra una
   comparación de ese par exacto, recuperable tras recargar la página.

---

### User Story 3 - Mantener las condiciones BT4.3 con sus vigencias (Priority: P2)

Como persona responsable de costos, quiero registrar las condiciones y precios BT4.3
aplicables al suministro y sus vigencias para que cada cálculo use la referencia correcta.

**Why this priority**: Una única opción tarifaria puede tener distintos precios y condiciones
a lo largo del historial; los cálculos anteriores deben seguir siendo reproducibles.

**Independent Test**: Registrar dos versiones sucesivas del perfil BT4.3 con fuentes y
vigencias conocidas y comprobar cálculos de períodos anteriores y posteriores al cambio.

**Acceptance Scenarios**:

1. **Given** el suministro y un pliego de referencia, **When** se configura su perfil,
   **Then** quedan identificados distribuidora, ubicación y condiciones relevantes, BT4.3,
   moneda, precios, unidades, calendario de punta, impuestos, redondeo y vigencias.
2. **Given** un precio o una regla obligatoria sin referencia para el período elegido,
   **When** se intenta calcular, **Then** se identifica el dato faltante y no se presenta
   un costo BT4.3 completo obtenido con un valor cero o con una tarifa supuesta.
3. **Given** una versión futura del perfil, **When** se guarda, **Then** los cálculos históricos
   mantienen la versión utilizada; un recálculo explícito produce una revisión identificable.
4. **Given** un ciclo que atraviesa un cambio de precios o condiciones, **When** se calcula,
   **Then** se aplica la regla de vigencia documentada para cada cargo y no se prorratean
   cargos fijos o de demanda mediante una división arbitraria.
5. **Given** segmentos superpuestos o condiciones contradictorias dentro de una revisión,
   **When** se validan, **Then** se exige resolver la ambigüedad antes de publicarla; la
   coincidencia de vigencias entre revisiones históricas no constituye ese conflicto.
6. **Given** la sección configurada, **When** se consulta su opción tarifaria,
   **Then** se identifica BT4.3 y sus versiones de vigencia, sin presentar otras tarifas
   como alternativas de cálculo de esta funcionalidad.
7. **Given** un perfil publicado con vigencia abierta, **When** se publica una revisión con
   el calendario completo dividido ante un nuevo precio o corregido retroactivamente,
   **Then** se conserva la revisión anterior y sus cálculos; solo los cálculos nuevos o
   recálculos explícitos usan la nueva revisión publicada.
8. **Given** suministro aún no registrado o una edición concurrente, **When** el Administrador
   abre y guarda su editor web, **Then** puede crear el suministro una sola vez o editarlo
   contra la revisión leída; un conflicto conserva las entradas y exige revisar el estado actual.
9. **Given** dos publicaciones basadas en la misma última revisión, **When** se confirman
   concurrentemente, **Then** solo una se guarda y la otra informa conflicto sin modificar
   el calendario publicado; un borrador guardado no cambia la selección para calcular.

---

### User Story 4 - Revisar el historial y reconocer cálculos incompletos (Priority: P2)

Como persona encargada del edificio, quiero revisar la evolución de costos y reconocer
qué resultados tienen datos incompletos o están en curso para interpretarlos correctamente.

**Why this priority**: La disponibilidad de energía no garantiza que exista información
suficiente para calcular todos los componentes de demanda e impuestos.

**Independent Test**: Preparar períodos completos, en curso, sin mediciones, con datos de
demanda insuficientes y con revisiones; comprobar estados, trazabilidad e historial.

**Acceptance Scenarios**:

1. **Given** al menos 12 meses de cálculos y boletas disponibles, **When** se consulta el
   historial, **Then** sus gráficos y tablas permiten recorrer los ciclos y ver el cálculo,
   el importe facturado comparable cuando exista y la diferencia.
2. **Given** energía conocida pero solo en intervalos horarios, **When** se intenta obtener
   demanda de 15 minutos sin otra medición válida, **Then** ese componente se declara no
   calculable y no se deduce una demanda máxima a partir del promedio horario.
3. **Given** un historial insuficiente para el cálculo de demanda o mediciones faltantes,
   **When** se consulta el costo, **Then** se identifican componentes disponibles y faltantes
   y el resultado no se presenta como un costo completo; los vacíos no se rellenan con ceros.
4. **Given** un ciclo que aún no termina, **When** se consulta, **Then** se identifica como
   en curso y provisional, sin presentar el consumo observado como una proyección del cierre.
5. **Given** nuevas mediciones válidas o una corrección de boleta, **When** se recalcula o
   se actualiza el contraste, **Then** se genera una revisión trazable y no se altera la
   evidencia de la comparación anterior.
6. **Given** las mismas mediciones, históricos y versión tarifaria, **When** se repite el
   cálculo, **Then** se obtienen los mismos importes y bases de cálculo tras el redondeo definido.
7. **Given** el registro de una comparación, **When** se inspecciona su procedencia,
   **Then** se identifican el tablero general, el suministro de la boleta y cualquier
   diferencia conocida entre puntos de medición, sin aplicar factores de ajuste no documentados.
8. **Given** un cálculo todavía dentro de sus 12 meses mínimos y detalle de mediciones que
   ya cumplió su propio plazo y dejó de conservarse, **When** se reproduce ese cálculo,
   **Then** sus bases preservadas permiten obtener los mismos importes y versiones sin
   perder el historial de máximos que se utilizó.
9. **Given** una boleta corregida o un costo recalculado sin nueva comparación, **When** se
   consulta el historial o su captura para reportes, **Then** se seleccionan las últimas
   revisiones visibles al corte y se indica contraste pendiente para ese par, con diferencias
   ausentes y sin incluirlo en el contraste agregado; la comparación anterior sigue siendo
   histórica y una captura anterior conserva su selección original.

### Edge Cases

- No tener mediciones no equivale a haber medido cero; tampoco elimina cargos fijos o
  históricos cuya base sí esté disponible.
- Un total calculado puede estar disponible en CAT-01 sin medidor total. Sirve para
  consultar el consumo de las categorías presentes, pero no satisface el requisito de
  medición general para los costos BT4.3; esa base faltante debe quedar identificada.
- Una actualización recibida cada 15 minutos no demuestra que sus mediciones permitan
  reconstruir los bloques de demanda de 15 minutos; se verifica la resolución del dato.
- La falta de parte de un bloque de demanda o de un mes histórico puede ocultar un máximo:
  no se considera completo por disponer de algunos registros.
- Dos meses distintos con el mismo máximo son dos antecedentes válidos al seleccionar
  los dos mayores; no se elimina un mes por coincidir su valor con el de otro.
- Las reglas de punta dependen del calendario aplicable y su vigencia, incluidos cambios
  horarios y excepciones; no se presume un horario universal para todos los suministros.
- Un mes de emisión y un ciclo de consumo son conceptos distintos; los límites reales del
  período y las reglas mensuales del perfil deben poder identificarse.
- Un intervalo que cruza un límite y no puede dividirse con evidencia conserva la política
  de las specs-001 y 002; no se prorratea su energía para cerrar artificialmente una boleta.
- Ajustes y créditos de la boleta pueden ser negativos; se conservan con su signo y no se
  confunden con mediciones negativas de consumo.
- Dos importes iguales no demuestran igualdad de conceptos, cobertura, impuestos o punto
  de medición. Las comparaciones incompletas deben seguir identificándose como tales.
- Cumplir el mínimo de conservación de datos originales no autoriza a perder los máximos,
  parámetros y evidencias necesarios para reproducir un cálculo todavía conservado.
- Un gráfico de costos no debe convertir cargos mensuales de demanda o fijos en cargos
  horarios ni repartirlos entre categorías mediante un criterio no solicitado.

## Requirements *(mandatory)*

### Functional Requirements

La sección presenta el costo BT4.3 como un desglose de componentes con base y procedencia,
según el perfil aplicable al suministro:

| Componente | Base que debe identificarse |
| --- | --- |
| Energía | Consumo del tablero general en kWh y precio aplicable. |
| Transmisión y servicio público | Consumo y componentes unitarios vigentes. |
| Cargo fijo | Importe y regla mensual aplicable. |
| Demanda en horas punta | Potencia de facturación en kW y calendario e historial utilizados. |
| Potencia suministrada | Potencia de facturación en kW e históricos utilizados. |
| Otros cargos aplicables e impuestos | Regla, base, vigencia y condición de aplicación documentadas. |

- **FR-001**: ECS-EC DEBE ofrecer una sección de costos con gráficos y tablas de evolución
  por ciclo y desglose por concepto, utilizando exclusivamente la opción tarifaria BT4.3.
- **FR-002**: Las cantidades medidas para el cálculo DEBEN provenir del tablero general
  identificado y asociado al suministro único del edificio, mediante CAT-01 de la spec-001.
  CAT-01 DEBE ser de origen medido por el medidor total; el total calculado admitido por
  la spec-001 NO DEBE sustituir esa base ni duplicarse con consumos parciales. Si no existe
  medidor total, DEBE identificarse la falta de la medición general y NO DEBE presentarse
  un costo energético completo del suministro a partir del total calculado.
- **FR-003**: El perfil BT4.3 DEBE identificar suministro, distribuidora y condiciones
  territoriales y técnicas relevantes, moneda, fuente documental, componentes, precios
  y unidades, reglas de demanda y punta, impuestos, redondeo y fechas de vigencia.
- **FR-004**: Solo DEBE aplicarse un perfil inequívoco para cada cargo y vigencia. Un dato
  obligatorio ausente, una superposición o una regla contradictoria DEBE impedir presentar
  el cálculo como completo y señalar qué debe corregirse; NO DEBE suplirse con cero.
  Cada revisión DEBE contener su calendario completo de segmentos sin superposiciones
  internas; publicar una nueva revisión sustituye la selección para cálculos nuevos sin
  modificar revisiones anteriores. La coincidencia de vigencias entre revisiones históricas
  NO DEBE tratarse como una superposición interna. Un borrador no cambia la selección publicada.
- **FR-005**: Cada componente DEBE mostrar cantidad o base, unidad, regla aplicada, precio
  o factor, importe y versión de referencia. El subtotal y el total DEBEN reconciliarse con
  el desglose y distinguir neto, impuestos e importes que ya los incluyan.
- **FR-006**: El componente de energía DEBE calcularse a partir de la suma de energía válida
  del tablero general contenida en el período de cálculo y los precios aplicables a sus
  vigencias. Los demás componentes energéticos DEBEN usar sus propias reglas y bases,
  sin sumar de nuevo la energía a la cantidad medida.
- **FR-007**: La demanda DEBE basarse en registros de potencia integrados en bloques de
  15 minutos o en energía que cubra exactamente esos bloques. En el segundo caso la
  potencia media en kW es la energía en kWh dividida por 0,25 horas. NO DEBE reconstruirse
  un máximo de 15 minutos desde datos horarios o de menor resolución temporal.
- **FR-008**: El cálculo DEBE distinguir máximos leídos y bases de facturación. El perfil
  inicial usa el promedio de los dos mayores máximos mensuales del historial de 12 meses,
  incluido el mes facturado, para potencia suministrada. En meses con punta usa el máximo
  efectivamente leído en punta; en meses sin punta usa el promedio de los dos mayores
  máximos mensuales de punta del período de punta inmediatamente anterior, conforme a la
  referencia normativa registrada.
  El mes de referencia de demanda DEBE resolverse mediante una regla documentada del perfil
  o evidencia explícita validada y conservarse con su fuente y versión de política. NO DEBE
  inferirse del mes de emisión, inicio o fin sin regla documental; si no se resuelve,
  los cargos dependientes DEBEN identificarse como no calculables.
- **FR-009**: El calendario de punta, los bloques de medición y las ventanas históricas
  DEBEN respetar la zona horaria, vigencia y reglas aplicables al suministro. DEBEN
  conservarse los meses y valores usados; la ausencia de históricos NO DEBE rellenarse
  con ceros ni con promedios de energía.
- **FR-010**: El cálculo DEBE incluir todos los cargos e impuestos aplicables identificados
  en el perfil, con su condición de aplicación. Un recargo que requiera una magnitud no
  disponible DEBE figurar como no calculable, no como inexistente. El consumo cero NO DEBE
  eliminar cargos independientes del consumo cuando correspondan.
- **FR-011**: DEBEN registrarse inicio y fin del ciclo de consumo, zona horaria y criterio
  de lectura de sus límites. Un contraste DEBE usar el ciclo de la boleta y las reglas
  de facturación del perfil; NO DEBE reemplazarlo automáticamente por el mes de emisión.
  El mes de demanda resuelto DEBE preservarse por revisión del cálculo; corregirlo NO DEBE
  modificar la evidencia de un cálculo anterior ni los límites del ciclo.
- **FR-012**: Una variación del perfil dentro del ciclo DEBE aplicar la regla de vigencia
  documentada de cada componente. NO DEBE asignar arbitrariamente cuotas diarias u horarias
  a cargos fijos o de demanda ni distribuir el costo entre las categorías parciales.
- **FR-013**: Gráficos y tablas DEBEN presentar los mismos ciclos, importes, moneda, bases
  tributarias y estados, diferenciando costo calculado, importe comparable facturado y
  total a pagar cuando sean conceptos distintos.
- **FR-014**: La sección DEBE indicar período en curso, cobertura de mediciones y suficiencia
  de históricos y parámetros. Con información parcial DEBE mostrar únicamente componentes
  calculables identificados y NO DEBE ofrecer su suma como un costo BT4.3 completo.
- **FR-015**: La persona DEBE poder registrar manualmente una boleta mensual con suministro,
  identificador, emisión, ciclo de consumo, cantidades de energía y demanda disponibles,
  conceptos e importes facturados, base tributaria, impuestos, total y referencia documental.
  DEBEN distinguirse cantidades leídas de bases de demanda ya facturadas.
- **FR-016**: La comparación DEBE alinear suministro, ciclo, moneda, concepto y base
  tributaria. DEBE mostrar los dos valores y la diferencia calculado menos facturado;
  el porcentaje es esa diferencia dividida por el valor absoluto del facturado y multiplicada
  por 100 cuando este no sea cero. Con facturado cero el porcentaje DEBE indicar que no aplica.
  Al consultar las últimas revisiones a un corte, solo DEBE usarse una comparación que
  referencie exactamente el cálculo y la revisión de boleta seleccionados. Si falta,
  DEBE indicarse contraste pendiente, conservar los valores disponibles y presentar
  diferencias ausentes; el ciclo NO DEBE integrar el contraste agregado ni recuperarse
  una comparación antigua como actual. La consulta NO DEBE crear comparaciones.
- **FR-017**: Los conceptos sin equivalente calculado DEBEN presentarse fuera del subtotal
  comparable, con explicación de su tratamiento. Deudas, intereses, cuotas, créditos y ajustes
  DEBEN conservar su signo y su relación con el ciclo; si tienen un equivalente calculado
  solo se comparan tras alinear sus bases. NO DEBEN atribuirse automáticamente a errores
  de medición.
- **FR-018**: Registrar una boleta NO DEBE modificar las mediciones, los parámetros del
  perfil ni el cálculo existente para forzar coincidencia. Una boleta ausente DEBE permitir
  consultar el costo calculado indicando que no existe contraste.
- **FR-019**: Repeticiones de identificador de boleta DEBEN detectarse. Correcciones de boleta,
  cambios de perfil y recálculos DEBEN generar revisiones con procedencia y fecha, preservando
  la evidencia anterior; cada comparación DEBE identificar las versiones utilizadas.
  El Administrador DEBE poder ejecutar cálculo/recálculo y crear el contraste de revisiones
  explícitas desde la web; el recálculo exige motivo y los reintentos de una misma operación
  NO DEBEN duplicar resultados. El suministro DEBE admitir alta inicial única y edición
  contra la revisión vigente, recuperable al abrir el editor; publicaciones concurrentes
  de perfil DEBEN detectar que cambió la última revisión antes de guardar.
- **FR-020**: Las mismas entradas, referencias y reglas de redondeo DEBEN producir los mismos
  resultados. La presentación DEBE declarar el criterio de redondeo y mantener la consistencia
  entre cada concepto, subtotal, impuestos, total y diferencia mostrados.
- **FR-021**: Cálculos, boletas, comparaciones y sus bases de reproducción DEBEN conservarse
  al menos 12 meses calendario desde su registro o revisión, conforme a las reglas temporales
  de la spec-002. DEBEN preservarse los máximos e históricos utilizados aunque parte del
  detalle original cumpla su plazo mínimo y deje de estar disponible.
- **FR-022**: La sección DEBE permitir consultar al menos 12 meses de historial cuando
  existan registros suficientes y mantener los estados de carga, ausencia de datos y error
  definidos en la spec-001. NO DEBE inventar datos anteriores al inicio de operación.
- **FR-023**: Las bases de reproducción DEBEN identificar el tablero general, mediciones
  o máximos de origen, cobertura, perfil y boleta utilizados. Diferencias conocidas respecto
  del punto de medición de la distribuidora DEBEN documentarse; NO DEBEN introducirse
  factores de ajuste sin una regla y evidencia registradas.

### Key Entities *(include if feature involves data)*

- **Suministro del edificio**: Identificación del servicio eléctrico, su tablero general,
  ubicación, distribuidora y condiciones que determinan el perfil BT4.3 aplicable.
- **Perfil BT4.3 versionado**: Conjunto de cargos, precios, reglas, impuestos, calendario,
  redondeo y vigencias, respaldado por fuentes documentales.
- **Ciclo de facturación**: Intervalo de consumo y referencias mensuales usados en un cálculo
  o boleta, con límites y zona horaria explícitos.
- **Base de demanda**: Bloques de potencia y máximos mensuales del tablero general,
  separados de las cantidades que finalmente se utilizan para facturar cada componente.
- **Cálculo de costo**: Revisión del desglose, cantidades, reglas, importes y estado de
  suficiencia para un ciclo, con sus referencias de reproducción.
- **Boleta registrada**: Datos del documento recibido del proveedor, su ciclo, conceptos,
  cantidades e importes, con identidad, referencia documental y revisiones.
- **Comparación de costos**: Relación entre un cálculo y una boleta versionados, con conceptos
  comparables, diferencias, exclusiones y evidencia utilizada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100 % de los casos de referencia completos, los cargos, bases de demanda,
  impuestos y totales coinciden con los resultados esperados después del redondeo definido,
  sin incorporar consumos de categorías diferentes al tablero general.
- **SC-002**: En el 100 % de los casos de contraste, se utilizan el suministro y ciclo correctos
  y se obtienen las diferencias esperadas, incluidos facturado cero, distintos tratamientos
  tributarios, créditos y cargos fuera del subtotal comparable.
- **SC-003**: Todos los escenarios de datos incompletos, resolución insuficiente, historial
  ausente y vigencias ambiguas identifican los componentes no calculables y ninguno presenta
  un total BT4.3 completo con información inventada.
- **SC-004**: Para el 100 % de los cálculos y comparaciones conservados durante sus 12 meses
  mínimos pueden identificarse las entradas y versiones utilizadas y reproducirse sus importes,
  incluidos casos con cambios tarifarios y correcciones de boleta.
- **SC-005**: En todos los escenarios de aceptación, gráfico y tabla coinciden en períodos,
  importes, bases tributarias, estados y diferencias mostradas.
- **SC-006**: En al menos 9 de 10 tareas con personas representativas de la administración
  del edificio, la persona identifica sin ayuda el costo calculado, el importe comparable
  de la boleta, su período y la diferencia en un máximo de dos minutos por tarea.

## Assumptions

- **Alcance de suministro**: Se trabaja con un edificio, un suministro general y una única
  opción BT4.3. CAT-01 debe identificar el tablero general correspondiente y ser de origen
  medido para este análisis; la compatibilidad con totales calculados de la spec-001 no
  cambia esa exigencia. No se implementan
  reparto de costos por categoría, comparación entre tarifas ni optimización de contratos.
- **Marco de referencia**: La caracterización se apoya en las
  [opciones tarifarias descritas por la CNE](https://www.cne.cl/en/tarificacion/electrica/valor-agregado-de-distribucion/opciones-tarifarias-a-usuarios-finales/).
  Para el perfil inicial se consideran las secciones 3.4 y 4.8 del
  [Decreto 5T de 2024 publicado por la CNE](https://www.cne.cl/wp-content/uploads/2025/08/Decreto-5T-2024-Toma-de-razon.pdf)
  y la descripción de componentes y demanda de
  [BT4.3 publicada por Enel](https://www.enel.cl/es/clientes/tarifas-y-regulacion/conceptos-tarifas.html).
  Las fuentes se consultaron el 2026-11-01; cada suministro y período debe usar su pliego y
  reglas efectivamente aplicables. La referencia de Enel no asigna esa distribuidora al edificio.
- **Valores tarifarios**: Se usa CLP como moneda inicial. Distribuidora, ubicación, condiciones
  de conexión, precios, impuestos y calendario deben proporcionarse con sus fuentes y vigencias
  antes del cálculo completo. No se fijan precios reales ni una tasa tributaria universal
  en esta especificación. Las cifras de los escenarios son exclusivamente datos de prueba.
- **Datos para demanda**: La frecuencia de recepción de la spec-002 no sustituye la resolución
  de medición. Se requieren bloques válidos de demanda de 15 minutos o energía suficiente
  para formarlos exactamente. Los datos horarios, diarios o mensuales por sí solos no bastan.
- **Historial inicial**: Para completar cargos históricos se requieren los máximos y cobertura
  que exija el perfil. Pueden incorporarse antecedentes verificables del mismo tablero general;
  los importes o potencias facturados de una boleta no se convierten automáticamente en
  mediciones independientes para hacer coincidir la comparación.
- **Registro de boleta**: La entrada inicial es manual y guarda referencia al documento.
  No se requieren carga de PDF, reconocimiento automático de texto ni conexiones a la
  distribuidora. Si la boleta no detalla un concepto o un límite temporal, se registra esa
  limitación y no se afirma una comparación exacta de información que no posee.
- **Calendario de comparación**: El ciclo real de facturación puede cruzar meses calendario.
  Sus límites se registran como inicio incluido y fin excluido. Si solo hay fechas y se
  asumen horas para consultar, el criterio debe mostrarse y la comparación se identifica
  como limitada hasta confirmar las referencias temporales.
- **Costos y estados**: Los resultados son cálculos del costo según mediciones y perfil,
  identificados separadamente de la boleta emitida. Un ciclo en curso no incluye proyección
  de consumo futuro. Los recargos cuya condición no pueda determinarse permanecen pendientes.
- **Dependencias y relación con specs previas**: Esta sección amplía el alcance anterior que
  excluía costos. Reutiliza los datos normalizados y su calidad de las specs-001 y 002,
  y admite los escenarios de prueba de la spec-003. El plan debe verificar el pliego del
  suministro, la cobertura histórica, el método de redondeo y las reglas de vigencia y punta.
- **Gobierno y límites**: Aplican la arquitectura monolítica y la documentación integral
  de la constitución. No se implementan pagos, emisión de boletas oficiales, reclamaciones
  automáticas ni nuevos protocolos de recepción de mediciones.
