# Feature Specification: Observabilidad técnica externa y rol Programador

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "ECS-EC debe contemplar técnicas de observabilidad para logs,
métricas y trazas. Las tecnologías todavía no se especifican, pero se decide implementar
un módulo de observabilidad. Este apartado técnico debe estar fuera de la plataforma
funcional. Operador y Administrador técnico no tendrán acceso directo; se incorpora el
rol Programador."

**Clarificación recibida**: Programador tiene acceso solo a observabilidad externa y no
hereda permisos funcionales del Administrador técnico dentro de ECS-EC.

**Especificaciones relacionadas**:
[spec-001: consulta de consumos](../001-visualizar-consumo-categorias/spec.md),
[spec-002: recepción e historial](../002-registro-retencion-consumo/spec.md),
[spec-003: publicación SFTP y simulación](../003-simulador-pas600-sftp/spec.md),
[spec-004: costos y boletas](../004-costos-tarifa-bt43/spec.md),
[spec-005: reportes PDF](../005-generar-reportes-pdf/spec.md) y
[spec-006: identidad y permisos funcionales](../006-acceso-usuarios-rbac/spec.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceder a la observabilidad como Programador (Priority: P1)

Como Programador autorizado, quiero consultar la información técnica en un entorno externo
a las vistas funcionales para diagnosticar el sistema sin administrar sus datos de negocio.

**Why this priority**: Define quién puede usar el nuevo módulo y preserva la separación
solicitada respecto de los perfiles de la plataforma.

**Independent Test**: Preparar identidades de los tres roles y una identidad sin autorización;
comprobar acceso técnico, funciones web y solicitudes directas de consulta de señales.

**Acceptance Scenarios**:

1. **Given** una identidad autenticada y autorizada como Programador,
   **When** solicita consultar logs, métricas o trazas en el entorno técnico externo,
   **Then** puede hacerlo dentro de los entornos para los que está habilitada.
2. **Given** un Operador o Administrador técnico autenticado en ECS-EC,
   **When** intenta acceder directamente al módulo, sus fuentes de consulta o señales,
   **Then** se deniega el acceso y la navegación funcional no ofrece un visor de observabilidad.
3. **Given** una persona sin autorización técnica o que declara por sí misma el rol Programador,
   **When** solicita señales, **Then** no recibe información y no obtiene permisos por esa declaración.
4. **Given** una identidad habilitada solo como Programador,
   **When** intenta consultar datos funcionales, generar PDF o administrar usuarios y configuración
   de ECS-EC, **Then** ese rol no le concede acceso a dichas funciones.
5. **Given** un Administrador técnico que gestiona cuentas de la spec-006,
   **When** intenta conceder acceso a observabilidad mediante esa gestión,
   **Then** la operación no concede el rol técnico externo ni permite autoasignárselo.
6. **Given** un Programador cuya autorización técnica se revoca,
   **When** solicita una nueva consulta o entrega de señales,
   **Then** se rechaza aunque antes hubiera accedido.
7. **Given** el historial administrativo funcional de la spec-006,
   **When** lo consulta un Administrador técnico,
   **Then** conserva ese permiso sin obtener por ello acceso a los logs, métricas o trazas externos.

---

### User Story 2 - Relacionar un incidente mediante logs y trazas (Priority: P1)

Como Programador, quiero localizar los eventos y etapas de una operación para reconocer
su resultado, dónde falló y qué ocurrió antes o después.

**Why this priority**: Las señales deben permitir seguir una operación concreta y distinguir
un fallo del sistema de un rechazo esperado de datos o permisos.

**Independent Test**: Ejecutar operaciones de referencia correctas, fallidas y con rechazo
esperado; localizar sus logs y recorrer las etapas relacionadas de sus trazas.

**Acceptance Scenarios**:

1. **Given** una recepción SFTP válida que pasa por validación, conservación y agregación,
   **When** se consulta su referencia de operación,
   **Then** se relacionan eventos y etapas con sus tiempos, resultados y contexto técnico.
2. **Given** registros inválidos, duplicados o una actualización anticipada conforme a la spec-002,
   **When** se observa su procesamiento,
   **Then** se identifica el rechazo esperado y su motivo técnico sin presentarlo como una
   excepción imprevista de la aplicación.
3. **Given** un fallo inesperado durante un cálculo o generación PDF,
   **When** se investiga la operación,
   **Then** puede localizarse la etapa fallida y su relación con los demás eventos sin
   revelar en la respuesta funcional detalles internos del fallo.
4. **Given** una operación que continúa después de su solicitud inicial,
   **When** se completa o falla su procesamiento posterior,
   **Then** se conserva la relación entre la solicitud y sus etapas posteriores.
5. **Given** una publicación nativa PAS600 reintentada,
   **When** se comparan los intentos,
   **Then** pueden relacionarse con la misma publicación y distinguirse los intentos,
   sin añadir campos a CSV o JSON ni modificar el contrato SFTP de la spec-003.
6. **Given** eventos de dos operaciones distintas,
   **When** se consulta una referencia,
   **Then** no se mezclan por coincidencias en textos, nombres de archivo o valores enviados
   por una fuente; un contexto no disponible se identifica como tal.

---

### User Story 3 - Revisar métricas de funcionamiento (Priority: P1)

Como Programador, quiero consultar volúmenes, resultados y tiempos de las operaciones
para reconocer errores, demoras y ausencia de actividad observable.

**Why this priority**: Las métricas ofrecen una visión agregada que complementa el diagnóstico
de operaciones individuales.

**Independent Test**: Ejecutar una carga conocida y comparar los conteos, proporciones,
duraciones y disponibilidad de señales con los resultados esperados del mismo intervalo.

**Acceptance Scenarios**:

1. **Given** diez consultas terminadas, ocho correctas y dos con fallo inesperado,
   **When** se consultan sus métricas en la misma ventana,
   **Then** se identifican diez operaciones, ocho resultados correctos, dos errores y
   una proporción de error del 20 %, con unidades y período visibles.
2. **Given** una recepción con cinco registros, tres aceptados, uno inválido y uno duplicado,
   **When** se revisan sus métricas,
   **Then** se distinguen el conteo de operaciones y el de registros, con los resultados esperados,
   sin confundir una recepción con cinco actualizaciones independientes.
3. **Given** operaciones con duraciones conocidas,
   **When** se consultan tiempos y distribuciones disponibles,
   **Then** se identifican la unidad, el tipo de operación y la ventana de cálculo, sin
   confundir tiempos de procesamiento con intervalos de medición eléctrica.
4. **Given** una interrupción de recolección,
   **When** se consulta la ventana afectada,
   **Then** se distingue ausencia de señales de una actividad medida igual a cero.
5. **Given** muchas operaciones nuevas con referencias distintas y las mismas dimensiones
   de agregación, **When** se reciben sus métricas,
   **Then** no se crea una serie independiente por usuario, archivo o referencia de operación.

---

### User Story 4 - Mantener una observación segura e independiente (Priority: P2)

Como Programador, quiero conocer los límites y la disponibilidad de la telemetría para
diagnosticar el sistema sin exponer datos funcionales ni interrumpir su operación.

**Why this priority**: La observabilidad debe aportar información técnica confiable y
respetar tanto las restricciones de acceso como la continuidad del monolito.

**Independent Test**: Interrumpir la recolección, superar límites de prueba de emisión,
introducir contenido sensible en operaciones controladas y aplicar políticas de conservación
y muestreo conocidas.

**Acceptance Scenarios**:

1. **Given** una operación de referencia con contraseñas, claves de integración, datos
   personales o contenido de boleta en sus entradas,
   **When** se consultan sus señales,
   **Then** no aparecen esos contenidos ni cuerpos completos de mensajes, archivos o reportes.
2. **Given** el entorno receptor de telemetría temporalmente indisponible,
   **When** se realizan consultas, recepciones válidas o generaciones PDF,
   **Then** conservan sus resultados funcionales esperados sin requerir que el receptor se recupere.
3. **Given** límites de recursos de emisión configurados para una prueba,
   **When** se supera su capacidad,
   **Then** no se supera el límite definido, se reconoce la pérdida o interrupción de señales
   y no se descartan mediciones de negocio por ese motivo.
4. **Given** una política de conservación técnica con plazo de prueba conocido,
   **When** se cumple ese plazo,
   **Then** se aplica únicamente a las señales correspondientes, sin reducir la conservación
   de mediciones, boletas, cálculos o evidencias funcionales de las specs anteriores.
5. **Given** muestreo habilitado o datos técnicos ya no conservados,
   **When** se consulta una operación no disponible,
   **Then** se identifica esa limitación y no se afirma que la operación nunca ocurrió.
6. **Given** dos entornos o versiones de la aplicación,
   **When** se investiga uno de ellos,
   **Then** las señales pueden distinguirse por entorno y versión y no se accede a un
   entorno para el que la identidad no está autorizada.
7. **Given** una política de referencia que conserva todas las trazas durante la prueba,
   **When** se ejecutan los casos de diagnóstico,
   **Then** las operaciones incluidas en la cobertura definida tienen sus logs, métricas
   y trazas verificables sin depender de una tecnología específica.
8. **Given** productores y recolectores con identidades técnicas autorizadas y ninguna
   sesión humana abierta, **When** se ejecutan operaciones observadas, **Then** las señales
   se recolectan sin exigir el ingreso de un Programador y sin conceder acceso humano
   a quienes solo tengan credenciales de integración.
9. **Given** ECS-EC y sus componentes o sustitutos de observabilidad de prueba locales,
   **When** se ejecuta una operación cubierta y se revisan sus señales como Programador,
   **Then** se pueden consultar y correlacionar logs, métricas y trazas sin servicios
   remotos; Operador y Administrador técnico conservan el acceso denegado a esas señales.

### Edge Cases

- El rol Programador no es una ampliación de los permisos del Administrador técnico ni un
  acceso implícito a datos, boletas, usuarios o administración funcional.
- La autenticación de una cuenta web de ECS-EC no equivale a autorización para consultar
  las fuentes o herramientas técnicas externas.
- El historial administrativo funcional de la spec-006 y los logs técnicos tienen fines
  y permisos de consulta diferentes, aunque puedan referirse a un mismo suceso.
- Datos defectuosos del simulador y denegaciones de acceso esperadas no se clasifican
  automáticamente como fallos inesperados del sistema.
- Un envío puede contener múltiples archivos y registros; los conteos deben indicar su unidad.
- Un reintento o una operación posterior relacionada necesita una referencia que permita
  reconocer su relación y también distinguir cada ejecución.
- Las marcas temporales de telemetría corresponden a ejecución u observación técnica,
  no reemplazan el período de las mediciones eléctricas recibidas.
- La falta de señal por muestreo, retención, pérdida o interrupción no es un valor cero
  ni prueba suficiente de ausencia de operación.
- Los identificadores libres, nombres de archivo y datos recibidos no deben crear nuevas
  dimensiones de métricas por cada valor distinto.
- Un texto recibido no puede convertirse en una severidad, identidad o referencia técnica
  confiable solo por incluir una cadena que parezca un evento.
- El mínimo de 12 meses de las specs-002 y 004 no se aplica automáticamente a toda la telemetría.
- La ausencia de una elección tecnológica no elimina la obligación de definir las tres
  señales y sus casos verificables.

## Requirements *(mandatory)*

### Functional Requirements

La ampliación de permisos distingue el ámbito funcional del técnico:

| Acción | Operador | Administrador técnico | Programador | Sin autorización |
| --- | --- | --- | --- | --- |
| Consultas y PDF funcionales de ECS-EC | Permitido | Permitido | Denegado | Denegado |
| Administración funcional de usuarios y sistema | Denegado | Permitido | Denegado | Denegado |
| Historial administrativo funcional de la spec-006 | Denegado | Permitido | Denegado | Denegado |
| Consulta externa de logs técnicos | Denegado | Denegado | Permitido | Denegado |
| Consulta externa de métricas técnicas | Denegado | Denegado | Permitido | Denegado |
| Consulta externa de trazas | Denegado | Denegado | Permitido | Denegado |

- **FR-001**: ECS-EC DEBE incorporar observabilidad con logs, métricas y trazas. Su consulta
  DEBE realizarse en un entorno técnico externo a las vistas funcionales de la plataforma,
  sin visores de observabilidad en su navegación o reportes funcionales.
- **FR-002**: El catálogo de roles DEBE ampliarse con Programador para el ámbito técnico
  externo. Este rol DEBE limitarse a consulta y diagnóstico de observabilidad y NO DEBE
  heredar consultas, PDF ni administración funcional de los otros perfiles.
- **FR-003**: Operador y Administrador técnico NO DEBEN acceder directamente a ninguna de
  las tres señales, sus visores ni sus fuentes de consulta por sus permisos funcionales.
  La gestión de cuentas web de la spec-006 NO DEBE conceder ni autoasignar acceso técnico externo.
- **FR-004**: Toda consulta o entrega de señales a una persona DEBE comprobar una identidad
  autenticada, autorización Programador y entorno permitido. Los accesos no autorizados
  DEBEN denegarse sin revelar telemetría; la revocación DEBE aplicarse antes de la siguiente
  consulta o entrega. La recolección automática DEBE autorizar sus propias identidades
  técnicas sin convertirlas en un permiso de consulta humana.
- **FR-005**: El módulo DEBE cubrir recepción e interpretación SFTP, validación y conservación
  de datos, agregaciones y consultas, cálculo y contraste de costos, generación PDF,
  autenticación y autorización, y cambios administrativos de las specs-001 a 006.
- **FR-006**: Los logs DEBEN ser estructurados y contener fecha con referencia temporal
  inequívoca, entorno, versión, operación o etapa, severidad, resultado y referencia de
  correlación cuando exista. Los fallos DEBEN incluir un código o clasificación técnica interpretable.
- **FR-007**: Los resultados DEBEN distinguir operación correcta, rechazo esperado de datos
  o permisos y fallo inesperado. Las señales de una operación DEBEN conservar el mismo
  significado de resultado, sin convertir rechazos previstos en errores imprevistos.
- **FR-008**: Las métricas DEBEN incluir volúmenes y resultados de operaciones, proporciones
  de error, tiempos de procesamiento y estado de disponibilidad de recolección. Para la
  recepción DEBEN distinguir operaciones, archivos y registros aceptados, inválidos o duplicados.
- **FR-009**: Cada métrica DEBE definir nombre comprensible, unidad, hecho que cuenta o mide,
  ventana y criterio de agregación. Los reintentos y fragmentos DEBEN contabilizarse según
  esa definición y no inflar artificialmente los conteos de operaciones o registros únicos.
  Las proporciones DEBEN identificar numerador y denominador; con denominador cero o no
  disponible DEBEN indicar que no pueden calcularse, sin presentar un porcentaje ficticio.
- **FR-010**: Las dimensiones de métricas DEBEN pertenecer a conjuntos definidos, como
  entorno, función, resultado y categoría conocida. NO DEBEN usarse como dimensiones
  identidades de personas, nombres libres de archivo o referencias únicas de cada operación.
- **FR-011**: Las trazas DEBEN permitir reconocer el comienzo, las etapas relevantes,
  sus relaciones, duración y resultado final de las operaciones cubiertas. La correlación
  DEBE mantenerse cuando el procesamiento continúe después de la solicitud inicial.
- **FR-012**: Logs y trazas DEBEN poder relacionarse mediante referencias técnicas de
  operación o publicación, con el contexto de entorno correspondiente. Cada intento DEBE
  distinguirse sin perder su relación con una publicación reintentada.
- **FR-013**: La correlación NO DEBE exigir cambios en los archivos nativos PAS600, las
  credenciales SFTP, las mediciones, boletas o PDF funcionales. Referencias declaradas por
  fuentes no confiables NO DEBEN aceptarse como identidades o relaciones técnicas verificadas.
- **FR-014**: Programador DEBE poder acotar consultas por período y entorno y, según la señal,
  por función, resultado, severidad o referencia de operación. DEBE poder pasar del contexto
  agregado de una incidencia a sus eventos y etapas disponibles.
- **FR-015**: Las señales NO DEBEN contener contraseñas, secretos de sesión, claves de
  integración, datos personales de usuarios, cuerpos de archivos o boletas, contenido de
  PDF ni valores individuales de consumo o facturación. DEBEN utilizar contexto técnico
  suficiente, referencias opacas y motivos de validación sin exponer esos contenidos.
  La exclusión o redacción DEBE aplicarse antes de emitir o conservar las señales.
- **FR-016**: Los textos y errores recibidos DEBEN tratarse como datos no confiables y
  preservar la estructura de los eventos. Los mensajes funcionales NO DEBEN exponer trazas
  internas, credenciales ni detalles técnicos de excepción de este módulo.
- **FR-017**: Una falla de emisión, recolección o consulta de observabilidad NO DEBE bloquear
  ni rechazar por sí sola las operaciones funcionales del monolito ni provocar pérdida de
  mediciones de negocio. Los recursos dedicados a emitir señales DEBEN tener límites definidos.
- **FR-018**: Las interrupciones, pérdida de señales y agotamiento de los límites configurados
  DEBEN poder reconocerse en el ámbito técnico, con su último dato disponible cuando exista.
  La ausencia de telemetría NO DEBE presentarse como actividad o errores medidos iguales a cero.
- **FR-019**: La conservación y el muestreo técnico DEBEN tener políticas explícitas por
  tipo de señal y entorno antes de activarse. Sus límites DEBEN ser verificables y las
  consultas DEBEN identificar sus efectos sobre la información disponible.
- **FR-020**: La conservación o retirada de señales técnicas NO DEBE alterar los registros,
  evidencias o plazos de conservación funcionales de las specs anteriores. El historial
  administrativo de la spec-006 DEBE conservar su finalidad y sus permisos propios.
- **FR-021**: La instrumentación que produce señales de ECS-EC DEBE formar parte del
  monolito y preservar su unidad de aplicación. El entorno de consulta técnica DEBE estar
  separado del uso funcional; su disponibilidad NO DEBE ser una dependencia obligatoria
  para operar las funciones de negocio.
- **FR-022**: La habilitación y revocación de Programador DEBEN realizarse mediante un
  procedimiento técnico externo documentado y separado de la administración funcional.
  La emisión automática de señales DEBE poder continuar sin una sesión humana abierta,
  mediante las autorizaciones técnicas que correspondan.
- **FR-023**: DEBEN documentarse el catálogo de señales, cobertura por operación, reglas
  de correlación, protección de datos, políticas y procedimiento de acceso técnico.
  Esta especificación NO DEBE fijar proveedores, productos, bibliotecas o protocolos de
  observabilidad; su selección corresponde al diseño técnico posterior.

- **FR-024**: La emisión, recolección y consulta de logs, métricas y trazas DEBEN poder
  verificarse con componentes o sustitutos de prueba locales, sin requerir servicios
  remotos de observabilidad. Este entorno DEBE mantener el catálogo de señales, la
  identificación de entorno, la protección de contenidos y la autorización exclusiva
  de Programador, separado de las vistas funcionales.

### Key Entities *(include if feature involves data)*

- **Identidad Programador**: Persona autenticada con autorización de consulta técnica y
  entornos permitidos; no obtiene un perfil funcional por esa autorización.
- **Evento de log**: Suceso estructurado de ejecución con severidad, resultado, entorno,
  tiempo y contexto técnico protegido.
- **Métrica técnica**: Conteo, proporción, duración o estado con unidad y dimensiones
  definidas, referido a una ventana y una operación conocidas.
- **Traza y etapa**: Seguimiento de una operación y sus pasos relacionados, incluidos
  procesamiento posterior, tiempos y resultados.
- **Referencia de correlación**: Identificación técnica que relaciona señales e intentos
  de una operación sin modificar los datos de negocio.
- **Política de telemetría**: Condiciones de cobertura, muestreo, conservación y recursos
  por señal y entorno, verificables con configuraciones de referencia.
- **Estado de recolección**: Información sobre continuidad, última señal y pérdidas o
  interrupciones que limita la interpretación de las consultas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las combinaciones de la matriz de permisos produce el resultado
  esperado, incluidos accesos directos, declaraciones de rol manipuladas y autorizaciones
  revocadas, sin entregar señales a perfiles funcionales ni acceso funcional a Programador.
- **SC-002**: Con cobertura completa durante las pruebas, todas las operaciones de referencia
  de las specs-001 a 006 cuentan con los logs, métricas y etapas de traza definidos para ellas,
  incluidos resultados correctos, rechazos esperados y fallos inesperados.
- **SC-003**: En todos los casos de referencia con carga conocida, los conteos y proporciones
  coinciden con los resultados ejecutados y las duraciones tienen unidad, ventana y
  valores no negativos, sin confundir operaciones, archivos y registros.
- **SC-004**: En el 100 % de los escenarios con procesamiento posterior o reintentos pueden
  relacionarse las señales de la misma operación y distinguirse ejecuciones diferentes,
  sin modificar los archivos de publicación ni mezclar entornos.
- **SC-005**: Ninguno de los valores sensibles introducidos en los casos de protección
  aparece en las señales consultables ni se entrega como detalle técnico en las vistas funcionales.
- **SC-006**: En todas las pruebas de indisponibilidad o saturación técnica, las operaciones
  funcionales de referencia mantienen sus resultados esperados, respetan los límites de
  emisión configurados y no pierden mediciones de negocio por el fallo de observabilidad.
- **SC-007**: En todos los escenarios de interrupción, muestreo o conservación técnica se
  identifican los límites de disponibilidad de las señales sin presentarlos como ceros
  medidos ni alterar el historial funcional.
- **SC-008**: En al menos 9 de 10 tareas de diagnóstico con Programadores representativos,
  la persona identifica sin ayuda la operación afectada, su resultado y etapa relevante
  mediante las señales disponibles y sus referencias.

- **SC-009**: En el escenario funcional local de referencia se generan y consultan las
  tres señales sin servicios remotos; Programador obtiene los resultados esperados y los
  perfiles funcionales o identidades sin autorización no acceden a ellas.

## Assumptions

- **Entornos local y VPS**: Se aplican las condiciones de la spec-001. Durante el desarrollo,
  la consulta técnica externa a las vistas funcionales puede ejecutarse en el mismo
  equipo local, manteniendo sus permisos y separación. El plan definirá la ubicación de
  sus componentes para la futura VPS sin hacerlos obligatorios para el desarrollo local.
  La exposición web de ECS-EC por internet no concede acceso público a las señales técnicas.
- **Tecnologías pendientes**: Se decide el módulo y sus capacidades, sin seleccionar
  herramientas, proveedores ni mecanismos de instrumentación, almacenamiento o consulta.
  El plan debe concretarlos posteriormente sin convertir la observabilidad en una sección funcional.
- **Ampliación de la spec-006**: Se amplía su catálogo humano con Programador de ámbito
  técnico externo. La exclusividad de sus dos perfiles se mantiene para el acceso funcional
  a ECS-EC, no para todo el entorno operativo. La matriz de esta spec concreta esa ampliación.
  La persona solicitante confirmó que Programador no hereda permisos funcionales.
- **Acceso e identidad**: El mecanismo de autenticación del entorno técnico se define en el
  diseño posterior; no se presupone reutilización de las sesiones o credenciales web.
  La autorización individual y por entorno es obligatoria cualquiera sea ese mecanismo.
  La provisión no se realiza desde el panel de usuarios de la spec-006.
- **Alcance de Programador**: El permiso inicial es consulta y diagnóstico de las tres señales.
  No concede administración de usuarios funcionales, ejecución del simulador, edición de
  mediciones, despliegues ni acceso general a bases de datos o secretos.
- **Separación del módulo**: Fuera de la plataforma significa fuera de las vistas y permisos
  funcionales. El monolito se instrumenta para emitir señales y el entorno técnico las
  recibe y permite consultarlas; no se divide la aplicación de negocio en servicios nuevos.
- **Operaciones observadas**: Se cubren funciones del monolito y el procesamiento recibido
  de las integraciones. El simulador de la spec-003 conserva su informe local; no se exige
  incorporarlo a la plataforma ni publicar cambios de formato para correlacionarlo.
- **Calidad frente a fallos técnicos**: Un registro inválido, duplicado o anticipado puede
  ser un resultado esperado. Las métricas deben permitir separarlo de una falla del sistema.
  Los indicadores técnicos no reemplazan los consumos y costos de las vistas funcionales.
- **Auditoría administrativa**: El historial de acciones de la spec-006 permanece disponible
  para el Administrador técnico bajo sus reglas. No constituye un visor de observabilidad
  ni habilita consulta de logs técnicos externos.
- **Políticas y recursos**: Los plazos de conservación técnica, muestreo y límites de emisión
  deben fijarse antes de activar la instrumentación, según el diseño y capacidad elegidos.
  Se prueban con valores de referencia explícitos; no se heredan automáticamente los
  12 meses de conservación funcional. No se impone en esta fase una frecuencia de muestreo
  ni un plazo de retención uniforme para las tres señales.
- **Disponibilidad y significado**: El entorno técnico debe permitir reconocer ventanas sin
  recolección y muestreo. Que no aparezca una traza no demuestra que no hubo una operación.
  Los reportes PDF y pantallas funcionales mantienen su contenido operativo y no incorporan
  telemetría interna para compensar una consulta técnica fallida.
- **Dependencias y límites**: Se requieren identificaciones de operación y entorno y las
  reglas de procesamiento de las specs-001 a 006. El plan debe verificar acceso externo,
  protección de contenidos, límites y correlación. No se incluyen notificaciones externas,
  reglas automáticas de actuación sobre el negocio ni elección tecnológica en esta especificación.

## Contexto de planificación compartido

Consultar [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). El [archivo de tareas](tasks.md)
conserva responsabilidades antes concentradas en 008 y debe integrarse al planificar
esta funcionalidad; no cambia sus requisitos ni acredita diseño o implementación completos.
