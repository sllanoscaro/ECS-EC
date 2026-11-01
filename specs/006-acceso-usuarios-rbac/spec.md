# Feature Specification: Autenticación y permisos por perfil

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "ECS-EC debe implementar RBAC para dos perfiles: Operador y
Administrador técnico. Ambos ingresan mediante correo y contraseña. El Operador tiene
permisos de lectura para visualizar datos y no accede a configuraciones. El Administrador
técnico hereda esos permisos y accede a la configuración de usuarios registrados y del sistema."

**Clarificación recibida**: El Operador puede generar y descargar los reportes PDF de la
spec-005 como una operación de lectura, sin modificar los datos del sistema.

**Especificaciones relacionadas**:
[spec-001: consumo por categorías](../001-visualizar-consumo-categorias/spec.md),
[spec-002: historial y recepción](../002-registro-retencion-consumo/spec.md),
[spec-003: integración PAS600](../003-simulador-pas600-sftp/spec.md),
[spec-004: costos y boletas](../004-costos-tarifa-bt43/spec.md) y
[spec-005: reportes PDF](../005-generar-reportes-pdf/spec.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingresar y salir con una cuenta identificada (Priority: P1)

Como persona registrada con cualquiera de los dos perfiles, quiero ingresar con mi correo
y contraseña y cerrar mi sesión para acceder a la plataforma con mis permisos vigentes.

**Why this priority**: La identidad debe conocerse antes de permitir acceso a los datos
y funciones de ECS-EC.

**Independent Test**: Preparar una cuenta activa por perfil y cuentas inactivas; comprobar
ingreso, rechazo de credenciales, cierre y vencimiento de sesión.

**Acceptance Scenarios**:

1. **Given** una cuenta activa de Operador o Administrador técnico y sus credenciales válidas,
   **When** inicia sesión, **Then** accede a la plataforma con su identidad y perfil vigentes.
2. **Given** un correo desconocido, contraseña incorrecta o cuenta inactiva,
   **When** se intenta ingresar, **Then** se rechaza el acceso con el mismo mensaje general,
   sin revelar cuál de esas condiciones ocurrió.
3. **Given** una persona sin sesión, **When** intenta consultar datos, configuraciones o
   descargar un reporte mediante un acceso directo, **Then** se exige autenticarse y no se
   entrega la información protegida.
4. **Given** una sesión abierta, **When** se cierra, **Then** las siguientes solicitudes
   protegidas requieren nuevo ingreso; reutilizar el acceso anterior no permite continuar.
5. **Given** una sesión que cumple el límite de inactividad o duración máxima,
   **When** intenta una acción protegida, **Then** se solicita un nuevo ingreso.
6. **Given** intentos fallidos consecutivos que alcanzan el umbral definido,
   **When** se vuelve a intentar durante la espera temporal, **Then** se informa que debe
   esperar y no se autentica, tanto para correos existentes como para desconocidos.
7. **Given** una contraseña inicial o restablecida que debe renovarse,
   **When** se ingresa con ella, **Then** solo se permite establecer una nueva contraseña
   propia y cerrar sesión hasta completar la renovación.
8. **Given** la futura instalación en VPS con su dirección pública,
   **When** se verifica el ingreso y una consulta protegida desde una red externa,
   **Then** ambas utilizan HTTPS y conservan los permisos del perfil; un acceso sin
   protección de transporte no permite autenticarse ni obtener información protegida.
9. **Given** un entorno local con una cuenta de prueba activa por perfil,
   **When** se ejecutan los casos de ingreso, rechazo, permisos y cierre de sesión,
   **Then** se obtienen los mismos resultados de autorización previstos por la matriz,
   sin una VPS ni servicios remotos de identidad.

---

### User Story 2 - Consultar información como Operador (Priority: P1)

Como Operador, quiero consultar consumo, historial, costos, boletas y reportes sin poder
modificar datos o configuraciones para realizar el monitoreo del edificio.

**Why this priority**: Es el alcance de lectura solicitado y debe aplicarse a todas las
funcionalidades ya especificadas.

**Independent Test**: Iniciar sesión como Operador, recorrer las funciones de consulta y PDF,
y verificar que las funciones administrativas se rechacen también por acceso directo.

**Acceptance Scenarios**:

1. **Given** una sesión de Operador, **When** consulta las siete categorías, gráficos, tablas,
   historial, costos BT4.3 o boletas registradas, **Then** puede visualizar los datos y sus
   referencias de negocio y cambiar filtros sin modificar las fuentes.
2. **Given** una sesión de Operador, **When** selecciona un período y genera o descarga un PDF,
   **Then** obtiene el reporte de la spec-005 sin adquirir permisos para modificar mediciones,
   tarifas, boletas o configuración.
3. **Given** una sesión de Operador, **When** accede a la navegación,
   **Then** no se ofrecen las secciones de administración de usuarios ni configuración.
4. **Given** esa sesión y una solicitud directa para leer o modificar usuarios o configuración,
   **When** se evalúa la solicitud, **Then** se deniega sin revelar los datos administrativos
   ni efectuar cambios, aunque el acceso no provenga de la navegación habitual.
5. **Given** una sesión de Operador, **When** se intenta registrar o corregir una boleta,
   guardar una tarifa o forzar un recálculo que cree una revisión de negocio,
   **Then** se deniega y permanecen los datos anteriores.
6. **Given** una sesión de Operador y datos manipulados que declaran un perfil administrativo,
   **When** se solicita una operación, **Then** los permisos se obtienen de la cuenta vigente
   y no de la declaración enviada por la persona.
7. **Given** un reporte generado antes de desactivar la cuenta o cerrar su sesión,
   **When** se intenta obtenerlo de la plataforma después del cambio,
   **Then** la descarga vuelve a comprobar el acceso y se rechaza si ya no existe autorización.

---

### User Story 3 - Administrar cuentas y sus perfiles (Priority: P1)

Como Administrador técnico, quiero registrar, actualizar y desactivar cuentas y asignar
sus perfiles para mantener quién puede consultar o administrar ECS-EC.

**Why this priority**: La administración de usuarios es un permiso exclusivo solicitado.

**Independent Test**: Usar una cuenta administrativa para crear cuentas de ambos perfiles,
cambiar sus datos y estado y verificar la aplicación de los permisos en sesiones existentes.

**Acceptance Scenarios**:

1. **Given** una sesión administrativa, **When** registra un correo admisible y único,
   un perfil permitido y una contraseña inicial válida,
   **Then** se crea la cuenta con su estado y obligación de renovar la contraseña al ingresar.
2. **Given** una cuenta ya registrada, **When** se intenta crear otra con el mismo correo
   variando mayúsculas o espacios al inicio o final, **Then** se rechaza la duplicación.
3. **Given** una cuenta registrada, **When** el Administrador técnico modifica su correo,
   perfil o estado mediante una solicitud válida,
   **Then** se registra el cambio y sus sesiones anteriores dejan de autorizar nuevas acciones.
4. **Given** una cuenta inactiva, **When** se intenta ingresar o usar una sesión anterior,
   **Then** se rechaza el acceso; al reactivarse debe iniciar una nueva sesión.
5. **Given** una cuenta que necesita recuperar acceso, **When** el Administrador técnico
   restablece su contraseña, **Then** no obtiene la anterior, se invalidan las sesiones
   previas y la nueva credencial exige renovación por su titular.
6. **Given** el único Administrador técnico activo, **When** se intenta desactivarlo o
   convertirlo en Operador, **Then** se rechaza el cambio y se explica que debe conservarse
   al menos una cuenta administrativa activa.
7. **Given** dos administradores activos que intentan retirar simultáneamente sus permisos,
   **When** se evalúan los cambios, **Then** no puede alcanzarse un estado sin administradores
   activos, incluso si las solicitudes se superponen.
8. **Given** cualquiera de los dos perfiles y su contraseña actual válida,
   **When** cambia su propia contraseña, **Then** solo modifica su credencial, se invalidan
   las sesiones anteriores y no puede cambiar su perfil mediante esa función.

---

### User Story 4 - Administrar el sistema con trazabilidad (Priority: P2)

Como Administrador técnico, quiero acceder a las configuraciones existentes y a las
operaciones de mantenimiento autorizadas para gestionar el sistema conservando sus reglas.

**Why this priority**: La administración del sistema complementa la gestión de usuarios
y no debe eliminar la validación de las funciones anteriores.

**Independent Test**: Usar una sesión administrativa para consultar datos, generar PDF y
cambiar una configuración y una boleta válidas; revisar validaciones y registro de cambios.

**Acceptance Scenarios**:

1. **Given** una sesión de Administrador técnico, **When** realiza cualquiera de las consultas
   o generaciones PDF permitidas al Operador, **Then** conserva esos mismos permisos.
2. **Given** una configuración existente del sistema, **When** la consulta o modifica con
   valores válidos, **Then** puede administrarla y el cambio conserva las validaciones
   y versiones exigidas por la especificación correspondiente.
3. **Given** una sesión administrativa, **When** registra o revisa una boleta, configura una
   vigencia BT4.3 o ejecuta un recálculo explícito de la spec-004,
   **Then** se permite la operación con sus reglas y trazabilidad originales.
4. **Given** un valor que incumple una regla del sistema, por ejemplo una separación de
   recepción inferior a 15 minutos o conservación inferior a 12 meses,
   **When** el Administrador técnico intenta guardarlo,
   **Then** se rechaza y se conserva la última configuración válida.
5. **Given** un cambio administrativo permitido o una solicitud administrativa denegada,
   **When** se revisa su historial, **Then** se identifican actor, fecha, acción, destino
   y resultado, sin contraseñas ni secretos de sesión; si la solicitud no tenía sesión,
   se registra como no autenticada sin atribuirle una identidad declarada por el solicitante.
6. **Given** una cuenta cuyo perfil, estado o credenciales cambian durante su uso,
   **When** intenta la siguiente acción protegida,
   **Then** no mantiene permisos de una sesión anterior y debe autenticarse de nuevo.
7. **Given** una publicación SFTP con identidad técnica válida conforme a la spec-003 y
   ninguna sesión humana abierta, **When** se recibe, **Then** se verifica mediante su
   contrato de integración y no se exige el ingreso web de un Operador o Administrador técnico.

### Edge Cases

- Una cuenta tiene exactamente un perfil de los dos definidos; perfiles vacíos o desconocidos
  no conceden acceso por defecto.
- Los datos necesarios para interpretar costos, como precios usados y vigencias, son
  referencias de consulta de la spec-004; verlos no habilita el panel de configuración.
- Generar un PDF y seleccionar filtros son operaciones de consulta; crear o revisar boletas,
  guardar tarifas o configuraciones y generar revisiones de negocio son operaciones de modificación.
- Una contraseña propia es información personal de acceso: renovarla no concede permisos
  sobre otras cuentas ni configuraciones.
- Una cuenta desactivada conserva su identidad para las referencias históricas y no equivale
  a eliminar a la persona de los registros de cambios.
- Las sesiones abiertas en distintas pestañas o dispositivos pierden autorización después
  de cambios de perfil, correo, estado o contraseña; ocultar un menú no es la protección suficiente.
- Dos solicitudes simultáneas no pueden eliminar al último Administrador técnico activo.
- El primer administrador debe existir antes de habilitar el acceso normal; no hay registro
  público que permita elegir el perfil administrativo.
- Las credenciales de integración SFTP de la spec-003 son distintas de las cuentas humanas
  de esta funcionalidad y no se sustituyen por el ingreso web.
- Un reporte ya descargado mantiene el comportamiento sin conexión de la spec-005; la
  autorización se verifica sobre nuevas consultas y entregas realizadas por la plataforma.

## Requirements *(mandatory)*

### Functional Requirements

La matriz de permisos es fija y el Administrador técnico incluye las consultas del Operador.

La matriz describe el acceso normal. Una sesión pendiente de renovación de contraseña
solo permite las acciones restringidas de FR-015 hasta completar ese proceso.

| Acción | Sin sesión válida | Operador | Administrador técnico |
| --- | --- | --- | --- |
| Iniciar sesión con cuenta activa | Permitido | Permitido | Permitido |
| Consultar consumos, gráficos, tablas e historial | Denegado | Permitido | Permitido |
| Consultar costos, boletas y referencias de cálculo | Denegado | Permitido | Permitido |
| Elegir filtros y generar o descargar PDF | Denegado | Permitido | Permitido |
| Consultar o modificar administración de usuarios | Denegado | Denegado | Permitido |
| Consultar o modificar configuración del sistema | Denegado | Denegado | Permitido |
| Registrar o revisar boletas y tarifas; recálculo con revisión | Denegado | Denegado | Permitido |
| Consultar historial de administración | Denegado | Denegado | Permitido |
| Cambiar contraseña propia o cerrar sesión | Denegado | Permitido | Permitido |

- **FR-001**: ECS-EC DEBE admitir exactamente los perfiles Operador y Administrador técnico.
  Cada cuenta DEBE tener un único perfil válido y un estado activo o inactivo; la ausencia
  de un perfil reconocido NO DEBE conceder permisos.
- **FR-002**: Ambos perfiles DEBEN iniciar sesión con correo y contraseña. Solo una cuenta
  activa con credenciales válidas DEBE obtener acceso normal según su perfil vigente.
- **FR-003**: Los correos DEBEN validarse y ser únicos entre cuentas activas e inactivas,
  ignorando mayúsculas y espacios exteriores al comprobar identidad y duplicados. Las
  contraseñas DEBEN conservar sus caracteres, espacios y distinción de mayúsculas.
- **FR-004**: La autenticación fallida DEBE usar un mensaje general equivalente para correo
  desconocido, contraseña incorrecta y cuenta inactiva, sin revelar la existencia o estado
  de la cuenta. Los intentos repetidos DEBEN seguir la espera temporal definida en Assumptions.
- **FR-005**: Toda consulta, descarga u operación protegida DEBE verificar en el servidor
  la sesión válida, estado y permisos vigentes. Una navegación oculta, un acceso directo
  o un perfil declarado por la persona NO DEBEN sustituir esa verificación. Las acciones
  que no estén autorizadas por la matriz DEBEN denegarse por defecto.
- **FR-006**: Sin sesión válida DEBE denegarse el acceso a datos y funciones protegidas,
  incluidos archivos de reportes entregados desde la plataforma. Una operación no autorizada
  NO DEBE revelar datos administrativos ni producir cambios de negocio.
- **FR-007**: El Operador DEBE consultar las funciones de lectura de las specs-001, 002, 004
  y 005, incluidos datos, costos, boletas, filtros y generación o descarga de PDF. Estas
  operaciones NO DEBEN modificar mediciones, tarifas, boletas ni configuraciones.
- **FR-008**: El Operador NO DEBE acceder, ni para lectura ni modificación, a la administración
  de cuentas o configuración del sistema. Tampoco DEBE registrar o revisar boletas,
  guardar tarifas ni ejecutar acciones explícitas que creen revisiones de negocio.
- **FR-009**: El Administrador técnico DEBE disponer de todas las consultas y funciones PDF
  del Operador y acceso exclusivo a la administración de usuarios y del sistema, según
  la matriz, sin habilitar funciones de modificación ajenas a las ya especificadas.
- **FR-010**: La navegación DEBE mostrar las funciones permitidas al perfil y excluir las
  administrativas para el Operador, manteniendo la comprobación de permisos para accesos directos.
- **FR-011**: El Administrador técnico DEBE poder listar cuentas y registrar nuevas con
  correo, perfil, estado y contraseña inicial, además de actualizar correo, perfil y estado
  de cuentas existentes. El registro público de cuentas o autoasignación de perfil NO DEBE habilitarse.
- **FR-012**: La gestión normal de cuentas DEBE utilizar desactivación y reactivación,
  conservando la identidad y referencias históricas. Una cuenta inactiva NO DEBE iniciar
  ni conservar sesiones autorizadas; reactivarla NO DEBE restaurar sesiones anteriores.
- **FR-013**: Antes del acceso normal DEBE establecerse un Administrador técnico inicial
  mediante una preparación controlada. El sistema DEBE impedir desactivar o degradar al
  último administrador activo, incluso ante solicitudes concurrentes.
- **FR-014**: Ambos perfiles DEBEN poder renovar su propia contraseña validando la actual,
  sin cambiar perfil ni otras cuentas. El Administrador técnico DEBE poder restablecer
  contraseñas de otras cuentas sin conocer o recuperar las anteriores.
- **FR-015**: Las contraseñas iniciales o restablecidas DEBEN exigir renovación por el titular
  antes del acceso normal. Durante ese ingreso restringido solo DEBEN permitirse la
  renovación propia y el cierre de sesión. Las nuevas contraseñas DEBEN cumplir los
  límites definidos en Assumptions, sin truncarse silenciosamente.
- **FR-016**: El cierre DEBE invalidar la sesión utilizada. Las sesiones DEBEN vencer según
  los límites de inactividad y duración definidos en Assumptions. Después del cierre o
  vencimiento DEBE exigirse una nueva autenticación para cualquier acción protegida.
- **FR-017**: Un cambio efectivo de correo, perfil, estado o contraseña DEBE invalidar todas
  las sesiones previas de la cuenta afectada antes de su siguiente acción protegida.
  Si la cuenta continúa activa, DEBE volver a ingresar con sus credenciales y perfil vigentes.
- **FR-018**: Las contraseñas NO DEBEN persistirse en forma recuperable ni exponerse en
  listados, consultas, reportes o historial, incluso al Administrador técnico. Tampoco
  DEBEN exponerse secretos de sesión o credenciales de integración.
- **FR-019**: La administración del sistema DEBE abarcar las configuraciones y modificaciones
  existentes de las specs anteriores, incluidos parámetros de recepción e historial,
  referencias del suministro, correspondencias y perfiles BT4.3. DEBE mantener todas
  sus validaciones; el perfil administrativo NO DEBE permitir saltarlas.
- **FR-020**: Registrar o revisar boletas y ejecutar recálculos explícitos con nueva revisión
  de la spec-004 DEBE reservarse al Administrador técnico. La consulta del Operador DEBE
  conservar visibles las cantidades y referencias de negocio necesarias para interpretarlos,
  sin revelar secciones o secretos administrativos.
- **FR-021**: Las modificaciones administrativas y las solicitudes administrativas
  denegadas DEBEN dejar registro de fecha, acción, destino, resultado y actor autenticado
  cuando exista; de otro modo DEBE constar la condición no autenticada sin confiar en una
  identidad declarada. El Administrador técnico DEBE poder consultar ese historial,
  que NO DEBE permitir modificar o eliminar eventos desde sus funciones de consulta.
  Las contraseñas y secretos NO DEBEN formar parte de los registros.
- **FR-022**: Los fallos de autorización o validación DEBEN informarse conservando el último
  estado válido y sin cambios parciales de la operación rechazada. Las modificaciones
  permitidas DEBEN conservar el autor y las versiones exigidas por las specs anteriores.
- **FR-023**: Los permisos humanos DEBEN aplicarse a las funciones web del monolito. Las
  identidades de integración SFTP y el programa externo de simulación DEBEN conservar su
  contrato de acceso propio; tener un perfil web NO DEBE conceder automáticamente acceso SFTP
  ni requerirse una sesión humana para cada envío automatizado ya autorizado.

- **FR-024**: En el despliegue accesible por internet, el ingreso, las sesiones y las
  funciones web protegidas DEBEN utilizar HTTPS. Las credenciales y los secretos de sesión
  DEBEN transmitirse únicamente por conexiones protegidas; una conexión sin esa protección
  NO DEBE permitir autenticarse ni entregar datos protegidos. La dirección pública de la
  aplicación DEBE conservar todas las verificaciones de identidad y permisos de esta spec.

### Key Entities *(include if feature involves data)*

- **Cuenta de usuario**: Identidad estable con correo único, perfil, estado y condición de
  renovación de contraseña; permanece referenciable tras su desactivación.
- **Perfil y permiso**: Uno de los dos perfiles fijos y el conjunto de acciones de consulta
  o administración que puede ejecutar sobre las funciones existentes.
- **Sesión de acceso**: Autenticación de una cuenta con inicio, actividad, vencimiento y
  validez condicionada al estado y permisos actuales.
- **Credencial personal**: Contraseña inicial, restablecida o renovada que permite comprobar
  el acceso sin convertirse en información consultable por otros usuarios.
- **Cambio administrativo**: Operación sobre cuentas, configuraciones o datos mantenidos,
  con actor, destino, fecha, resultado y referencias a revisiones aplicables.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100 % de los casos de referencia, las cuentas activas de ambos perfiles
  ingresan con sus credenciales válidas y las credenciales inválidas o cuentas inactivas
  no obtienen acceso normal.
- **SC-002**: El 100 % de las combinaciones de la matriz produce el resultado esperado,
  incluidos accesos directos y declaraciones de perfil manipuladas; ningún caso denegado
  revela información administrativa ni modifica el estado de negocio.
- **SC-003**: Todas las consultas y generaciones PDF disponibles al Operador también están
  disponibles al Administrador técnico; ninguna requiere conceder al Operador un permiso de modificación.
- **SC-004**: Tras cerrar sesión, vencer sus límites o cambiar correo, perfil, estado o
  contraseña, ninguna sesión que deba invalidarse permite su siguiente acción protegida.
- **SC-005**: En todos los escenarios de alta, edición, desactivación y restablecimiento,
  se conserva la unicidad de correo y al menos un administrador activo, incluidos cambios
  concurrentes, sin revelar contraseñas ni perder referencias históricas.
- **SC-006**: El 100 % de los cambios administrativos y solicitudes administrativas denegadas
  de referencia identifica su actor autenticado o condición no autenticada, destino y resultado
  en el historial permitido.
- **SC-007**: En al menos 9 de 10 tareas con personas representativas, se inicia sesión y
  se alcanza la vista de datos asignada al perfil sin ayuda en un máximo de un minuto.

- **SC-008**: Durante la validación del despliegue en VPS, el 100 % de los casos de ingreso
  y solicitudes web protegidas de referencia utiliza HTTPS; los intentos sin sesión o
  sin protección de transporte no reciben información protegida ni obtienen una sesión válida.

## Assumptions

- **Entornos y acceso por internet**: Se aplican el desarrollo local y el despliegue final
  en VPS definidos en la spec-001. Las cuentas de prueba y configuraciones locales permiten
  verificar los mismos controles de identidad, permisos y sesión sin servicios remotos.
  En producción se accede por la dirección pública de la aplicación mediante HTTPS;
  disponer de esa dirección no concede acceso anónimo ni registro público de cuentas.
  La preparación del acceso cifrado se concretará en el plan junto con el stack pendiente.
- **Modelo de cuentas**: Existe un edificio y dos perfiles humanos fijos. No se definen
  perfiles personalizados, combinaciones de roles, registro público ni permisos editables
  por cuenta. Una persona sin sesión no constituye un tercer perfil.
- **Lectura confirmada**: La persona solicitante confirmó la generación y descarga de PDF
  por el Operador. Filtros, consultas y reportes no son mantenimiento de datos de negocio.
  La emisión puede registrar metadatos del reporte sin autorizar modificaciones de las fuentes.
- **Mantenimiento de datos**: Las personas responsables de costos y configuración de las
  specs anteriores actúan como Administrador técnico al guardar tarifas, boletas o revisiones.
  El Operador consulta esos resultados. No se añaden edición arbitraria de mediciones,
  eliminación masiva de datos ni funciones remotas para ejecutar el simulador.
- **Contraseñas**: Las nuevas contraseñas admiten entre 15 y 128 caracteres, incluidos espacios,
  sin exigir clases específicas de caracteres. No se recortan ni cambian mayúsculas.
  La contraseña inicial se establece al crear la cuenta; su entrega al titular se realiza
  por el procedimiento operativo de alta, sin implementar correo automático en esta función.
- **Sesiones e intentos**: Los valores iniciales son 30 minutos de inactividad y ocho horas
  de duración máxima desde el ingreso. Para el mismo correo y origen, cinco intentos
  fallidos dentro de 15 minutos activan una espera de 15 minutos desde alcanzar el umbral.
  Los correos desconocidos reciben el mismo tratamiento observable; no se impone un bloqueo
  permanente de cuenta por estos intentos.
- **Administración inicial y recuperación**: La preparación del primer administrador debe
  quedar documentada antes de habilitar el uso normal, sin una contraseña pública compartida.
  El restablecimiento cotidiano lo realiza otro Administrador técnico; la recuperación
  operativa del único administrador sin credenciales pertenece al procedimiento de operación.
- **Credenciales de integración**: La autenticación SFTP mantiene el alcance de la spec-003.
  La distinción de identidades técnicas no añade un tercer perfil humano ni concede al
  Operador acceso a configuraciones de recepción.
- **Alcance de lectura de referencias**: Los precios aplicados, versiones, unidades y calidad
  visibles en cálculos y reportes son datos de consulta. La configuración completa y los
  secretos permanecen reservados según la matriz y las restricciones de exposición.
- **Dependencias y gobierno**: Esta especificación concreta los actores de las specs-001 a 005
  y amplía su alcance previo sobre cuentas. El plan debe aplicar la matriz a cada función
  protegida, invalidación de sesiones, preparación inicial y trazabilidad, conservando
  arquitectura monolítica y documentación integral. No se prescriben bibliotecas o mecanismos
  concretos de almacenamiento de sesión.
- **Límites de la función**: No se incluyen ingreso federado, autenticación multifactor,
  recuperación automática por correo ni cambios a la política de conservación o las reglas
  de recepción, cálculo y reporte de las funcionalidades anteriores.
