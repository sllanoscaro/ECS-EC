# ECS-EC: plataforma de monitoreo y gestión de información eléctrica para ECS

## 1. Presentación del proyecto

ECS-EC es una plataforma web que convierte las mediciones eléctricas de un edificio en información comprensible para su operación y administración. Integra la consulta del consumo, la revisión de costos, el contraste con boletas, la generación de reportes y el envío de notificaciones. Su propósito es que ECS disponga de una visión ordenada y verificable del uso de la energía, con información que pueda consultar y comunicar sin reconstruir manualmente cada resultado.

La solución abarca el recorrido completo de la información: recibe los archivos de medición, revisa su validez, conserva el historial, organiza los consumos por categoría y período, y presenta los resultados mediante gráficos, tablas, documentos y avisos. Cada resultado mantiene su relación con los datos y las reglas que lo explican.

Este documento presenta el producto completo, considerando implementado el conjunto de sus nueve especificaciones. Explica su utilidad para ECS, sus funcionalidades, sus fundamentos teóricos, su relación con las tecnologías del sector y la metodología que estructura su desarrollo y evaluación.

## 2. Necesidad que resuelve para ECS

Contar con medidores eléctricos no basta para comprender el funcionamiento energético de un edificio. Las lecturas deben relacionarse con los equipos que representan, sus horarios de uso y las condiciones de cobro del suministro. También es necesario reconocer cuándo la información está completa y cuándo una aparente disminución del consumo corresponde, en realidad, a una interrupción de las mediciones.

El problema que aborda ECS-EC es la distancia entre disponer de datos eléctricos y contar con información útil para decidir. Una boleta entrega antecedentes del cobro, pero por sí sola no explica la evolución del consumo de iluminación, climatización o ascensores. A su vez, un archivo de mediciones contiene valores detallados, pero requiere organización y contexto para servir a una persona encargada del edificio.

La plataforma reúne estas perspectivas en un mismo entorno:

| Necesidad de ECS | Respuesta de ECS-EC | Utilidad para la empresa |
| --- | --- | --- |
| Comprender dónde se utiliza la energía | Consumo separado por categorías del edificio | Orienta la revisión de los sistemas con mayor participación energética. |
| Reconocer cómo cambia el consumo | Gráficos, tablas e historial con distintas escalas de tiempo | Facilita identificar horarios, concentraciones y variaciones que requieren revisión. |
| Entender los costos eléctricos | Desglose del suministro general bajo tarifa BT4.3 | Permite explicar la participación de energía, demanda y otros cargos. |
| Revisar diferencias con las boletas | Comparación de períodos y conceptos equivalentes | Entrega antecedentes para analizar discrepancias con una base común. |
| Compartir información con otras personas | Reportes PDF de una página | Facilita reuniones, seguimiento y comunicación de resultados. |
| Conocer situaciones relevantes sin consultar continuamente | Resúmenes y alertas por correo | Dirige la atención hacia condiciones de consumo o problemas de información. |
| Proteger datos y responsabilidades | Cuentas, permisos e historial de cambios | Mantiene control sobre quién consulta y quién administra. |
| Identificar problemas de funcionamiento | Herramientas técnicas de diagnóstico separadas | Apoya el mantenimiento del sistema sin exponer información privada. |

Estos beneficios corresponden a capacidades de apoyo a la gestión. El ahorro económico depende de las decisiones y acciones que ECS adopta a partir de la información; el documento no atribuye al proyecto un porcentaje de ahorro ni una reducción de consumo sin mediciones que los respalden.

## 3. Objetivos de la solución

### Objetivo general

Proporcionar a ECS una plataforma centralizada para monitorear y comprender el consumo eléctrico de un edificio, relacionarlo con sus costos y comunicar sus resultados con seguridad y trazabilidad.

### Objetivos específicos

- Mostrar el consumo de los principales sistemas del edificio mediante representaciones fáciles de consultar.
- Conservar mediciones e historial para examinar la evolución energética en distintas escalas de tiempo.
- Distinguir mediciones válidas, datos calculados, ausencias y errores, evitando interpretaciones engañosas.
- Explicar los costos del suministro general y contrastarlos con los antecedentes de facturación.
- Producir resúmenes descargables y notificaciones dirigidas a personas autorizadas.
- Proteger la información y registrar las decisiones administrativas relevantes.
- Facilitar la verificación y el diagnóstico del sistema mediante pruebas reproducibles y herramientas de supervisión.

## 4. Alcance y personas usuarias

ECS-EC se concentra en un edificio y un suministro eléctrico general. La interfaz está en español y se utiliza desde un navegador, mediante una conexión protegida y una cuenta autorizada. El acceso por internet permite consultar la plataforma desde ubicaciones externas al edificio.

La presentación utiliza la identidad visual de **Electro Conforma**, mientras **ECS-EC** identifica al sistema.

Existen dos perfiles dentro de la aplicación y un acceso técnico separado:

| Perfil | Responsabilidades y acceso |
| --- | --- |
| Operador | Consulta consumo, historial, costos y boletas; genera y descarga reportes; revisa sus notificaciones. Su función es monitorear e interpretar la información. |
| Administrador técnico | Dispone de las consultas del Operador y administra cuentas, fuentes de medición, condiciones tarifarias, boletas y reglas de notificación. Sus cambios quedan registrados. |
| Programador | Consulta información técnica de diagnóstico en herramientas externas a la aplicación funcional. Este acceso tiene autorización propia y no concede acceso a consumos, boletas o administración del edificio. |

El producto entrega información para apoyar decisiones humanas. Su alcance se centra en monitoreo, análisis y comunicación: las acciones sobre equipos eléctricos corresponden a la operación del edificio. Las alertas de consumo utilizan reglas explícitas, y el análisis histórico describe los registros disponibles.

## 5. Funcionamiento general

El recorrido de la información comprende seis etapas:

1. **Medición y publicación.** Los medidores registran magnitudes eléctricas y el concentrador PAS600 publica los archivos correspondientes.
2. **Recepción protegida.** Los archivos llegan mediante SFTP, un mecanismo de transferencia cifrada que identifica al emisor y al servidor receptor.
3. **Revisión de los datos.** La plataforma reconoce la fuente y la categoría, valida valores y fechas, detecta duplicados y explica los rechazos.
4. **Organización y conservación.** Las mediciones aceptadas se guardan junto con su procedencia y se agrupan por hora, día, mes y año.
5. **Consulta y análisis.** Las personas autorizadas revisan consumo, calidad de la información, costos e historial.
6. **Comunicación y seguimiento.** El sistema genera PDF, evalúa reglas de notificación y conserva los resultados de las operaciones relevantes.

Por ejemplo, una persona encargada del edificio consulta el consumo de iluminación interior de un mes, identifica los días con mayor uso y revisa sus valores exactos en una tabla. Después consulta el costo del suministro general, examina su comparación con la boleta y descarga un resumen para una reunión. Si faltan mediciones en alguna sección, esa limitación permanece visible durante todo el recorrido.

## 6. Características y funcionalidades

### 6.1. Monitoreo por categorías

El catálogo comprende siete categorías:

| Categoría | Información representada |
| --- | --- |
| Energía eléctrica total | Consumo general medido o total calculado de las categorías presentes, con identificación de su procedencia. |
| Climatización y agua caliente sanitaria | Consumo eléctrico de calefacción, ventilación, aire acondicionado y producción de agua caliente sanitaria. |
| Iluminación exterior | Consumo eléctrico asociado a la iluminación exterior del edificio. |
| Iluminación interior | Consumo eléctrico asociado a la iluminación interior. |
| Circuitos de enchufes | Consumo eléctrico de las cargas conectadas a los circuitos de enchufes medidos. |
| Sistema sanitario | Consumo eléctrico de los sistemas de agua potable y alcantarillado. |
| Ascensores | Consumo eléctrico asociado a los ascensores. |

La categoría sanitaria representa energía eléctrica, expresada en kilovatios hora; su valor no corresponde a un volumen de agua.

El edificio puede disponer de medidores solo para algunas categorías. La plataforma mantiene las siete identificables y señala cuáles carecen de medidor. Cada categoría disponible se consulta mediante un gráfico de evolución y una tabla de valores exactos. Ambas representaciones utilizan los mismos datos, filtros y períodos.

La portada presenta el estado del día y el desglose por categoría. Su consulta se actualiza una vez por cuarto de hora, cinco segundos después del cierre correspondiente, y admite actualización manual. La llegada efectiva de nuevas mediciones depende de la fuente y de las reglas de recepción.

### 6.2. Total medido y total calculado

El sistema distingue dos formas de representar el total:

- **Total medido:** corresponde a la lectura del medidor general. Conserva su valor aunque difiera de la suma de las categorías parciales.
- **Total calculado:** se obtiene, en instalaciones sin medidor general, sumando las categorías presentes con lecturas válidas para el mismo intervalo. Identifica cuáles participan y el alcance de esa suma.

Por ejemplo, si únicamente se miden iluminación exterior y enchufes, con 12 y 8 kWh en un mismo intervalo, el total calculado es 20 kWh. Ese valor representa la base medida disponible; no acredita que todas las cargas del edificio estén cubiertas.

Si falta la lectura de una categoría requerida, el sistema informa que el total está incompleto. Cuando existe medidor general y falta su lectura, conserva la condición de total medido sin datos. Esto mantiene una interpretación estable del origen de cada valor.

El análisis de costos BT4.3 utiliza exclusivamente el medidor general asociado al suministro. El total calculado sirve para las consultas, el historial, los reportes y las reglas de consumo, con su alcance visible.

### 6.3. Historial y consultas por período

La plataforma permite seleccionar categoría, período y nivel de detalle. Además de las mediciones originales, ofrece agrupaciones horarias, diarias, mensuales y anuales.

Cada agrupación muestra la energía disponible, el intervalo que representa y la cobertura de sus datos. Los límites siguen el calendario y la zona horaria del edificio, incluidos los cambios de hora y los años bisiestos. Un período en curso se identifica de forma independiente de su completitud.

Las incorporaciones de datos nuevos de una misma categoría respetan una separación mínima de 15 minutos reales. Esta regla limita la frecuencia de aceptación; no garantiza una llegada de datos cada 15 minutos ni define, por sí sola, la duración de las mediciones.

Las mediciones originales y los registros agrupados se conservan durante al menos doce meses calendario, según su fecha de aceptación, creación o incorporación de datos nuevos. La recepción tardía válida actualiza los períodos afectados sin volver a contabilizar registros existentes. La conservación protege la historia registrada y distingue los períodos anteriores al inicio del registro.

### 6.4. Calidad de la información

La plataforma trata la calidad de los datos como parte del resultado que entrega. Distingue:

| Estado | Significado |
| --- | --- |
| Cero medido | Existe una lectura válida cuyo consumo es cero. |
| Sin datos | No hay mediciones utilizables para la consulta. |
| Sin medidor | La categoría no tiene una fuente de medición configurada. |
| Datos incompletos | Existe información, pero no cubre todo el período o faltan contribuciones necesarias. |
| En curso | El período consultado todavía no ha terminado. |
| Error de consulta | Un problema impide recuperar la información solicitada. |

Los registros inválidos se rechazan con una causa identificable. Un reenvío equivalente se reconoce como duplicado y no aumenta el consumo. Un valor distinto para una medición ya aceptada se trata como conflicto, preservando el registro original.

Los vacíos permanecen visibles. Las mediciones que cruzan los límites de una agrupación se conservan en el detalle y se excluyen de esa agrupación con una explicación, sin repartir arbitrariamente su energía.

### 6.5. Análisis de costos bajo tarifa BT4.3

La sección de costos relaciona la medición del suministro general con sus condiciones tarifarias. Presenta el costo por ciclo, sus componentes y la evolución histórica mediante gráficos y tablas.

El desglose permite revisar la cantidad o base utilizada, su unidad, el precio o factor aplicado y el importe resultante. Distingue energía, demanda, otros cargos aplicables, impuestos y total, de acuerdo con el perfil documentado del suministro.

El Administrador técnico mantiene la identificación del suministro, la distribuidora, las condiciones aplicables, los precios, las vigencias y las referencias que respaldan las reglas. Los cambios generan revisiones, de modo que un resultado histórico conserva la relación con las condiciones utilizadas en su cálculo.

Cuando faltan antecedentes para un cargo, el sistema identifica qué componente no puede calcularse y mantiene visibles los que sí cuentan con respaldo. Un subtotal disponible conserva su condición parcial.

La vista incluye una estimación de la distribución del cargo neto de energía entre categorías, con porcentajes e importes en pesos chilenos. La estimación usa proporciones de consumo del mismo ciclo y distingue la energía general no asignada. Tiene un corte de consulta propio y condiciones de suficiencia: no constituye una boleta por categoría ni distribuye demanda, transmisión, cargos fijos o impuestos.

### 6.6. Comparación con boletas

El Administrador técnico registra los antecedentes de las boletas, incluidos el suministro, el ciclo de consumo, las cantidades disponibles, los conceptos cobrados, los impuestos y la referencia documental.

La plataforma compara el cálculo y la boleta cuando coinciden sus períodos y bases. Muestra el importe calculado, el facturado y su diferencia. Para interpretar el signo, utiliza la relación:

**Diferencia = importe calculado − importe facturado.**

Una diferencia positiva indica un cálculo mayor que el importe facturado comparable; una negativa indica uno menor. El porcentaje se obtiene respecto del valor absoluto del importe facturado, cuando este es distinto de cero.

Deudas, intereses, créditos y otros conceptos mantienen su tratamiento propio. La existencia de una diferencia aporta un antecedente para revisión; su causa requiere analizar las bases utilizadas, las condiciones del suministro y los conceptos efectivamente comparados.

Las correcciones de boletas y los recálculos conservan las versiones anteriores. Cada contraste identifica las revisiones exactas que compara, lo que permite explicar un resultado sin alterar sus antecedentes.

### 6.7. Reportes PDF

ECS-EC genera resúmenes diarios, mensuales y anuales en PDF, descargables y legibles sin conexión a la plataforma. Cada reporte ocupa exactamente una página A4 vertical, reúne la información esencial y mantiene texto de al menos diez puntos.

El documento contiene las siete categorías con sus consumos, unidades y estados; una evolución del total; los costos disponibles; el contraste comparable con boletas; y las referencias necesarias para interpretar el período, la zona horaria, la emisión y el corte de los datos.

El gráfico usa horas en el resumen diario, días en el mensual y meses en el anual. Los datos simulados se identifican y las limitaciones de cobertura se conservan en el documento.

La energía se resume según el período calendario seleccionado. La información financiera se agrupa por los ciclos cuyo cierre pertenece a ese período, indicando su alcance. Así, un reporte mensual puede incluir un ciclo de facturación que comenzó en el mes anterior sin confundir sus fechas con las del resumen energético.

Cada emisión utiliza una captura coherente de datos y versiones. Un documento ya emitido conserva sus resultados aunque después lleguen mediciones o se registren nuevas revisiones. Cuando una generación falla, el sistema informa el resultado y permite reintentar sin ofrecer un archivo incompleto como descarga exitosa.

### 6.8. Notificaciones y alertas

Las notificaciones comunican información relevante por correo electrónico. El Administrador técnico configura su contenido, destinatarios y condiciones de envío; también activa, pausa y revisa las reglas.

Existen dos modalidades:

- **Periódica:** entrega resúmenes según intervalos de minutos u horas, o recurrencias diarias, semanales, mensuales o anuales. Por ejemplo, un resumen diario a las 06:00 con información de recepción y calidad.
- **Urgente:** comunica una condición detectada, como un umbral de consumo, ausencia de datos durante un plazo configurado o un fallo funcional de cálculo o generación de PDF.

Las reglas de consumo utilizan categorías, ventanas temporales, comparaciones y umbrales definidos. Se evalúan con datos aceptados y cobertura suficiente. Una ventana incompleta se identifica como no evaluable, evitando conclusiones basadas en información insuficiente.

Una condición persistente mantiene un mismo episodio para evitar alertas repetidas por la misma situación. Las alertas de ausencia de datos utilizan un plazo explícito compatible con la recepción, de al menos 15 minutos.

Los destinatarios son cuentas funcionales activas con permiso para consultar el contenido. El sistema comprueba su autorización antes de cada intento y registra si la entrega está pendiente, aceptada por el servicio de correo, fallida, cancelada o indeterminada. La aceptación por el servicio de correo tiene un significado distinto de la lectura del mensaje.

La programación y los estados sobreviven a reinicios. Los fallos transitorios admiten reintentos limitados; una entrega de resultado incierto requiere una decisión administrativa para reenviarse. Bajo las condiciones operativas y de carga definidas para la evaluación, el primer intento se inicia dentro de los 60 segundos de la programación o detección válida.

### 6.9. Acceso seguro y administración

El ingreso utiliza correo y contraseña. Las cuentas se crean mediante administración controlada; cada solicitud protegida comprueba en el servidor la identidad, el estado y los permisos vigentes.

El sistema permite renovar contraseñas, restablecerlas administrativamente, desactivar cuentas y cerrar sesiones. Las contraseñas iniciales o restablecidas requieren renovación por su titular. Los cambios relevantes de cuenta invalidan las sesiones anteriores, y la protección del último administrador activo mantiene la capacidad de gestión.

Los accesos web utilizan HTTPS. Las contraseñas se almacenan mediante mecanismos no recuperables, y las credenciales de integración permanecen fuera de reportes y contenidos públicos.

El historial administrativo registra quién realizó una acción, cuándo ocurrió, qué afectó y cuál fue su resultado. Esta trazabilidad permite revisar cambios de configuración sin modificar los acontecimientos registrados.

### 6.10. Supervisión y continuidad de operación

El equipo técnico dispone de herramientas para reconocer qué ocurrió durante una operación, cuánto tardó y en qué etapa apareció un problema. La supervisión combina registros de acontecimientos, indicadores agregados y seguimiento de las etapas de procesamiento.

Este entorno está separado de las pantallas de uso cotidiano y excluye contraseñas, contenidos de boletas y reportes, valores individuales de consumo y otros datos protegidos. La auditoría funcional conserva una finalidad distinta: documenta acciones y resultados relevantes del negocio.

Los fallos del correo o de las herramientas de supervisión no bloquean por sí solos la recepción de mediciones, las consultas, los costos o los PDF. La solución incluye procedimientos de respaldo y restauración para recuperar información y mantener una operación controlada.

### 6.11. Simulación y verificación de mediciones

El proyecto incorpora una herramienta independiente que simula medidores iEM3150 y publicaciones PAS600. Genera archivos CSV o JSON y los transmite por el mismo mecanismo protegido de recepción.

Permite seleccionar categorías, períodos, rangos de consumo y anomalías deliberadas, como muestras ausentes, errores de formato y valores fuera de rango. También produce escenarios de al menos doce meses simulados.

Cada ensayo mantiene un informe de control separado de los archivos enviados. Con la misma configuración y semilla —el valor que fija la generación de datos— se reproduce el escenario y se compara lo generado con lo aceptado o rechazado por ECS-EC.

Esta herramienta permite estudiar la calidad de la recepción sin depender de provocar fallos en equipos reales. Los datos sintéticos conservan su identificación y se utilizan como evidencia de prueba.

## 7. Fundamentos teóricos

### 7.1. Gestión energética basada en información

La gestión energética utiliza mediciones para comprender los usos de la energía, establecer referencias y evaluar decisiones. La norma ISO 50001 ofrece un marco de gestión y mejora continua basado en el ciclo de planificar, hacer, verificar y actuar. ECS-EC aporta información para la observación y verificación dentro de esa lógica; la referencia conceptual no constituye una certificación de la empresa ni del sistema. [Fuente: ISO, gestión de la energía](https://www.iso.org/iso-50001-energy-management.html).

En ECS, esta relación se expresa en un ciclo práctico: identificar un comportamiento, revisar sus antecedentes, decidir una acción operativa y examinar los registros posteriores. La plataforma suministra evidencia para ese análisis. Una atribución de ahorro requiere además considerar factores como ocupación, clima, horarios y condiciones de funcionamiento.

### 7.2. Energía y potencia

La **energía**, expresada en kilovatios hora o kWh, representa una cantidad consumida durante un intervalo. La **potencia**, expresada en kilovatios o kW, representa la intensidad de uso de energía.

Por ejemplo, una carga que mantiene 2 kW durante tres horas consume 6 kWh. Para un bloque de quince minutos completamente cubierto por una medición de energía, la potencia media se obtiene dividiendo los kWh entre 0,25 horas: 5 kWh en ese bloque equivalen a una potencia media de 20 kW.

Esta diferencia explica por qué el costo eléctrico no se interpreta únicamente desde el consumo acumulado. La concentración del uso en determinados intervalos también importa. Los promedios horarios no permiten recuperar con exactitud un máximo de quince minutos.

### 7.3. Medición por usos o submedición

La separación de consumos por sistemas permite pasar de una cifra general a una descripción de los usos de la energía. En ECS-EC, las categorías actúan como unidades de análisis para identificar qué parte del edificio concentra el consumo y cuándo ocurre.

La representatividad depende de la cobertura de los medidores. La suma de categorías disponibles describe esa base de medición; la lectura general representa su punto físico de medida. Conservar ambas procedencias evita atribuir a las categorías una cobertura que no tienen.

### 7.4. Series temporales y agregación

Las mediciones forman una serie temporal: valores asociados a intervalos ordenados. Su agrupación facilita reconocer patrones diarios, mensuales o anuales.

La energía de un período se obtiene sumando las contribuciones válidas de ese período una sola vez. Los límites temporales y la zona horaria forman parte del significado del resultado. Los cambios de hora pueden producir días de distinta duración y horas locales repetidas, por lo que el sistema conserva referencias que permiten distinguirlas.

Cuando la fuente entrega un contador acumulado, el consumo se obtiene de diferencias entre lecturas válidas consecutivas. La primera lectura establece una referencia; por sí sola no determina un consumo anterior.

### 7.5. Calidad, cobertura y trazabilidad

La calidad de la información comprende su validez, completitud, consistencia y relación con una fuente identificada. La cobertura temporal expresa cuánto del período está respaldado por las mediciones incluidas:

**Cobertura = duración cubierta por mediciones válidas ÷ duración real del período × 100.**

Si una hora terminada contiene tres intervalos de quince minutos con 1 kWh cada uno, el resultado disponible es 3 kWh y su cobertura es 75 %. La plataforma conserva ambas cifras para evitar que una suma parcial parezca un consumo completo.

La trazabilidad permite responder de dónde proviene un valor, a qué período corresponde y qué reglas produjeron un resultado. En consumo relaciona categorías y fuentes; en costos relaciona mediciones, parámetros y vigencias; en reportes identifica el corte de datos; y en administración conserva los cambios realizados.

### 7.6. Tarificación y comparación económica

La Comisión Nacional de Energía describe BT4.3 como una opción de medición de energía y demanda máxima, que distingue demanda en horas de punta y demanda máxima suministrada. Esta estructura fundamenta que ECS-EC mantenga separados el consumo energético y las bases de demanda. [Fuente: CNE, opciones tarifarias a usuarios finales](https://www.cne.cl/tarificacion/electrica/valor-agregado-de-distribucion/opciones-tarifarias-a-usuarios-finales/).

La aplicación concreta de los cargos utiliza el perfil documentado del suministro y sus vigencias. El sistema conserva las referencias de cada cálculo, en lugar de interpretar una descripción general de BT4.3 como una lista universal de precios.

La comparación económica exige equivalencia: mismo suministro, ciclo, moneda, concepto y tratamiento tributario. Este principio permite que una diferencia sea interpretable y evita comparar un subtotal energético con un total que también incorpora deudas u otros conceptos.

### 7.7. Seguridad y observación del sistema

La separación de responsabilidades limita cada acceso a las funciones que necesita. La consulta cotidiana, la administración y el diagnóstico técnico mantienen permisos distintos. La auditoría registra decisiones relevantes y la supervisión ayuda a investigar problemas de funcionamiento.

La observabilidad combina registros, métricas y trazas para comprender el comportamiento de una aplicación. ECS-EC aplica esa idea mediante señales correlacionadas y un entorno técnico separado. [Fuente: OpenTelemetry, introducción a la observabilidad](https://opentelemetry.io/docs/concepts/observability-primer/).

## 8. Estado del arte tecnológico y posición de ECS-EC

### 8.1. Referentes del sector

El monitoreo energético de edificios reúne distintas familias de herramientas. Para contextualizar el proyecto se consideran referentes de adquisición de datos, análisis eléctrico, seguimiento energético y diagnóstico de aplicaciones. La comparación es funcional: no constituye una clasificación comercial ni afirma superioridad de un producto sobre otro.

| Referente | Capacidad documentada | Relación con ECS-EC |
| --- | --- | --- |
| Concentradores EcoStruxure Panel Server | Publicación de datos adquiridos en archivos CSV o JSON mediante SFTP | Referente de interoperabilidad para la recepción y la simulación de archivos. |
| EcoStruxure Power Monitoring Expert | Visualización de datos eléctricos históricos mediante paneles y reportes | Contextualiza la combinación de medición, consulta visual e información resumida. |
| ENERGY STAR Portfolio Manager | Seguimiento y comparación del desempeño energético de edificios | Representa el uso de historiales e indicadores para dar contexto al consumo. |
| OpenTelemetry | Instrumentación y conceptos comunes para registros, métricas y trazas | Fundamenta la supervisión técnica separada de las funciones de negocio. |

Las capacidades anteriores se describen en la [guía oficial de Panel Server](https://download.se.com/files?p_Doc_Ref=DOCA0172EN&p_enDocType=User+guide), la [documentación de visualizaciones y reportes de Schneider Electric](https://productinfo.se.com/esxp_digital_apps_nema/viewer?docidentity=Outputs-C9FEF281&extension=xml&lang=en&manualidentity=EDMA-NEMA-0995DB98), la [presentación de Portfolio Manager de ENERGY STAR](https://www.energystar.gov/buildings/benchmark?testEnv=false) y la [documentación de OpenTelemetry](https://opentelemetry.io/docs/concepts/observability-primer/).

Estos referentes muestran que la adquisición de mediciones, la consulta histórica y la presentación de resultados forman parte de enfoques establecidos. El aporte de ECS-EC es su integración para el contexto específico de ECS: siete categorías, reglas explícitas de calidad, análisis BT4.3 del suministro general, contraste con boletas, síntesis de una página y comunicaciones autorizadas.

La comparación con Portfolio Manager aporta contexto sobre el seguimiento energético; ECS-EC concentra su análisis en el edificio y su propia historia. Las capacidades de los referentes no se atribuyen automáticamente al proyecto.

### 8.2. Tecnologías utilizadas y su función

La solución emplea herramientas con responsabilidades definidas. Los nombres siguientes identifican sus componentes principales; su utilidad se expresa en términos del servicio que prestan.

| Componente | Tecnologías | Función en la solución |
| --- | --- | --- |
| Interfaz web | React, Next.js y TypeScript | Presentan navegación, formularios, gráficos, tablas y estados de consulta en el navegador. |
| Procesamiento central | Python y FastAPI | Aplican validaciones, permisos y reglas de consumo, costos, reportes y notificaciones. |
| Almacenamiento | PostgreSQL | Conserva mediciones, cuentas, revisiones y resultados relacionados de forma consistente. |
| Recepción de archivos | SFTP, CSV y JSON | Permiten recibir publicaciones de medición y reconocer sus datos. |
| Documentos | ReportLab | Compone los reportes PDF. |
| Correo | SMTP | Transfiere las notificaciones al servicio de correo configurado. |
| Diagnóstico técnico | Loguru, Alloy, Loki, Grafana, OpenTelemetry y Jaeger | Registran, reúnen y permiten consultar señales de funcionamiento. |
| Ejecución | Docker Compose y un servidor virtual privado | Mantienen una configuración reproducible y el acceso web centralizado. |

ECS-EC se organiza como una única aplicación con módulos internos de responsabilidades separadas. Esta arquitectura, denominada **monolito modular**, permite mantener unidos el despliegue y las reglas compartidas, conservando límites entre consumo, costos, reportes, identidad y notificaciones.

La interfaz se construye como archivos web y los datos privados se consultan mediante solicitudes autenticadas al procesamiento central. La base de datos, el servicio de correo y las herramientas de supervisión cumplen funciones de infraestructura con sus propios accesos.

El criterio tecnológico prioriza coherencia, mantenimiento y reproducibilidad para el alcance del edificio. La utilidad del proyecto reside en la integración y en la fidelidad de sus resultados, más que en la cantidad de herramientas utilizadas.

## 9. Metodología del proyecto

### 9.1. Enfoque aplicado y orientado a una solución

El proyecto aborda una necesidad concreta de ECS mediante la construcción de un producto de software. Su enfoque metodológico combina análisis de necesidades, especificación de comportamientos, diseño por responsabilidades, implementación incremental y evaluación mediante escenarios conocidos.

Desde una perspectiva académica, el trabajo se describe como desarrollo aplicado de una solución tecnológica. Su objeto de evaluación es el sistema y la correspondencia entre sus resultados y los requisitos. Los ensayos con datos controlados permiten comprobar comportamiento; una conclusión sobre ahorro real exige un análisis energético adicional con condiciones comparables.

### 9.2. Desarrollo guiado por especificaciones

El proyecto utiliza Spec Kit para estructurar un desarrollo guiado por especificaciones. En este enfoque, el comportamiento esperado se describe antes de traducirlo a decisiones de diseño y tareas de construcción. La documentación oficial de la herramienta presenta esa relación entre especificación, planificación y ejecución. [Fuente: repositorio oficial de GitHub Spec Kit](https://github.com/github/spec-kit).

En ECS-EC, cada funcionalidad mantiene historias de usuario, reglas, criterios de aceptación y contratos de intercambio de información. Una historia explica qué necesita una persona y para qué; un criterio de aceptación define una condición verificable para evaluar la respuesta del sistema.

La constitución del proyecto aporta cinco principios comunes: foco en el monitoreo eléctrico, arquitectura modular en una sola aplicación, documentación integral, integridad y trazabilidad de los datos, y visualización comprensible y verificable.

### 9.3. Organización del trabajo

La metodología se articula mediante las siguientes actividades:

1. **Definición de necesidades.** Identificación de perfiles, consultas, decisiones y datos requeridos para monitorear el edificio.
2. **Especificación funcional.** Descripción de comportamientos normales, restricciones, situaciones de error y criterios de aceptación.
3. **Análisis de referencias.** Consulta de documentación de equipos, conceptos energéticos, reglas tarifarias y herramientas tecnológicas.
4. **Diseño de responsabilidades.** Separación de módulos y definición de cómo intercambian información sin duplicar reglas.
5. **Construcción incremental.** Organización de las capacidades según sus dependencias, desde la base común hasta las consultas y comunicaciones.
6. **Verificación y revisión.** Comparación de resultados con valores conocidos, comprobación de permisos y revisión de la correspondencia entre datos y presentación.
7. **Documentación operativa.** Registro de configuración, decisiones, procedimientos de ejecución, respaldo y restauración.

La revisión de consistencia vincula necesidad, regla, cálculo, pantalla y prueba. Por ejemplo, la regla de no convertir una ausencia en cero se aplica en la recepción, los agregados, los gráficos, los PDF y la evaluación de alertas.

### 9.4. Estrategia de evaluación

La evaluación combina varios niveles:

| Nivel | Qué examina | Ejemplo |
| --- | --- | --- |
| Reglas de cálculo | Exactitud de conversiones, sumas, cobertura y redondeo | Verificar que tres intervalos de 1 kWh suman 3 kWh. |
| Integración | Coherencia entre recepción, almacenamiento y consumidores | Comprobar que una medición aceptada aparece en el historial y en su resumen. |
| Intercambio entre módulos | Respeto de los datos y significados compartidos | Verificar que PDF y notificaciones conservan el origen del total. |
| Uso de la interfaz | Recorridos completos, filtros y correspondencia visual | Seleccionar categoría y período, y contrastar gráfico con tabla. |
| Seguridad | Autorización efectiva y protección de datos | Denegar cambios administrativos a una cuenta Operador. |
| Resistencia a fallos | Recuperación y preservación de estados válidos | Interrumpir un envío, reiniciar y revisar su resultado sin duplicar registros. |
| Comprensión | Interpretación de valores, períodos y limitaciones | Reconocer si un resultado está completo o representa solo información parcial. |

Las pruebas utilizan bases separadas de la información operativa. Los escenarios abarcan datos ausentes, ceros válidos, duplicados, conflictos, retrasos, cambios de hora, años bisiestos y operaciones concurrentes. El simulador aporta una referencia controlada para los ensayos de recepción.

Los criterios de evaluación se expresan como resultados observables: exactitud frente a valores conocidos, conservación durante los plazos establecidos, rechazo de acciones no autorizadas, coherencia de representaciones y legibilidad del PDF. Estos criterios explican cómo se juzga la calidad del producto; no representan porcentajes de ahorro ni resultados de estudios con personas.

## 10. Aporte del proyecto para ECS

ECS-EC convierte el monitoreo eléctrico en un proceso continuo de consulta, interpretación y comunicación. Para la operación, facilita reconocer la evolución de cada categoría y revisar situaciones que requieren atención. Para la administración, reúne condiciones tarifarias, boletas y cálculos con antecedentes identificables. Para la comunicación, produce resúmenes que conservan el contexto necesario fuera de la plataforma.

La calidad de los datos forma parte de ese aporte. Una cifra acompañada de su origen, cobertura y período ofrece una base más útil que un valor aislado. Del mismo modo, un cálculo conserva su valor explicativo cuando permite revisar las condiciones que lo produjeron.

El resultado para ECS es una fuente centralizada de información eléctrica con responsabilidades claras: quién consulta, quién administra y quién diagnostica. La plataforma apoya decisiones documentadas sobre el edificio y permite explicar sus resultados a personas que no participan de su implementación técnica.

## 11. Glosario breve

| Término | Explicación |
| --- | --- |
| BT4.3 | Opción tarifaria de baja tensión que considera energía y mediciones de demanda máxima. |
| Ciclo de facturación | Intervalo de consumo al que corresponde una boleta; puede diferir del mes calendario. |
| Cobertura | Parte del período respaldada por las mediciones válidas incluidas. |
| Corte de datos | Momento de referencia que delimita la información utilizada en una consulta o reporte. |
| Demanda | Potencia utilizada en un intervalo, relevante para determinados cargos eléctricos. |
| HVAC | Calefacción, ventilación y aire acondicionado. |
| kW | Unidad de potencia eléctrica. |
| kWh | Unidad de energía eléctrica consumida durante un intervalo. |
| PAS600 | Concentrador que reúne y publica información de dispositivos de medición. |
| Revisión | Versión identificada de un registro, configuración o cálculo. |
| SFTP | Mecanismo cifrado de transferencia de archivos. |
| Submedición | Medición de partes o usos específicos de una instalación. |
| Trazabilidad | Relación verificable entre un resultado y sus fuentes, reglas y cambios. |
| VPS | Servidor virtual privado que aloja la aplicación. |

## 12. Base documental del proyecto

La descripción integra el [contexto de producto](PRODUCT.md), la [arquitectura compartida](docs/architecture.md), los [principios del proyecto](.specify/memory/constitution.md) y las nueve especificaciones. La cobertura de cada una es la siguiente:

| Especificación | Contenido integrado en este documento |
| --- | --- |
| [001. Consumo por categorías](specs/001-visualizar-consumo-categorias/spec.md) | Categorías, visualización, validación y procedencia de los totales. |
| [002. Registro y conservación](specs/002-registro-retencion-consumo/spec.md) | Recepción, historial, agrupaciones, cobertura y conservación mínima. |
| [003. PAS600 y simulación](specs/003-simulador-pas600-sftp/spec.md) | Publicaciones, recepción SFTP y pruebas reproducibles con anomalías. |
| [004. Costos BT4.3](specs/004-costos-tarifa-bt43/spec.md) | Desglose, vigencias, demanda, boletas y comparación económica. |
| [005. Reportes PDF](specs/005-generar-reportes-pdf/spec.md) | Síntesis diaria, mensual y anual en una página. |
| [006. Acceso y usuarios](specs/006-acceso-usuarios-rbac/spec.md) | Cuentas, sesiones, permisos y administración con trazabilidad. |
| [007. Observabilidad](specs/007-observabilidad-externa/spec.md) | Diagnóstico técnico, protección de señales y separación de accesos. |
| [008. Notificaciones](specs/008-notificaciones-programables/spec.md) | Programación, condiciones, destinatarios e historial de entregas. |
| [009. Plataforma común](specs/009-fundaciones-plataforma/spec.md) | Infraestructura, persistencia, auditoría, respaldo y operación compartida. |

Las referencias externas junto a los fundamentos y al estado del arte respaldan sus conceptos y referentes tecnológicos. Las reglas particulares del producto proceden de las especificaciones de ECS-EC y se presentan aquí en lenguaje orientado a lectores externos.
