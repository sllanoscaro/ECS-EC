# Feature Specification: Reportes PDF de una página por período

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "ECS-EC debe generar reportes detallados en PDF con resúmenes
acordes a las especificaciones anteriores. El resumen debe ocupar como máximo una página
y permitir personalizar el período: diario, mensual o anual, según la elección del usuario."

**Clarificación recibida**: Para costos se incluyen los ciclos de facturación que cierran
en el período elegido, mostrando sus fechas y alcance.

**Especificaciones relacionadas**:
[spec-001: consumo por categorías](../001-visualizar-consumo-categorias/spec.md),
[spec-002: registros e historial](../002-registro-retencion-consumo/spec.md),
[spec-003: simulación y calidad de datos](../003-simulador-pas600-sftp/spec.md) y
[spec-004: costos BT4.3 y boletas](../004-costos-tarifa-bt43/spec.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Elegir el período y descargar su resumen (Priority: P1)

Como persona encargada del edificio, quiero elegir un día, mes o año y descargar su resumen
en PDF para comunicar el estado del consumo, los costos disponibles y la calidad de los datos.

**Why this priority**: Es el flujo principal de la funcionalidad solicitada.

**Independent Test**: Preparar información conocida para un día, un mes y un año; seleccionar
cada período y comprobar las fechas y el contenido de los archivos descargados.

**Acceptance Scenarios**:

1. **Given** información disponible de varios períodos, **When** se elige el tipo diario
   y una fecha, **Then** el reporte cubre ese día calendario en la zona horaria del edificio.
2. **Given** una selección mensual o anual, **When** se elige un mes y año o un año,
   **Then** el reporte cubre respectivamente ese mes completo o ese año calendario,
   con sus límites identificados.
3. **Given** un período válido, **When** se solicita su generación, **Then** se informa el
   progreso y se ofrece descargar un PDF cuyo nombre e identificación reconocen el edificio,
   el tipo de resumen y el período.
4. **Given** una selección incompleta, una fecha inexistente o un período totalmente futuro,
   **When** se solicita generar, **Then** se explica la corrección necesaria y no se entrega
   un archivo presentado como un reporte válido.
5. **Given** un período que todavía está en curso, **When** se genera, **Then** se mantienen
   sus límites calendario y se identifican el corte de datos y el carácter provisional,
   sin proyectar valores para el resto del período.
6. **Given** un fallo de generación o descarga, **When** se informa el error, **Then** se
   conservan las opciones elegidas y se permite reintentar sin alterar los datos de origen.

---

### User Story 2 - Leer las siete categorías en una sola página (Priority: P1)

Como persona que recibe el reporte, quiero reconocer los consumos y su evolución en una
página legible para revisar la información esencial sin recorrer todas las vistas de ECS-EC.

**Why this priority**: La síntesis debe mantener el contenido esencial y cumplir el límite de página.

**Independent Test**: Generar reportes con las siete categorías, valores conocidos, nombres
largos y un año de datos; comprobar el número de páginas, la legibilidad y sus cifras.

**Acceptance Scenarios**:

1. **Given** datos para las siete categorías, **When** se genera el resumen, **Then** contiene
   una tabla con las siete categorías, energía en kWh, cobertura y estado; el total de
   CAT-01 conserva el origen medido o calculado establecido por la spec-001,
   con su base y alcance visibles cuando es calculado.
2. **Given** un reporte diario, mensual o anual, **When** se lee su gráfico temporal,
   **Then** muestra la evolución de CAT-01 agrupada por horas, días o meses,
   respectivamente, con unidad, fechas y vacíos distinguibles.
3. **Given** un año completo y textos o cifras extensos, **When** se genera el PDF,
   **Then** el archivo completo tiene una sola página, conserva las secciones obligatorias
   y no tiene recortes, solapamientos ni texto ilegible al imprimirlo al tamaño previsto.
4. **Given** un PDF descargado, **When** se abre sin acceso a ECS-EC, **Then** pueden
   interpretarse edificio, período, unidades, alcance de costos y estados sin consultar
   leyendas o contenido indispensable que solo exista en la plataforma.
5. **Given** datos cuyo detalle no cabe en una página, **When** se compone el reporte,
   **Then** se usan resúmenes y agrupaciones definidas, conservando las siete categorías
   y las advertencias; no se agregan anexos ni se oculta contenido esencial para lograr el límite.
6. **Given** una instalación sin medidor total, con CAT-03 y CAT-05 presentes y un total
   calculado válido de 20 kWh, **When** se genera el PDF, **Then** CAT-01 identifica el
   origen calculado y ambas categorías de la base, las categorías sin medidor conservan
   ese estado y la sección BT4.3 identifica la falta de medición general sin utilizar
   esos 20 kWh como base de costos del suministro.

---

### User Story 3 - Entender los costos y el contraste con boletas (Priority: P1)

Como persona responsable del edificio, quiero conocer los costos y diferencias con boletas
de los ciclos cerrados en el período para interpretar sus importes con el alcance correcto.

**Why this priority**: Los ciclos de facturación pueden cruzar los límites del período
calendario del resumen de energía.

**Independent Test**: Preparar ciclos de facturación que cierren dentro y fuera del período,
con cálculos completos, parciales y boletas disponibles solo para algunos de ellos.

**Acceptance Scenarios**:

1. **Given** un reporte de noviembre y un ciclo que consume entre octubre y noviembre y
   cierra en noviembre, **When** se genera, **Then** ese ciclo se incluye en la sección de
   costos con sus fechas, aunque parte de su consumo sea anterior al período energético.
2. **Given** un ciclo que se solapa con el período pero cierra fuera de él, **When** se
   genera el reporte, **Then** no se incorpora a sus importes por cierre ni se prorratean
   sus cargos para incluir una fracción.
3. **Given** varios ciclos cerrados y boletas comparables para un subconjunto, **When** se
   muestran diferencias agregadas, **Then** calculado, facturado y diferencia corresponden
   exactamente a los mismos ciclos y conceptos comparables y se informa cuántos pares hay.
   Con costos de prueba de 10, 20 y 30 CLP y boletas solo para el primero y tercero por
   9 y 29 CLP, el contraste muestra 40 frente a 38 CLP, diferencia de 2 CLP y dos pares;
   los 60 CLP disponibles se identifican aparte con su alcance de tres ciclos.
4. **Given** un ciclo sin cálculo completo o sin boleta, **When** se resume, **Then** se
   identifica la limitación; no se trata el importe faltante como cero ni se presenta un
   subtotal de ciclos disponibles como el costo completo de todos los ciclos.
5. **Given** un día o mes sin cierres de facturación, **When** se genera su resumen,
   **Then** se indica "Sin ciclos de facturación cerrados en el período", manteniendo
   disponible el resumen de energía.
6. **Given** varias revisiones de una boleta o cálculo para el mismo ciclo, **When** se
   genera, **Then** se usa la revisión vigente al corte y ese ciclo se cuenta una sola vez.
7. **Given** créditos, impuestos o importes no comparables, **When** se exporta su resumen,
   **Then** se conserva el tratamiento de la spec-004, incluido el signo y la distinción
   entre costo calculado, subtotal comparable y total a pagar.

---

### User Story 4 - Reconocer datos incompletos y la procedencia del reporte (Priority: P2)

Como persona que revisa el PDF, quiero reconocer la cobertura y procedencia de sus datos
para distinguir un período completo, uno parcial y otro sin información disponible.

**Why this priority**: Un documento descargado debe conservar el significado y las
limitaciones de la información que presenta la plataforma.

**Independent Test**: Generar reportes con datos ausentes, ceros medidos, agregados históricos,
orígenes simulados identificados y cambios recibidos durante la generación.

**Acceptance Scenarios**:

1. **Given** una categoría sin registros y otra con ceros medidos, **When** se genera,
   **Then** la primera indica "Sin datos" y la segunda muestra su cero y cobertura reales.
2. **Given** un período con huecos, datos rechazados o intervalos excluidos, **When** se
   resume, **Then** se usa únicamente la información aceptada y se mantienen cobertura
   y limitaciones, sin completar valores mediante ceros o estimaciones.
3. **Given** un período histórico sin datos disponibles en ninguna categoría, **When** se
   solicita el reporte, **Then** se permite descargar una página que identifica la
   ausencia de datos y no inventa consumos o costos.
4. **Given** un agregado anual conservado y parte de su detalle mensual retirado, **When**
   se genera el resumen anual, **Then** se mantiene el total anual válido y el gráfico
   identifica el detalle no disponible, sin reemplazar ese total por una suma parcial.
5. **Given** nuevas mediciones o revisiones recibidas mientras se genera, **When** finaliza
   el reporte, **Then** todas sus cifras y referencias corresponden al mismo corte de datos;
   una generación posterior puede reflejar los cambios con una nueva identificación.
6. **Given** datos de un origen identificado como simulado o de pruebas,
   **When** se incorporan al reporte, **Then** esa procedencia queda visible sin añadir
   información de credenciales o configuración técnica del simulador.
7. **Given** las mismas opciones, datos y revisiones al mismo corte, **When** se vuelve a
   generar, **Then** coinciden los valores, agrupaciones y estados, aunque la identificación
   y la fecha de emisión del nuevo documento sean distintas.

### Edge Cases

- Un día puede tener una duración diferente de 24 horas; febrero y los años bisiestos se
  interpretan según el calendario y zona horaria del edificio.
- El período tiene inicio incluido y fin excluido. Un cierre exactamente en el fin del
  período pertenece al siguiente; uno exactamente en el inicio se incluye si ya ocurrió.
- Un ciclo todavía abierto no se convierte en cerrado porque su fecha de fin esté prevista
  dentro del período elegido; debe haber alcanzado su cierre al corte de datos.
- La energía del período calendario y los importes por ciclos cerrados tienen alcances
  distintos; esa diferencia debe quedar visible dentro del propio PDF.
- La falta de boleta no significa facturado cero ni una diferencia de cobro del 100 %.
- La cobertura de las siete categorías puede ser distinta. Una categoría completa no
  convierte en completos el tablero general ni los costos. Las categorías sin medidor
  se distinguen de lecturas faltantes y no se muestran como consumo cero.
- Un agregado válido puede conservar más información que el detalle disponible; se
  mantienen su procedencia y cobertura en lugar de recalcularlo desde datos incompletos.
- Una omisión del simulador o un registro rechazado no es una medición de consumo cero.
  Los defectos cuyo período no puede identificarse no se contabilizan arbitrariamente en el resumen.
- Textos largos y valores extremos no permiten eliminar categorías o advertencias ni
  reducir indefinidamente el tamaño de letra.
- Solicitar varios reportes no es una actualización de mediciones y no queda limitado por
  la separación mínima de 15 minutos de recepción de las specs-002 y 003.

## Requirements *(mandatory)*

### Functional Requirements

El contenido obligatorio se sintetiza con esta prioridad dentro de la misma página:

| Sección | Contenido mínimo |
| --- | --- |
| Identificación | ECS-EC, edificio, tipo de reporte, período, zona horaria, emisión y corte. |
| Consumo | Siete categorías con energía en kWh, cobertura y estado; CAT-01 con origen medido o calculado identificado. |
| Evolución | Gráfico de CAT-01 con agrupación horaria, diaria o mensual según el resumen. |
| Costos BT4.3 | Ciclos cerrados seleccionados, alcance temporal, importes disponibles y estado de completitud. |
| Contraste con boletas | Importes comparables y diferencias sobre el mismo conjunto de pares o motivo de ausencia. |
| Calidad y procedencia | Limitaciones de datos y cálculo, origen de pruebas cuando esté identificado y referencia del reporte. |

- **FR-001**: ECS-EC DEBE permitir generar y descargar un reporte PDF a solicitud de la
  persona usuaria con selección de resumen diario, mensual o anual.
- **FR-002**: La selección DEBE permitir elegir una fecha, un mes y año o un año, respectivamente.
  El intervalo DEBE corresponder al período calendario elegido en la zona horaria del edificio,
  con inicio incluido y fin excluido.
- **FR-003**: Una selección incompleta, inexistente o totalmente futura DEBE impedir la
  generación e indicar su corrección. Un período actual DEBE admitirse como en curso;
  un período pasado sin datos DEBE permitir un reporte explícito de ausencia de información.
- **FR-004**: Cada generación exitosa DEBE producir un PDF completo de exactamente una página,
  sin anexos ni páginas vacías adicionales, con todas las secciones obligatorias.
- **FR-005**: El formato inicial DEBE ser A4 vertical, imprimible al 100 % sin recortes ni
  solapamientos. Todo el texto, incluido el de tablas, ejes, notas y leyendas, DEBE tener
  al menos 10 puntos.
  Si la composición no cumple el límite y legibilidad, NO DEBE entregarse como exitosa.
- **FR-006**: La síntesis DEBE conservar las siete categorías de la spec-001 con nombres
  inequívocos, energía, unidad, cobertura y estado, incluso si algunas no tienen datos.
  CAT-01 DEBE conservar su origen medido o calculado conforme a la spec-001; un total
  calculado DEBE indicar su base y alcance. NO DEBE sumarse nuevamente con las categorías
  que contribuyeron a él. Las categorías sin medidor DEBEN identificarse como tales.
- **FR-007**: El gráfico DEBE representar la evolución de CAT-01 usando horas para el reporte
  diario, días para el mensual y meses para el anual. DEBE indicar unidades, referencia temporal,
  vacíos y cobertura parcial sin interpolar consumos ausentes, desambiguando las horas repetidas
  conforme a la spec-002. Sin datos DEBE mostrar ese estado sin inventar una curva.
- **FR-008**: Los valores y estados energéticos DEBEN usar las reglas y agregados de las
  specs-001 y 002 al corte de generación. Si existe un total conservado válido pero falta detalle
  para el gráfico, DEBE conservarse el total e indicarse la falta de detalle; NO DEBE
  sustituirse por una suma incompleta ni presentar esa gráfica como completa.
- **FR-009**: Una categoría sin medidor DEBE distinguirse de una instalada sin datos y
  de un consumo cero válido, medido o calculado. Un total calculado incompleto DEBE
  conservar ese estado y las categorías faltantes conforme a la spec-001.
  El reporte NO DEBE inventar mediciones, completar huecos, incorporar registros rechazados
  ni contar defectos en períodos a los que no puedan asociarse con evidencia.
- **FR-010**: El resumen de costos DEBE seleccionar los ciclos cuyo instante efectivo de fin
  esté dentro del período elegido y sea anterior o igual al corte de datos. DEBE indicar
  que sus importes se agrupan por cierre de ciclo, mostrar la cantidad de ciclos y el
  alcance de sus fechas de consumo, aunque excedan el período energético del reporte.
- **FR-011**: La sección financiera DEBE reutilizar cálculos, moneda, bases tributarias,
  redondeo y revisiones de la spec-004. NO DEBE recalcular una tarifa distinta ni repartir
  cargos mensuales entre días, horas o categorías para hacerlos coincidir con el reporte.
- **FR-012**: Los importes agregados DEBEN distinguir ciclos con cálculo completo, parcial
  o ausente. La suma de ciclos calculables DEBE identificarse como subtotal disponible
  cuando no cubra todos los seleccionados; los importes desconocidos NO DEBEN asumirse cero.
- **FR-013**: El contraste agregado DEBE usar los mismos ciclos, conceptos y bases en sus
  dos lados. DEBE indicar la cantidad de pares comparables y mostrar calculado, facturado
  y diferencia conforme a la spec-004, separadamente de totales con otro alcance.
- **FR-014**: Sin ciclos cerrados, sin boletas o sin conceptos comparables DEBE mostrarse
  el motivo correspondiente. Esa ausencia NO DEBE impedir generar el resumen de energía
  ni producir diferencias ficticias o un costo completo sin información suficiente.
- **FR-015**: Cada ciclo DEBE contarse una sola vez usando las revisiones vigentes de cálculo
  y boleta al corte. Créditos, ajustes, impuestos y conceptos no comparables DEBEN mantener
  su tratamiento y signo conforme a la spec-004.
- **FR-016**: El PDF DEBE identificar período, zona horaria, fecha de emisión, corte de datos,
  referencia del reporte y los estados temporales y de completitud de cada sección,
  incluidas las situaciones en curso, completas, incompletas y sin información disponible.
  La información indispensable para interpretarlo DEBE estar contenida en la misma página.
- **FR-017**: Todas las secciones DEBEN corresponder a una captura coherente de datos y
  revisiones al mismo corte, fijado al inicio de la generación. La generación NO DEBE modificar
  mediciones, tarifas, boletas ni las reglas de aceptación o conservación anteriores.
- **FR-018**: Los valores DEBEN coincidir con las consultas equivalentes de la plataforma
  para el mismo período, corte, agrupaciones y revisiones. La presentación compacta DEBE
  conservar unidades y reglas de precisión o redondeo, sin convertir un consumo positivo
  pequeño en un cero aparente ni ocultar limitaciones para reducir espacio.
- **FR-019**: Los datos de procedencia simulada o de pruebas identificada DEBEN señalarse
  visiblemente. El reporte DEBE limitarse a información operativa y NO DEBE incluir secretos
  ni el informe local de control del simulador como si fueran mediciones recibidas.
- **FR-020**: La generación DEBE mostrar progreso, finalización o error. Ante fallo DEBE
  conservar la selección para reintentar y NO DEBE ofrecer un archivo incompleto o corrupto
  como descarga exitosa.
- **FR-021**: El archivo descargado DEBE poder abrirse e interpretarse sin conexión a ECS-EC.
  Su nombre DEBE distinguir edificio, escala y período. Una nueva generación DEBE poder
  identificarse sin alterar un documento ya emitido.
- **FR-022**: Las mismas opciones y datos versionados al mismo corte DEBEN producir los
  mismos valores, agrupaciones y estados. La nueva emisión puede cambiar sus metadatos
  de identificación y fecha, pero no los resultados sin un cambio de entradas.

### Key Entities *(include if feature involves data)*

- **Solicitud de reporte**: Edificio, escala diaria, mensual o anual, fecha o período elegido
  y zona horaria que determinan el resumen solicitado.
- **Captura del resumen**: Información energética, calidad, cálculos y referencias vigentes
  al mismo corte; conserva su alcance sin incorporar datos de otra generación.
- **Resumen energético**: Las siete categorías, sus valores, cobertura, estados y la
  evolución del tablero general con la agrupación adecuada.
- **Conjunto financiero por cierre**: Ciclos cerrados dentro del intervalo, con sus fechas
  efectivas, revisiones, importes disponibles y subconjunto de pares comparables.
- **Reporte emitido**: Documento PDF de una página con identificación, fecha, corte,
  contenido obligatorio y condiciones de interpretación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En todos los escenarios válidos de referencia, incluidos reportes anuales,
  nombres largos, valores extremos y datos incompletos, se obtiene exitosamente un PDF de
  exactamente una página A4, sin recortes ni solapamientos y con todo el texto de al menos 10 puntos.
- **SC-002**: En las tres escalas, el 100 % de los valores energéticos y estados coincide con
  las consultas equivalentes de la plataforma para las siete categorías y el mismo corte,
  incluidos días con cambios horarios y años bisiestos.
- **SC-003**: En todos los casos financieros de referencia se seleccionan únicamente los
  ciclos cerrados correspondientes, sin duplicarlos ni prorratearlos; cada comparación
  utiliza exactamente los mismos pares y bases en ambos lados.
- **SC-004**: Todos los escenarios de ausencia de información, ceros medidos, datos parciales,
  origen simulado y falta de boleta mantienen sus estados y limitaciones visibles en el PDF.
- **SC-005**: El 100 % de los archivos descargados en los casos de referencia se abre sin
  conexión a ECS-EC y permite interpretar período, unidades y alcance financiero.
- **SC-006**: En al menos 9 de 10 tareas con personas representativas del monitoreo del
  edificio, se elige el período, se descarga el PDF y se identifican consumo total,
  cobertura y situación de costos sin ayuda en un máximo de dos minutos.

## Assumptions

- **Límite del documento**: Se interpreta el máximo de una página como el PDF completo,
  no una portada seguida de anexos. El formato inicial es A4 vertical; no se solicita un
  editor de diseño ni personalización de papel, colores o secciones obligatorias.
- **Personalización temporal**: Se elige un día, mes o año concreto del calendario.
  No se incluyen rangos arbitrarios de varias fechas ni resúmenes semanales u horarios
  como tipos adicionales; la escala horaria se utiliza dentro de la evolución diaria.
- **Contenido de síntesis**: La tabla conserva las siete categorías y el gráfico resume
  CAT-01. No se exportan todas las filas de mediciones ni las siete vistas gráficas completas;
  el detalle operativo sigue disponible en las secciones de la plataforma.
- **Decisión sobre costos**: La persona solicitante confirmó la inclusión de ciclos que
  cierren en el período elegido. Su importe puede representar consumos que empezaron
  antes del intervalo energético del PDF; sus fechas y el criterio por cierre se muestran.
  El período de emisión de una boleta no sustituye el fin efectivo del ciclo.
- **Alcance financiero**: Se presentan cantidades de ciclos y el costo disponible, con
  estados de completitud; la comparación usa un subconjunto pareado explícito cuando falten
  boletas o cálculos comparables. El resumen no introduce nuevas fórmulas BT4.3 ni distribuye
  un cargo mensual para obtener un supuesto costo diario.
- **Datos disponibles e historial**: Se reutilizan los agregados e históricos conservados
  bajo las specs-002 y 004. Un año calendario no equivale necesariamente a los últimos
  12 meses; los períodos no conservados se identifican como indisponibles, sin inventarlos.
  La falta de detalle no invalida automáticamente un agregado que sí permanece válido.
- **Procedencia de pruebas**: La spec-003 aporta escenarios para verificar los reportes.
  La marca de datos simulados se obtiene de orígenes ya identificados en su configuración
  de correspondencias, sin agregar campos propios a los archivos nativos PAS600 ni exigir
  al backend el informe local privado del simulador.
- **Emisión y descarga**: La generación es a solicitud de la persona usuaria y entrega un
  archivo descargable; no se incluyen envío por correo, publicación SFTP ni programación
  automática de reportes. La frecuencia mínima de recepción de mediciones no limita esta operación.
- **Dependencias y gobierno**: Se requieren las consultas y resultados coherentes de las
  specs-001 a 004 y la identificación del edificio y su zona horaria. El plan debe comprobar
  composición de una página, legibilidad y correlación de datos y revisiones, manteniendo
  la arquitectura monolítica y la documentación integral establecidas en la constitución.
