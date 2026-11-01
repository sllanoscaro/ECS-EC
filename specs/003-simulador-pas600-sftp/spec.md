# Feature Specification: Simulador PAS600 con publicación SFTP

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "En adición a ECS-EC, implementar un programa adicional
encargado de generar y enviar datos de uso de energía eléctrica, imitando el funcionamiento
del EcoStruxure Panel Server Universal PAS600. Debe generar salidas CSV o JSON y enviarlas
al backend usando publicación SFTP. Debe permitir configurar datos faltantes, con formato
incorrecto o fuera del rango esperado para probar la limpieza de datos de la plataforma."

**Clarificaciones recibidas**: Deben reproducirse los formatos CSV/JSON reales del PAS600
para probar la compatibilidad con el dispositivo. El PAS600 real recibe las mediciones de
varios medidores Schneider Electric iEM3150 conectados físicamente mediante RS485 y
asociados a las categorías de la spec-001; el PAS600 concentra y publica esos datos.

**Especificaciones relacionadas**:
[spec-001: categorías y visualización](../001-visualizar-consumo-categorias/spec.md) y
[spec-002: registro temporal y conservación](../002-registro-retencion-consumo/spec.md).

## Clarifications

### Session 2026-11-01

- Q: ¿Qué equipos originan las mediciones que concentra el PAS600 real y cómo se conectan? → A: Varios medidores Schneider Electric iEM3150, asociados a las categorías de la spec-001 y conectados físicamente mediante RS485 al EcoStruxure Panel Server Universal PAS600.
- Q: ¿La topología exige siete medidores y un medidor propio del total? → A: No; según la aclaración de la spec-001, las categorías medidas son opcionales y CAT-01 admite un total medido o calculado. El simulador publica solo los medidores configurados y ECS-EC obtiene el total calculado de las categorías presentes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generar archivos compatibles con un PAS600 (Priority: P1)

Como persona responsable de las pruebas, quiero generar datos de medidores iEM3150 de
las siete categorías en los formatos reales publicados por un PAS600 para comprobar la
compatibilidad de ECS-EC sin disponer de los equipos físicos.

**Why this priority**: Permite comprobar la compatibilidad con los archivos que publicará
el dispositivo físico.

**Independent Test**: Generar el mismo escenario sin anomalías en CSV y en JSON, comprobarlo
con el perfil documental de referencia y comparar las mediciones interpretadas.

**Acceptance Scenarios**:

1. **Given** un escenario válido con un PAS600 y siete medidores iEM3150 simulados,
   uno por categoría, con anomalías desactivadas, **When** se generan los archivos,
   **Then** todas las mediciones previstas están presentes, son atribuibles a su medidor
   y categoría y cumplen el perfil PAS600 de referencia; el total procede de su medidor propio.
2. **Given** el mismo escenario y semilla, **When** se genera una ejecución en CSV y otra
   en JSON, **Then** ambos formatos representan las mismas mediciones y tiempos, respetando
   cada estructura nativa, sin agregar columnas o propiedades propias de ECS-EC.
3. **Given** varios medidores iEM3150 con identidades distintas bajo un mismo PAS600,
   magnitudes y unidades del perfil y correspondencias explícitas con las categorías,
   **When** se verifica la compatibilidad en CSV y JSON, **Then** se distinguen el PAS600
   publicador y cada medidor de origen, se conserva su categoría y los archivos cumplen
   los ejemplos y reglas documentales seleccionados, incluida su división en archivos.
4. **Given** un período histórico de 12 meses, **When** se ejecuta solo la generación local,
   **Then** se obtiene el conjunto correspondiente sin esperar 12 meses reales ni efectuar
   envíos de red acelerados.
5. **Given** un canal de energía acumulada con lecturas equivalentes a 100 y 104 kWh en dos
   instantes consecutivos, **When** se interpreta el resultado, **Then** el consumo entre
   esos instantes es 4 kWh; la primera lectura solo establece la referencia y no inventa
   un consumo inicial. Un canal de consumo por intervalo conserva su significado propio.
6. **Given** solo CAT-03 y CAT-05 configuradas como presentes, sin medidor total,
   **When** se genera y publica el escenario sin anomalías, **Then** los archivos contienen
   únicamente las mediciones de esos medidores, no inventan un dispositivo CAT-01 y permiten
   comprobar el total calculado de ECS-EC conforme a la spec-001; las categorías sin medidor
   no se contabilizan como muestras omitidas.

---

### User Story 2 - Publicar los archivos al destino SFTP de ECS-EC (Priority: P1)

Como persona responsable de las pruebas, quiero configurar el destino y publicar los
archivos por SFTP para recorrer el mismo camino de recepción que utilizará el dispositivo.

**Why this priority**: Generar archivos localmente no permite evaluar su entrega al backend.

**Independent Test**: Usar un destino SFTP de pruebas, verificar los archivos entregados y
simular fallos de conexión, autenticación y transferencia.

**Acceptance Scenarios**:

1. **Given** un destino válido con permisos de escritura, **When** se inicia una publicación,
   **Then** los archivos completos llegan al directorio configurado y la ejecución informa
   su transferencia, sin afirmar por ello que sus mediciones fueron aceptadas por el backend.
2. **Given** una separación de publicación configurada en menos de 15 minutos, **When** se
   valida el escenario, **Then** se impide iniciarlo y se explica el incumplimiento de la spec-002.
3. **Given** publicaciones periódicas, **When** se entregan nuevas mediciones de una categoría,
   **Then** sus ciclos están separados al menos 15 minutos reales; distintas categorías
   pueden publicarse en el mismo ciclo. La espera comienza al finalizar el envío anterior,
   de modo que una transferencia lenta no acorte la separación entre nuevas entregas.
4. **Given** credenciales incorrectas, un servidor no reconocido o un directorio sin permisos,
   **When** se prueba la conexión, **Then** se informa el fallo sin publicar datos ni exponer
   contraseñas o claves en archivos de mediciones o informes de ejecución.
5. **Given** una transferencia interrumpida, **When** se reintenta, **Then** se conserva el
   contenido y la identidad de las mediciones, se respeta la separación temporal y un
   reenvío no duplica consumos ya aceptados.
6. **Given** una publicación dividida en varios archivos, **When** se entrega al backend,
   **Then** los archivos incompletos no se procesan como entregas terminadas y los archivos
   de una misma publicación y categoría constituyen una única actualización lógica.
7. **Given** fallos transitorios persistentes, **When** se alcanza el número máximo de intentos,
   **Then** se informa el fallo definitivo y se conservan los archivos pendientes para revisión
   o reenvío posterior, sin un ciclo de reintentos ilimitado.
8. **Given** un escenario y un receptor SFTP de pruebas configurados localmente,
   **When** se generan y publican archivos con credenciales de prueba válidas,
   **Then** se pueden comprobar su entrega completa, identidad y resultados de recepción
   sin una VPS ni servicios remotos, manteniendo las comprobaciones de identidad del
   servidor y la separación temporal exigida.

---

### User Story 3 - Introducir anomalías de datos configurables (Priority: P1)

Como persona que evalúa la limpieza de datos, quiero seleccionar la clase, proporción y
categorías de los defectos para construir casos de prueba con resultados esperados conocidos.

**Why this priority**: Los defectos deben ser deliberados y medibles para distinguir fallos
del generador de fallos de detección en ECS-EC.

**Independent Test**: Generar conjuntos con cantidades previstas de omisiones, formatos
incorrectos y valores fuera de rango, y contrastarlos con el informe de control local.

**Acceptance Scenarios**:

1. **Given** 100 muestras previstas para una categoría y tasas del 10 % por cada una de las
   tres clases de anomalía, **When** se genera el escenario, **Then** quedan 10 muestras
   omitidas, 10 con formato incorrecto, 10 fuera de rango y 70 sin alterar, sin solapamientos.
2. **Given** una omisión configurada, **When** se genera el archivo, **Then** la muestra no
   aparece y no se reemplaza por un cero; el informe local identifica el intervalo ausente.
3. **Given** errores de tipo o fecha y una corrupción estructural de archivo seleccionada,
   **When** se generan los casos en CSV o JSON, **Then** las alteraciones corresponden a lo
   solicitado y el informe distingue el defecto de una muestra de un archivo ilegible completo.
4. **Given** un rango esperado de 0 a 10 kWh por intervalo para una categoría,
   **When** se configura una anomalía superior al rango, **Then** se genera un consumo
   estrictamente mayor que 10 kWh, con su intervalo y causa identificados en el informe.
5. **Given** anomalías por muestra habilitadas solo para iluminación exterior, **When** se genera el
   escenario, **Then** las otras categorías mantienen sus muestras sin defectos inducidos.
6. **Given** tasas del 0 % o del 100 %, **When** se generan escenarios válidos, **Then** se
   cumplen sus cantidades exactas; si la suma de tasas supera el 100 % o un rango es inválido,
   la configuración se rechaza antes de generar o publicar datos.
7. **Given** un archivo estructuralmente ilegible y archivos válidos independientes,
   **When** se evalúa la recepción, **Then** el fallo del primero puede identificarse sin
   confundirlo con una pérdida de transporte ni impedir analizar los otros archivos.

---

### User Story 4 - Repetir y evaluar una prueba de limpieza (Priority: P2)

Como persona responsable de calidad, quiero repetir un escenario y conocer qué se generó,
alteró y transfirió para comparar esos hechos con el comportamiento observado de ECS-EC.

**Why this priority**: La evaluación necesita una referencia independiente del resultado del backend.

**Independent Test**: Ejecutar dos veces una configuración y semilla fijas y comparar los
datos, las anomalías y los informes con los resultados de recepción de la plataforma.

**Acceptance Scenarios**:

1. **Given** la misma configuración, semilla y período simulado, **When** se repite la generación,
   **Then** coinciden los valores, intervalos y posiciones de las anomalías; los tiempos reales
   de transferencia pueden ser diferentes y quedan identificados como tales.
2. **Given** una ejecución con anomalías, **When** se consulta su informe local, **Then** se
   identifican configuración, perfil, muestras previstas, omisiones, alteraciones, archivos
   generados e intentos de transferencia, sin enviar ese informe como si fuera un archivo PAS600.
3. **Given** un archivo defectuoso transferido correctamente, **When** se revisa su estado,
   **Then** figura como transferido y no como aceptado por ECS-EC sin evidencia de recepción.
4. **Given** el informe de control y los resultados de recepción de ECS-EC, **When** se
   comparan, **Then** se pueden localizar registros indebidamente aceptados, rechazados o
   duplicados y omisiones no reflejadas en la cobertura, sin alterar los archivos originales.
5. **Given** una solicitud de detener la ejecución, **When** termina la transferencia en
   curso o se informa su interrupción, **Then** no se inician nuevos ciclos y los resultados
   ya generados y sus estados permanecen disponibles para revisión.
6. **Given** la documentación y una configuración de ejemplo sin secretos, **When** otra
   persona prepara y repite el escenario siguiendo las instrucciones, **Then** puede
   identificar el perfil, las correspondencias y anomalías utilizadas y obtener los
   mismos datos lógicos sin encontrar credenciales en las salidas de la ejecución.

### Edge Cases

- Una omisión total de muestras de una categoría instalada produce ausencia de datos,
  no consumo cero. Una categoría configurada sin medidor no genera muestras previstas
  ni omisiones inducidas; ambos casos deben distinguirse en el informe y la recepción.
- En modo normal los contenedores son compatibles con el perfil; una alteración intencionada
  puede invalidar una parte o todo el archivo y debe identificarse con ese alcance.
- Una corrupción estructural no se contabiliza como si cada registro hubiera sido alterado
  por separado: las cantidades por muestra y por archivo se informan separadamente.
- La generación histórica rápida no autoriza a acelerar las actualizaciones del backend.
- Un reintento puede corresponder a una entrega que llegó antes de perder la conexión;
  conservar sus identidades permite detectar el duplicado.
- El período de muestreo y el intervalo real de publicación son parámetros distintos.
- Un contador acumulado no es consumo por intervalo. Una lectura inicial, faltante,
  inválida o decreciente no autoriza inventar deltas ni repartirlos en muestras ausentes.
- CSV y JSON deben producir resultados equivalentes aunque agrupen las mediciones de
  forma distinta; identidades de medidor y categorías se relacionan mediante la configuración.
- Compartir el modelo iEM3150 no convierte a los medidores en un único origen ni determina
  su categoría. La identidad del PAS600 publicador no sustituye la de cada medidor de origen.
- Un valor positivo elevado no es inválido solo por su tamaño: su anomalía se evalúa contra
  el rango configurado para esa categoría, unidad y duración del intervalo.
- Una división en archivos no debe convertir una publicación de una categoría en varias
  actualizaciones separadas por menos de 15 minutos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El simulador DEBE ser un programa adicional ejecutable de forma independiente
  que actúe como fuente externa de pruebas. El funcionamiento de la plataforma NO DEBE
  depender de mantenerlo en ejecución.
- **FR-002**: La persona DEBE poder configurar categorías activas, medidores iEM3150
  simulados asociados al PAS600 publicador, correspondencia de magnitudes, período y zona
  horaria de los datos, muestreo, formato, semilla, rangos de consumo, destino y periodicidad
  de publicación. DEBE admitir subconjuntos de categorías y escenarios sin medidor total.
  Por defecto DEBEN incluirse las siete categorías y estar desactivadas todas las anomalías;
  esa configuración de prueba no exige siete medidores en la instalación real.
- **FR-003**: Los archivos normales DEBEN reproducir el perfil real de publicación del PAS600
  fijado en Assumptions, incluidos estructura, metadatos, nombres y convenciones temporales.
  NO DEBEN sustituirse por un formato propio ni añadirse marcas de prueba a su contenido.
- **FR-004**: El programa DEBE soportar CSV y JSON como opciones seleccionables y representar
  el mismo escenario lógico en ambas. La conformidad DEBE verificarse contra casos de
  referencia independientes, no solo contra el lector desarrollado para ECS-EC.
- **FR-005**: Cada medición DEBE poder vincularse con su medidor iEM3150 de origen,
  PAS600 publicador, magnitud, categoría, unidad e intervalo mediante las identidades
  nativas del perfil y su configuración de correspondencias. Los medidores DEBEN tener
  identidades distintas dentro del PAS600. Si hay medidor total configurado, sus lecturas
  DEBEN conservar su identidad y valor. El simulador NO DEBE inventar un medidor total ni
  insertar totales calculados propios en las publicaciones nativas cuando no exista;
  ECS-EC DEBE obtenerlos según las reglas de la spec-001, conservando sus contribuciones.
- **FR-006**: Sin anomalías, las muestras DEBEN cumplir los rangos definidos y las reglas
  temporales del escenario. La interpretación DEBE distinguir energía acumulada y consumo
  por intervalo; para la acumulada se usan diferencias entre lecturas válidas consecutivas,
  sin inventar consumo anterior a la primera referencia ni subdividir huecos sin evidencia.
- **FR-007**: La publicación DEBE usar SFTP hacia el destino de recepción de ECS-EC. DEBEN
  configurarse servidor, puerto, directorio, usuario y autenticación mediante contraseña
  o clave. DEBE poder comprobarse la conexión y la identidad del servidor antes del envío.
  El destino DEBE poder configurarse para un receptor SFTP de pruebas local o para la
  recepción de la futura VPS, conservando el mismo contrato de publicación y autenticación.
- **FR-008**: Los ciclos con nuevas mediciones para una categoría DEBEN separarse al menos
  15 minutos reales, conforme a la spec-002; la configuración de una separación menor DEBE
  rechazarse. El valor inicial de separación DEBE ser 15 minutos. La generación local
  y el avance del tiempo simulado NO DEBEN reducir ese intervalo real de publicación.
  La espera DEBE contarse desde la finalización del envío anterior hasta el inicio del
  siguiente, incluidos los reintentos; no se permiten envíos simultáneos de esa categoría.
- **FR-009**: Una publicación DEBE conservar la identidad de sus archivos y mediciones al
  reintentarse. El contrato de recepción DEBE impedir el procesamiento de archivos todavía
  incompletos y reconocer los fragmentos de una misma publicación como una actualización
  lógica por categoría, sin introducir campos ajenos al formato nativo.
- **FR-010**: Los fallos transitorios DEBEN admitir reintentos limitados y configurables,
  con un máximo inicial de tres intentos totales por publicación y separación mínima de
  15 minutos. Los fallos de autenticación, identidad o configuración DEBEN detener el envío
  hasta corregirse; los archivos no entregados DEBEN conservarse para revisión o reenvío.
- **FR-011**: La ejecución DEBE distinguir archivos generados, pendientes, transferidos y
  fallidos. Una transferencia SFTP exitosa NO DEBE presentarse como aceptación o limpieza
  correcta de las mediciones por el backend.
- **FR-012**: DEBEN configurarse, por categoría, tasas independientes de muestras faltantes,
  con formato incorrecto y fuera de rango, cada una entre 0 % y 100 %. Se DEBE usar el
  número original de muestras previstas como denominador y asignar a cada clase la parte
  entera inferior de su cantidad calculada, sin solapamientos; la suma no puede superar el 100 %.
  Una categoría sin medidor configurado no tiene muestras previstas ni participa en esas tasas.
- **FR-013**: Las muestras faltantes DEBEN omitirse de la publicación sin reemplazarlas
  por ceros. Las anomalías de formato DEBEN permitir tipos o fechas inválidos por muestra
  y, mediante selección explícita de archivos, corrupción de su estructura CSV o JSON.
  Esta última DEBE informarse separadamente de las tasas por muestra.
- **FR-014**: Los rangos esperados DEBEN definirse por categoría y duración de intervalo,
  expresados en una unidad de energía identificada. Los valores fuera de rango DEBEN
  poder generarse por debajo del mínimo o por encima del máximo, sin confundir el valor
  absoluto de un contador acumulado con el consumo correspondiente al intervalo.
- **FR-015**: Las anomalías DEBEN aplicarse únicamente a las categorías y posiciones
  seleccionadas. El resto del escenario DEBE conservar sus datos y estructura normales,
  salvo el alcance explícito de una corrupción estructural de archivo.
- **FR-016**: Cada ejecución DEBE generar un informe local de control, separado de las
  publicaciones PAS600, con configuración sin secretos, perfil de referencia, semilla,
  datos lógicos anteriores a la alteración, defectos aplicados, cantidades por muestra
  y archivo, identidades de correlación y resultados de transferencia.
- **FR-017**: La misma configuración, semilla y período simulado DEBEN reproducir los mismos
  datos y anomalías en ejecuciones independientes. Los identificadores y tiempos reales
  de ejecución o transferencia DEBEN distinguirse de los tiempos y datos simulados.
- **FR-018**: La persona DEBE poder contrastar el informe local con los resultados de
  recepción de ECS-EC para evaluar aceptación, rechazo, duplicados y cobertura. El contraste
  NO DEBE alterar el archivo enviado ni añadir indicadores privados que revelen al receptor
  qué muestras fueron alteradas.
- **FR-019**: La configuración DEBE validarse antes de generar o publicar: categorías y
  correspondencias válidas, período creciente, muestreo positivo compatible con el perfil,
  rangos finitos con mínimo no negativo y máximo mayor o igual al mínimo, tasas permitidas
  y separación temporal válida. Las alteraciones deliberadas del contenido solo se aplican
  después de validar esa configuración.
- **FR-020**: DEBE existir generación local sin publicación, capaz de cubrir al menos
  12 meses simulados de las siete categorías. La publicación periódica DEBE poder iniciarse
  y detenerse, conservando los archivos e informes ya generados y su estado.
- **FR-021**: La interpretación de archivos nativos por el backend DEBE mantener los contratos
  de categorías, unidades, validación, actualización y conservación de las specs-001 y 002
  sobre las mediciones normalizadas. Un archivo ilegible DEBE poder distinguirse de una
  transferencia fallida y de un rechazo de una medición aislada.
- **FR-022**: El programa DEBE documentar sus configuraciones, el perfil compatible, las
  correspondencias, los escenarios de anomalías y la reproducción de pruebas, conforme a
  la constitución. Los archivos de datos e informes NO DEBEN contener credenciales SFTP.

### Key Entities *(include if feature involves data)*

- **Escenario de simulación**: Categorías presentes y sin medidor, PAS600 publicador,
  medidores iEM3150, disponibilidad de medidor total, magnitudes, calendario, muestreo,
  rangos, semilla y reglas de alteración de una ejecución reproducible.
- **Perfil de compatibilidad PAS600**: Revisión documental y casos de referencia que
  determinan la conformidad de las publicaciones normales y la interpretación de sus medidas.
- **PAS600 publicador simulado**: Representación del concentrador que recibe los datos
  de varios medidores y publica los archivos nativos; su identidad se distingue de las
  identidades de los medidores de origen.
- **Medidor iEM3150 y canal simulados**: Modelo, identidad del medidor dentro del PAS600 y
  magnitudes nativas relacionadas con una categoría del edificio mediante una correspondencia
  explícita; representan los medidores conectados por RS485 en la instalación real.
- **Muestra prevista**: Dato lógico de energía esperado para un intervalo antes de introducir
  anomalías; permite reconocer omisiones y conservar una referencia independiente.
- **Regla de anomalía**: Clase, categorías, tasa y posiciones o archivos afectados, con rango
  y alcance suficientes para conocer el defecto introducido.
- **Publicación**: Conjunto de archivos de un ciclo, con identidad correlacionable,
  categorías incluidas, destino, intentos y estado de entrega.
- **Informe de control**: Evidencia local de los datos previstos, sus alteraciones y las
  transferencias, utilizada para contrastar los resultados del backend.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En escenarios sin anomalías con las siete categorías o subconjuntos de ellas,
  incluidos escenarios sin medidor total, el 100 % de los archivos CSV y JSON cumple los
  casos de referencia del perfil PAS600 y ambos formatos producen
  los mismos consumos e intervalos esperados tras su interpretación, conservando la
  atribución de cada medición a su medidor iEM3150, PAS600 publicador y categoría. Los
  totales calculados de ECS-EC coinciden con la base de categorías presentes y las reglas
  de datos incompletos de la spec-001, sin aparecer como lecturas de un medidor inexistente.
- **SC-002**: En conjuntos de tamaño conocido, el 100 % de las cantidades y posiciones de
  defectos coincide con las reglas configuradas, incluidos 0 %, 100 %, selección por categoría
  y corrupción estructural; no aparecen alteraciones fuera de su alcance declarado.
- **SC-003**: Dos generaciones con la misma configuración, semilla y período reproducen el
  100 % de los valores lógicos, tiempos de medición y ubicaciones de anomalías, incluidas
  las muestras omitidas.
- **SC-004**: En los escenarios de publicación, el 100 % de los archivos conserva un estado
  de entrega verificable; no se procesan transferencias parciales ni se duplican consumos
  por reintentos, y ninguna actualización nueva por categoría se entrega con separación
  inferior a 15 minutos.
- **SC-005**: Para cada caso de aceptación, la persona evaluadora puede identificar todas
  las diferencias entre los datos esperados y el resultado observado del backend mediante
  el informe y sus correlaciones, distinguiendo defectos, rechazos y fallos de entrega.
- **SC-006**: Se puede generar localmente un historial de al menos 12 meses simulados para
  las siete categorías sin hardware físico ni transcurso equivalente de tiempo real, y
  utilizarlo para preparar pruebas de conservación y de las cuatro agrupaciones de la spec-002.

## Assumptions

- **Entornos de ejecución y destino**: Rigen las condiciones transversales de la spec-001:
  el desarrollo actual y sus pruebas funcionales son locales, con un receptor SFTP de
  pruebas local y sin requerir una VPS ni servicios remotos. El destino de producción
  se configurará para la futura VPS durante el despliegue. La ubicación del receptor no
  cambia formatos, identidades, validaciones, separación temporal ni protección de credenciales.
  El simulador conserva su condición de herramienta externa opcional de pruebas.
- **Topología física de referencia**: Un EcoStruxure Panel Server Universal PAS600 de
  Schneider Electric concentra las mediciones de varios medidores iEM3150 de la misma marca,
  conectados físicamente mediante RS485. Los medidores son el origen de las mediciones;
  el PAS600 las recopila y publica por SFTP hacia ECS-EC. La comunicación del iEM3150 es
  Modbus RTU sobre RS485, según la
  [ficha oficial A9MEM3150 de Schneider Electric](https://iportal.se.com/Contents/docs/SQD-A9MEM3150_DATASHEET.PDF),
  fechada el 2020-03-20 y consultada el 2026-11-01.
- **Referencia fija de compatibilidad**: El perfil inicial se basa en la
  [guía oficial DOCA0172EN-19 de Schneider Electric](https://www.productinfo.schneider-electric.com/ecostruxurepanelserverguide/doca0172-ecostruxure-panel-server-user-guide/English/Panel-Server-User-Guide-DOCA0172EN-19.pdf),
  secciones de publicación SFTP, formatos y apéndice D, consultada el 2026-10-31.
  Se fija esta revisión reproducible; no se afirma compatibilidad con todas las versiones
  de firmware o variantes del producto.
- **Alcance de la fidelidad**: Se reproducen los archivos de publicación y sus convenciones
  para los canales de energía seleccionados de los medidores iEM3150. Como resume la guía
  de referencia, CSV organiza datos por dispositivo y JSON puede reunir dispositivos;
  deben respetarse sus reglas de fragmentación. La conexión RS485 describe la instalación
  real; no se emulan el bus, los intercambios Modbus RTU, los circuitos físicos ni la interfaz
  de los equipos, y la ejecución del simulador no requiere hardware.
- **Correspondencias y normalización**: El plan debe documentar el contrato exacto del perfil
  y ejemplos contrastados, las magnitudes y unidades admitidas y las correspondencias con
  CAT-01 a CAT-07. Si se usan contadores acumulados, su interpretación produce consumos por
  intervalo para las specs-001 y 002, conservando los datos de origen y la referencia temporal.
  No se cambian los archivos del fabricante para acomodarlos al modelo interno de ECS-EC.
- **Configuración inicial**: Por defecto se representa un PAS600 publicador con siete
  medidores iEM3150 simulados de identidades distintas, uno por categoría de CAT-01 a CAT-07.
  También deben poder configurarse categorías sin medidor y ausencia de medidor total:
  no se presupone que la instalación real disponga de los siete equipos. Se mantiene una
  serie por categoría medida; el total calculado es responsabilidad de ECS-EC según la
  spec-001 y no implica agregar submedidores dentro de una categoría. El muestreo es de
  15 minutos y la publicación se separa al menos 15 minutos. Los rangos esperados se proporcionan
  explícitamente por categoría e intervalo antes de iniciar; no se inventan límites físicos
  del edificio. Un formato se elige por ejecución; ambos deben estar disponibles.
- **Alcance de limpieza**: El generador introduce casos y proporciona su referencia; no
  limpia sus propios defectos antes de enviarlos. Las reglas de aceptación del backend
  deben estar identificadas para evaluar cada prueba. Las bandas configuradas no modifican
  silenciosamente esas reglas; una aceptación inesperada constituye un hallazgo de la prueba.
- **Recepción y evidencia**: Se requiere un destino SFTP de pruebas y resultados de recepción
  correlacionables en ECS-EC. SFTP confirma entrega de archivos, no aceptación de mediciones.
  El plan debe resolver la entrega completa y agrupación de publicaciones nativas sin
  alterar sus formatos. El contraste puede realizarse por la persona evaluadora; no se
  presupone una interfaz adicional de confirmación desde el backend al simulador.
- **Anomalías y reproducibilidad**: Las tasas por muestra son excluyentes y usan cantidades
  exactas según FR-012. La selección explícita de archivos corruptos tiene un conteo separado.
  La semilla reproduce el escenario lógico; los tiempos de transferencia reales no son
  parte del requisito de igualdad entre ejecuciones.
- **Arquitectura y alcance**: El simulador es una herramienta externa de pruebas; la recepción
  e interpretación de datos pertenecen al backend monolítico. Su incorporación no requiere
  dividir las funcionalidades de la plataforma en servicios independientes.
  No se implementan otros protocolos, réplicas completas del firmware, cambios a la política
  de conservación ni nuevas reglas de limpieza ajenas al contrato de prueba.
