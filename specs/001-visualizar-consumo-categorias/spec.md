# Feature Specification: Consumo eléctrico por categorías

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "La plataforma ECS-EC recibe datos de uso de energía eléctrica
por separado para: 1. Energía eléctrica total; 2. Sistema de calefacción, ventilación,
aire acondicionado HVAC y agua caliente sanitaria; 3. Iluminación exterior;
4. Iluminación interior; 5. Circuitos de enchufes; 6. Sistema sanitario (agua potable
y alcantarillado); 7. Ascensores. Cada categorización debe poder visualizarse mediante
gráficos y tablas."

**Clarificación recibida**: La instalación real puede disponer de solo algunas de las
categorías del catálogo. CAT-01 admite un total medido directamente o un total calculado
sumando las categorías presentes; no se exige disponer de siete medidores físicos.

**Entornos de ejecución**: El desarrollo actual es exclusivamente local. El producto final
se desplegará como monolito en una VPS y ofrecerá acceso web por internet desde redes
externas al edificio. La pila tecnológica permanece pendiente de definición.

## Clarifications

### Session 2026-11-01

- Q: ¿Se requieren siete medidores y una medición directa del total en todas las instalaciones? → A: No; algunas categorías pueden no estar presentes y el total puede ser medido directamente o calculado desde las categorías presentes.
- Q: Cuando el total se calcula sumando las categorías instaladas, ¿qué debe ocurrir si falta la lectura de alguna de ellas para un intervalo? → A: No calcular el total de ese intervalo y mostrar datos incompletos hasta disponer de lecturas válidas de todas las categorías instaladas; las categorías sin medidor se excluyen de la base de cálculo.
- Q: Si hay un medidor de energía total instalado pero falta su lectura para un intervalo, ¿debe el sistema calcular ese total usando las categorías presentes? → A: No; con medidor total se usa su lectura y se muestra "Sin datos" cuando falta. El total se calcula únicamente en instalaciones sin medidor total.
- Q: ¿Debe el total calculado desde las categorías presentes poder utilizarse también en el análisis de costos BT4.3 de la spec-004? → A: No; los costos BT4.3 requieren un medidor total asociado al suministro general. El total calculado se admite en visualización, historial, PDF y reglas de consumo, con su procedencia y alcance visibles.
- Q: ¿En qué entornos se desarrollará y se desplegará ECS-EC? → A: El desarrollo actual es exclusivamente local; el producto final se desplegará en una VPS y será accesible por internet desde cualquier ubicación, con los permisos existentes. La pila tecnológica aún no está definida.
- Q: Durante el desarrollo local, ¿las pruebas funcionales deben poder ejecutarse sin depender de servicios remotos de correo, observabilidad o recepción de archivos? → A: Sí; deben poder ejecutarse con componentes o sustitutos de prueba locales, sin requerir servicios remotos ni la futura VPS. La integración definitiva se verificará durante la etapa de despliegue.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar cada categoría mediante gráficos y tablas (Priority: P1)

Como persona encargada de monitorear el edificio, quiero consultar un gráfico y una tabla
de cada categoría para reconocer la evolución del consumo y revisar sus valores exactos.

**Why this priority**: Es el resultado principal solicitado: las siete categorías deben
ser identificables y consultables en ambas representaciones.

**Independent Test**: Preparar instalaciones completas y con categorías ausentes, con total
medido y con total calculado; comprobar valores, procedencia, etiquetas y períodos de sus
gráficos y tablas, incluidas las categorías sin medidor.

**Acceptance Scenarios**:

1. **Given** una instalación con solo algunas categorías medidas, **When** la persona abre
   la consulta, **Then** puede identificar y seleccionar las siete categorías del catálogo,
   distinguiendo las que carecen de medidor sin impedir consultar las disponibles.
2. **Given** una categoría con mediciones, **When** la selecciona, **Then** puede consultar
   un gráfico temporal y una tabla de esa categoría, con nombre, unidad, período y zona horaria;
   para CAT-01 se identifica si el total es medido o calculado y, en este último caso, su base.
3. **Given** las mismas mediciones y período, **When** compara ambas vistas, **Then** cada
   valor e intervalo del gráfico corresponde con una fila de la tabla, sin mezclar categorías.
4. **Given** un total recibido de 100 kWh y seis consumos parciales de 10 kWh cada uno para
   el mismo intervalo, **When** consulta energía eléctrica total, **Then** ambas vistas
   muestran 100 kWh identificados como total medido y no lo reemplazan por la suma de los
   consumos parciales ni añaden estos al total.
5. **Given** una instalación sin medidor total con solo CAT-03 y CAT-05 presentes y lecturas
   de 12 y 8 kWh para el mismo intervalo, **When** se consulta CAT-01 calculada,
   **Then** ambas vistas muestran 20 kWh como total calculado de las categorías presentes,
   identifican CAT-03 y CAT-05 como base y no atribuyen consumo a las categorías sin medidor.
6. **Given** la documentación de preparación y una configuración de desarrollo local,
   con datos y dependencias de prueba locales, **When** se inicia ECS-EC y se consulta una
   categoría con una cuenta de prueba autorizada, **Then** se obtiene su gráfico y tabla
   sin disponer de una VPS ni depender de servicios remotos para esa prueba funcional.
7. **Given** el producto desplegado en la VPS durante su validación final,
   **When** una persona con cuenta activa accede desde una red de internet externa al
   edificio y al equipo de desarrollo, **Then** puede autenticarse y consultar sus datos
   permitidos mediante la dirección pública de la aplicación, sin requerir conexión a la
   red local del edificio ni mantener encendido el equipo de desarrollo.

---

### User Story 2 - Recibir mediciones separadas y confiables (Priority: P1)

Como persona responsable del monitoreo, quiero que ECS-EC conserve las mediciones recibidas
en su categoría correspondiente para consultar información fiel a su origen.

**Why this priority**: Las visualizaciones requieren datos separados, identificables y
sin duplicaciones que alteren el significado del consumo.

**Independent Test**: Enviar mediciones conocidas y comprobar el resultado de recepción y
el conjunto aceptado, incluyendo reenvíos y registros inválidos, sin depender de los gráficos.

**Acceptance Scenarios**:

1. **Given** mediciones válidas de las categorías presentes, **When** se reciben, **Then**
   quedan disponibles para consulta con categoría, origen, valor, unidad e intervalo originales,
   sin exigir registros ni medidores de las categorías ausentes.
2. **Given** una medición aceptada, **When** se reenvía el mismo origen, categoría, intervalo
   y valor equivalente, **Then** se informa como duplicada y se conserva una única medición.
3. **Given** una medición aceptada, **When** llega otra con el mismo origen, categoría e
   intervalo pero distinto valor, **Then** se informa un conflicto y no se reemplaza la aceptada.
4. **Given** registros con categoría desconocida, valor inválido o no finito, unidad incompatible o
   intervalo incompleto, **When** se reciben, **Then** se rechazan con una causa identificable
   y las mediciones válidas recibidas junto a ellos siguen siendo consultables.
5. **Given** mediciones válidas en Wh, kWh o MWh y recibidas fuera de orden temporal,
   **When** se consultan, **Then** sus valores equivalentes se muestran en kWh y ordenados
   cronológicamente, conservando su información de origen.
6. **Given** un intervalo ya aceptado, **When** llega otro distinto que se superpone en la
   misma categoría, **Then** el nuevo se rechaza sin cambiar el aceptado; un intervalo
   contiguo sí se acepta.

---

### User Story 3 - Consultar un período específico (Priority: P2)

Como persona encargada del edificio, quiero elegir el período de consulta para revisar el
consumo de una categoría dentro de los mismos límites en el gráfico y la tabla.

**Why this priority**: Permite interpretar los valores en un contexto temporal explícito.

**Independent Test**: Preparar mediciones antes, dentro y después de un período elegido;
comprobar la selección temporal en ambas vistas y al cambiar de categoría.

**Acceptance Scenarios**:

1. **Given** mediciones de varios días, **When** se elige un período válido, **Then** ambas
   vistas muestran únicamente mediciones cuyo intervalo esté contenido completamente en él.
2. **Given** un período seleccionado, **When** se cambia de categoría o representación,
   **Then** el período se conserva y las etiquetas identifican la categoría activa.
3. **Given** un inicio igual o posterior al fin, **When** se intenta consultar, **Then** se
   explica cómo corregir el período y se conserva la última consulta válida.
4. **Given** una medición que cruza un límite del período elegido, **When** se consulta,
   **Then** no se prorratea ni se incluye parcialmente y se informa que existen mediciones
   excluidas por cruzar los límites.
5. **Given** mediciones en un cambio de día o de horario estacional, **When** se consultan,
   **Then** las fechas incluyen la zona y el desfase horario necesarios para distinguir
   sus intervalos, sin omitirlos ni duplicarlos por su hora local.
6. **Given** mediciones aceptadas y ninguna selección previa, **When** se abre la consulta,
   **Then** el período inicial cubre desde el inicio más antiguo hasta el fin más reciente
   de las mediciones del edificio, compartido por las siete categorías.

---

### User Story 4 - Reconocer ausencia de datos y fallos de consulta (Priority: P2)

Como persona encargada del edificio, quiero distinguir un consumo cero, la falta de
mediciones y un fallo de consulta para no interpretar información incompleta como consumo real.

**Why this priority**: Evita conclusiones incorrectas cuando una categoría no tiene datos
o sus mediciones no pueden consultarse.

**Independent Test**: Preparar una categoría sin mediciones, otra con cero medido y otra
con intervalos faltantes; simular una consulta fallida y verificar cada estado visible.

**Acceptance Scenarios**:

1. **Given** una categoría con medidor configurado pero sin mediciones en el período,
   **When** se consulta, **Then** ambas vistas indican "Sin datos" y no generan valores
   cero ni filas ficticias.
2. **Given** una medición válida de cero, **When** se consulta, **Then** ambas vistas muestran
   ese cero como una medición y lo distinguen de la ausencia de datos.
3. **Given** intervalos conocidos con un vacío entre ellos, **When** se consulta, **Then** el
   gráfico deja visible el vacío y la tabla contiene únicamente datos válidos, recibidos
   o calculados conforme a FR-006.
4. **Given** una consulta en curso o fallida, **When** se muestra su estado, **Then** se
   distingue carga de error; ante error se ofrece reintentar y no se presentan valores de
   otra categoría o período como resultados actuales.
5. **Given** una categoría sin datos o con error y otra disponible, **When** se selecciona
   la segunda, **Then** puede consultarse sin depender del estado de la primera.
6. **Given** una categoría parcial sin medidor en la instalación, **When** se consulta,
   **Then** se identifica "Sin medidor", distinguiéndola de una categoría instalada sin
   lecturas, y no se generan ceros ni filas ficticias.
7. **Given** CAT-03 y CAT-05 presentes, CAT-03 con 12 kWh y CAT-05 sin lectura válida para el
   mismo intervalo, **When** se consulta el total calculado, **Then** no se muestra un total
   numérico para ese intervalo, se indica "Datos incompletos" y se identifica CAT-05 faltante;
   cuando llega su lectura válida de 8 kWh, el total calculado pasa a ser 20 kWh.
8. **Given** un conjunto no vacío de categorías presentes con lecturas válidas de cero para
   el mismo intervalo, **When** se consulta el total calculado, **Then** se muestra cero
   calculado; si no hay categorías parciales presentes ni total medido, se muestra "Sin datos".
9. **Given** un medidor total instalado sin lectura válida para un intervalo y categorías
   parciales con lecturas disponibles, **When** se consulta CAT-01, **Then** se indica
   "Total medido" y "Sin datos" para ese intervalo, sin sustituirlo por una suma.

### Edge Cases

- Un total medido puede diferir de la suma de las categorías parciales; se conserva su
  valor original. Un total calculado identifica las categorías presentes que contribuyen
  y no se presenta como una medición directa ni garantiza cubrir cargas no medidas.
- Una categoría sin medidor se excluye de la base del total calculado; una categoría
  instalada con lectura ausente o inválida impide obtenerlo para ese intervalo.
- Una base vacía no produce cero. Un cero calculado requiere al menos una categoría
  presente y lecturas válidas de cero en todas las categorías de la base.
- Las contribuciones del total calculado deben corresponder al mismo inicio y fin de
  intervalo, convertirse a kWh y contarse una sola vez; CAT-01 no contribuye a su propia suma.
- El desarrollo local no debe necesitar la VPS ni servicios remotos de prueba. Una
  indisponibilidad de la futura infraestructura de producción no impide ejecutar esas pruebas.
- Acceso por internet significa disponibilidad de la interfaz para ingresar con una cuenta;
  los datos y operaciones conservan la autenticación y permisos de la spec-006.
- La zona horaria del navegador o del servidor VPS no sustituye la zona del edificio al
  interpretar y presentar las mediciones.
- HVAC y agua caliente sanitaria forman una única categoría; el sistema sanitario representa
  su consumo eléctrico, no volúmenes de agua ni de alcantarillado.
- Las siete categorías siguen siendo seleccionables aunque ninguna tenga datos todavía.
- Un único dato debe ser visible en el gráfico y la tabla sin exigir dos puntos temporales.
- Un dato negativo, no numérico, no finito, sin origen o sin referencia temporal se rechaza; un cero
  explícito es válido. Un intervalo de duración nula o negativa también se rechaza.
- Los intervalos superpuestos dentro de la misma serie se rechazan, salvo el reenvío exacto,
  que se informa como duplicado. Un rechazo no elimina mediciones previamente aceptadas.
- Si el filtro excluye todos los intervalos disponibles por cruzar sus límites, la consulta
  muestra "Sin datos" e informa de esa exclusión, sin prorratearlos.

## Requirements *(mandatory)*

### Functional Requirements

El catálogo de categorías de esta funcionalidad es fijo; la presencia de sus medidores
en cada instalación es opcional:

| Identificador | Categoría | Alcance |
| --- | --- | --- |
| CAT-01 | Energía eléctrica total | Total medido directamente o calculado desde las categorías presentes, con procedencia y alcance identificados. |
| CAT-02 | HVAC y agua caliente sanitaria | Calefacción, ventilación, aire acondicionado y agua caliente sanitaria en una serie conjunta. |
| CAT-03 | Iluminación exterior | Consumo eléctrico de iluminación exterior. |
| CAT-04 | Iluminación interior | Consumo eléctrico de iluminación interior. |
| CAT-05 | Circuitos de enchufes | Consumo eléctrico de los circuitos de enchufes. |
| CAT-06 | Sistema sanitario | Consumo eléctrico de los sistemas de agua potable y alcantarillado. |
| CAT-07 | Ascensores | Consumo eléctrico de los ascensores. |

- **FR-001**: ECS-EC DEBE ofrecer las siete categorías del catálogo, con nombres distinguibles,
  y permitir seleccionar cualquiera incluso cuando carezca de mediciones. DEBE permitir
  configurar qué categorías tienen medidor, sin exigir siete equipos físicos. Las categorías
  parciales sin medidor DEBEN identificarse como "Sin medidor", separadas de "Sin datos".
- **FR-002**: ECS-EC DEBE recibir y conservar por separado mediciones de cualquier subconjunto
  de categorías con fuente configurada, sin exigir registros para las categorías ausentes.
  Cada medición DEBE identificar categoría, origen, valor de energía, unidad, inicio y fin del intervalo.
- **FR-003**: La recepción DEBE aceptar valores numéricos finitos de consumo mayores o iguales a cero
  en Wh, kWh o MWh, con origen y categoría conocidos e inicio anterior al fin. DEBE rechazar
  otros registros indicando la causa, sin impedir la aceptación de registros válidos independientes.
- **FR-004**: La recepción DEBE informar por registro si fue aceptado, omitido por duplicado
  o rechazado. Origen, categoría e intervalo identifican un reenvío: un valor equivalente se
  omite; un valor diferente se rechaza como conflicto, sin sobrescribir la medición existente.
- **FR-005**: ECS-EC DEBE rechazar intervalos nuevos que se superpongan con mediciones aceptadas
  de la misma categoría; los intervalos contiguos son válidos y los reenvíos se rigen por FR-004.
- **FR-006**: CAT-01 DEBE admitir total medido directamente cuando exista medidor total
  configurado y total calculado únicamente cuando no exista. Si el medidor total existe
  pero no entrega una lectura válida para un intervalo, DEBE mostrarse "Sin datos", sin
  sustituirlo por una suma. El total medido DEBE conservar su valor y origen; el calculado
  DEBE sumar una sola vez los consumos válidos de las categorías parciales configuradas
  como presentes para el mismo intervalo, convertidos a kWh. La base DEBE ser un subconjunto
  no vacío de CAT-02 a CAT-07 y todas sus
  categorías DEBEN tener lecturas válidas con el mismo inicio y fin. Si falta alguna,
  NO DEBE calcularse un total numérico para ese intervalo: DEBEN indicarse "Datos incompletos"
  y las categorías faltantes hasta disponer de sus lecturas. Las categorías sin medidor se
  excluyen de la base. Un resultado calculado DEBE conservar la identificación de sus
  contribuciones y NO DEBE presentarse como una medición física del total.
- **FR-007**: Para cada categoría, la persona DEBE poder consultar un gráfico temporal con
  intervalos y valores identificables, incluidos los casos con una única medición o valor cero.
- **FR-008**: Para cada categoría, la persona DEBE poder consultar una tabla con inicio y fin
  de intervalo, consumo y unidad por dato recibido o calculado, ordenada del intervalo más
  antiguo al más reciente.
- **FR-009**: Gráfico y tabla DEBEN usar las mismas mediciones y período para la categoría
  activa. DEBEN mostrar su nombre, magnitud de energía, unidad, límites de consulta y zona horaria.
  CAT-01 DEBE identificar "Total medido" o "Total calculado de las categorías presentes";
  el calculado DEBE enumerar su base y advertir su alcance cuando falten categorías del catálogo.
- **FR-010**: Ambas vistas DEBEN expresar el consumo en kWh: 1 kWh equivale a 1.000 Wh y
  1 MWh a 1.000 kWh. DEBEN conservarse el valor y la unidad originales para trazabilidad.
  La presentación DEBE conservar la precisión del dato convertido, sin introducir redondeos
  distintos entre gráfico y tabla ni convertir un consumo positivo en un cero aparente.
- **FR-011**: La persona DEBE poder elegir inicio y fin de consulta. Solo DEBEN incluirse
  mediciones con inicio mayor o igual al inicio elegido y fin menor o igual al fin elegido.
  Los intervalos que crucen un límite DEBEN excluirse con aviso, sin prorratear sus valores.
- **FR-012**: El período DEBE conservarse al cambiar de categoría o representación. Un rango
  con inicio igual o posterior al fin DEBE mostrar un mensaje de corrección y mantener la
  última consulta válida. La consulta inicial DEBE seguir el período definido en Assumptions.
- **FR-013**: ECS-EC DEBE interpretar y mostrar las fechas con la zona horaria del edificio;
  cuando una hora local sea ambigua, DEBE incluir su desfase para distinguir los intervalos.
- **FR-014**: Ambas vistas DEBEN distinguir carga, resultados disponibles, categorías sin
  medidor, ausencia de datos, datos incompletos del total calculado y error de consulta.
  Un error DEBE ofrecer reintento; la ausencia de datos o un fallo de una
  categoría NO DEBE impedir consultar las categorías disponibles.
- **FR-015**: ECS-EC NO DEBE rellenar intervalos ausentes con ceros, interpolaciones o estimaciones.
  El gráfico DEBE mostrar los vacíos entre intervalos con datos válidos y la tabla NO DEBE
  inventar filas. Los totales calculados conforme a FR-006 son resultados derivados de
  lecturas existentes y DEBEN identificarse como tales, sin rellenar lecturas faltantes.
- **FR-016**: Un cambio de categoría o período NO DEBE presentar los resultados de la consulta
  anterior como si correspondieran a la nueva, ni siquiera durante la carga o después de un error.

- **FR-017**: ECS-EC DEBE poder ejecutarse en un entorno de desarrollo local y desplegarse
  posteriormente como una única aplicación monolítica en una VPS. El cambio de entorno
  DEBE realizarse mediante configuración y procedimientos documentados, conservando los
  contratos funcionales. Su ejecución en la VPS DEBE ser independiente del equipo de desarrollo.
- **FR-018**: El producto desplegado en la VPS DEBE ofrecer una dirección web pública
  accesible desde redes externas por internet, sin requerir pertenecer a la red del
  edificio. El acceso a datos y funciones DEBE aplicar la autenticación y los permisos
  de la spec-006; la exposición por internet no convierte esos datos en información pública.
- **FR-019**: Las pruebas funcionales DEBEN poder prepararse y ejecutarse íntegramente en
  el entorno local, con componentes o sustitutos locales para recepción de archivos,
  correo y observabilidad, sin requerir la VPS ni servicios remotos. Los sustitutos DEBEN
  preservar los contratos y los resultados de prueba observables, y su uso DEBE quedar
  identificado. La preparación de cada entorno y sus configuraciones DEBEN documentarse.

### Key Entities *(include if feature involves data)*

- **Edificio monitoreado**: Contexto único de las mediciones y de la zona horaria de consulta.
- **Categoría de consumo**: Uno de los siete elementos del catálogo, con identificador,
  nombre, alcance y presencia de medidor configurada; agrupa su serie. CAT-01 admite una
  procedencia medida o calculada y las categorías parciales pueden carecer de medidor.
- **Origen de medición**: Fuente identificable que entrega la serie consolidada de una categoría;
  permite rastrear los registros sin presuponer un equipo ni un mecanismo de envío concreto.
- **Medición de energía**: Consumo recibido de una categoría durante un intervalo, con
  origen, valor, unidad originales y equivalencia en kWh para su consulta.
- **Total calculado**: Resultado de sumar las categorías presentes para un intervalo común,
  con valor en kWh, base configurada y referencias a todas las mediciones contribuyentes;
  su trazabilidad permite distinguirlo de una lectura directa y detectar datos incompletos.
- **Período de consulta**: Inicio, fin y zona horaria elegidos, compartidos por gráfico y tabla.
- **Resultado de recepción**: Clasificación de cada registro recibido como aceptado, duplicado
  o rechazado, con su causa cuando corresponda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Las siete categorías, el 100 % del catálogo, son seleccionables y cada una
  dispone de gráfico y tabla, con datos o con estados distinguibles de "Sin medidor",
  "Sin datos" y "Datos incompletos" cuando correspondan.
- **SC-002**: Con al menos tres mediciones conocidas por categoría, el 100 % de los valores
  e intervalos del gráfico coincide con las filas correspondientes de la tabla y con los
  valores esperados en kWh, incluidos totales medidos y calculados identificados con su
  base; no aparece ninguna medición atribuida a otra categoría o fuera del período.
- **SC-003**: Al recibir mediciones de subconjuntos de las siete categorías, reenvíos,
  conflictos y registros inválidos, el 100 % de los registros obtiene el resultado esperado:
  ningún duplicado, conflicto o rechazo modifica las mediciones válidas ya aceptadas.
- **SC-004**: En todos los escenarios de aceptación de categorías sin medidor, ausencia de
  lecturas, total calculado incompleto, cero medido o calculado, vacíos, carga y error,
  las personas pueden identificar el estado correcto y no encuentran valores inventados
  o atribuidos a una consulta diferente; ninguna lectura faltante de una categoría de la
  base produce un total calculado.
- **SC-005**: En al menos 9 de 10 tareas de evaluación con personas representativas del
  monitoreo del edificio, la persona localiza sin ayuda una categoría asignada y comprueba
  un consumo y su período en el gráfico y la tabla en un máximo de 60 segundos por tarea.

- **SC-006**: Siguiendo la documentación y usando configuraciones de prueba locales,
  pueden ejecutarse los casos funcionales de consulta y las integraciones de prueba SFTP,
  correo y observabilidad sin recursos remotos obligatorios ni una VPS disponible.
- **SC-007**: Durante la validación final del despliegue, una cuenta activa de cada perfil
  funcional puede ingresar y ejecutar sus consultas permitidas desde una red de internet
  externa, con el equipo de desarrollo apagado; una persona sin sesión no obtiene los
  datos protegidos. Las consultas conservan categorías, unidades y zona del edificio.

## Assumptions

- **Fases y despliegue transversal**: La fase actual comprende desarrollo y pruebas locales.
  El despliegue en una VPS y su verificación desde internet corresponden al producto final;
  no se requiere contratar ni habilitar ese servidor para comenzar el desarrollo local.
  Esta condición se aplica a las funcionalidades de las specs-001 a 008, preservando el
  monolito y los contratos de integración de cada una.
- **Configuración por entorno**: Desarrollo y producción tienen configuraciones, destinos,
  credenciales y datos propios. El plan debe concretar su provisión y documentación para
  que los valores del equipo local no se conviertan en destinos obligatorios en la VPS.
- **Pila tecnológica pendiente**: Lenguajes, frameworks, almacenamiento, herramientas de
  despliegue, proveedor y características de la VPS se definirán en los planes técnicos
  antes de implementar las partes que dependan de ellos. Esta aclaración fija los entornos
  y el acceso esperado, conservando abiertas esas elecciones.
- **Actor y alcance**: La funcionalidad se dirige a quien consulta el consumo de un edificio.
  No define nuevos roles, gestión de cuentas ni administración de múltiples edificios.
- **Agrupaciones**: HVAC y agua caliente sanitaria son una categoría conjunta; agua potable
  y alcantarillado forman la categoría sanitaria. Las siete categorías representan energía eléctrica.
- **Instalación y categorías presentes**: No se presupone la existencia de los siete
  medidores. Se configura el subconjunto de categorías con medición; la ausencia física
  de un medidor no equivale a consumo cero ni a un fallo temporal de adquisición.
- **Significado de los datos**: Se reciben consumos por intervalo, no lecturas acumuladas
  de un contador ni potencia instantánea. Cada categoría medida cuenta con una serie ya
  consolidada y sin intervalos superpuestos; no se agregan submedidores dentro de una
  categoría. Se permite la suma entre categorías parciales únicamente para obtener CAT-01.
- **Origen de CAT-01**: Lo determina la presencia de medidor total en la instalación:
  con medidor se utiliza exclusivamente su serie medida, sin reemplazar huecos por sumas;
  sin medidor se utiliza la serie calculada de las categorías parciales presentes.
- **Uso del total por las funcionalidades relacionadas**: El total calculado puede
  utilizarse en visualización, historial, PDF y reglas de consumo, con su base y procedencia.
  No sustituye la medición general requerida por el análisis de costos BT4.3 de la spec-004;
  sin medidor total debe identificarse la falta de esa base para los costos.
- **Fórmula y alcance del total calculado**: Para un intervalo I y la base no vacía P de
  categorías parciales presentes, T(I) = suma de E(c, I) para cada c de P, convertidas a kWh.
  Cada contribución debe cubrir exactamente I. No se prorratea ni se interpolan lecturas;
  si alguna falta o es inválida, el total queda sin valor e identificado como incompleto.
  Se registran la base aplicable y los orígenes utilizados, sin inferir qué cargas del
  edificio quedan cubiertas por las categorías ausentes del catálogo.
- **Unidades y presentación**: Se admiten Wh, kWh y MWh y se consulta en kWh. No se crean
  agregaciones adicionales por día, mes o año; cada valor representa su intervalo recibido
  o calculado según FR-006.
  Se conserva la precisión del dato convertido en ambas vistas.
- **Período inicial**: Sin una selección previa, se consulta desde el inicio de la medición
  más antigua hasta el fin de la más reciente del edificio. Si no hay mediciones, se usa
  el día actual del edificio y se muestra "Sin datos". El período es común a las siete
  categorías y no se cambia automáticamente al seleccionar otra.
- **Dependencias de datos**: Antes de implementar la recepción, deben confirmarse las fuentes
  disponibles, las categorías presentes, su correspondencia con el catálogo, el suministro
  de consumos por intervalo y la zona horaria del edificio. El plan debe documentar el
  mecanismo y la frecuencia de recepción; esta especificación no presupone equipos,
  protocolos ni actualización en tiempo real.
- **Límites funcionales**: No se incluyen alarmas, predicciones, costos, exportaciones,
  control de equipos, comparación simultánea de categorías ni conciliación entre total y parciales.
- **Gobierno del proyecto**: Aplica la constitución de ECS-EC v1.0.0. El plan debe comprobar
  sus restricciones de arquitectura, documentación e integridad antes de la implementación.
