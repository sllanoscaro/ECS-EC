# Feature Specification: Notificaciones programables y alertas por correo

**Feature Branch**: No creada; no hay un hook de creación de rama configurado.

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "ECS-EC debe contener un apartado de notificaciones programables,
con alertas propias del sistema o configurables según el consumo. Solo el Administrador
técnico configura las notificaciones dentro de la plataforma. Pueden enviarse periódicamente
por correo, por ejemplo trazabilidad diaria a las 06:00 al Administrador técnico, y las
urgentes pueden enviarse de inmediato a los usuarios configurados."

**Clarificación recibida**: El correo de trazabilidad contiene un resumen funcional de
recepción, calidad de datos y cambios administrativos; no incluye logs ni trazas técnicas
de la spec-007.

**Especificaciones relacionadas**:
[spec-001: consumos y calidad](../001-visualizar-consumo-categorias/spec.md),
[spec-002: recepción e historial](../002-registro-retencion-consumo/spec.md),
[spec-003: datos de prueba](../003-simulador-pas600-sftp/spec.md),
[spec-004: información de costos](../004-costos-tarifa-bt43/spec.md),
[spec-005: reportes](../005-generar-reportes-pdf/spec.md),
[spec-006: permisos funcionales](../006-acceso-usuarios-rbac/spec.md) y
[spec-007: observabilidad externa](../007-observabilidad-externa/spec.md).

## Clarifications

### Session 2026-11-01

- Q: ¿Dónde se implementan los productores reales de costos y PDF y sus eventos de fallo? → A: En sus propias funcionalidades, specs 004 y 005, con planes y tareas explícitos para cálculo/generación reales, resultados persistidos y eventos funcionales de fallo; la integración de notificaciones solo conecta esos eventos.
- Q: ¿Qué perfil reproducible acredita el plazo de 60 segundos? → A: 10 destinatarios elegibles; dos reglas periódicas y dos urgentes coincidentes dirigidas a todos; 40 entregas iniciales, cola vacía, cuatro plazas y aceptación del transporte de prueba en <=1 s; todos los primeros intentos en <=60 s desde programación o detección válida.
- Q: ¿Cuándo debe estar disponible la coordinación entre envíos y cambios de identidad o regla? → A: Desde las fundaciones de identidad y antes del primer despacho periódico; la historia de revisión de entregas conserva las funciones administrativas de historial y reenvío.
- Q: ¿Cómo se aplica una actualización de reglas de zona horaria al iniciar una versión nueva? → A: Reconciliación automática antes de habilitar el planificador: comparar versiones, recalcular solo futuros no materializados, conservar ocurrencias existentes e invalidar previsualizaciones afectadas.
- Q: ¿Cómo se informa la cobertura de recepción, calidad y cambios administrativos? → A: Por contenido: completa con historial íntegro de toda la ventana; incompleta con intervalos faltantes conocidos; desconocida si no puede determinarse integridad o consultarse la fuente. Se conservan conteos conocidos y un desconocido no se convierte en cero.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurar notificaciones como Administrador técnico (Priority: P1)

Como Administrador técnico, quiero definir el contenido, los destinatarios y cuándo se
envían las notificaciones para comunicar información relevante del edificio.

**Why this priority**: La programación y las reglas deben quedar bajo el control exclusivo
del perfil que administra el sistema.

**Independent Test**: Usar cuentas de los tres roles, configurar una notificación válida
y probar acceso directo, validaciones, cambios y pausa de la configuración.

**Acceptance Scenarios**:

1. **Given** una sesión de Administrador técnico,
   **When** crea una notificación con contenido permitido, destinatarios activos y modalidad válida,
   **Then** puede guardarla, revisar su programación o condición y activarla.
2. **Given** una sesión de Operador, una identidad Programador o una persona sin autorización,
   **When** intenta crear, modificar, activar, pausar o reenviar notificaciones mediante
   navegación o solicitud directa, **Then** se deniega sin modificar la configuración.
3. **Given** una regla de consumo,
   **When** se elige categoría, ventana, comparación, umbral y destinatarios,
   **Then** quedan identificados la energía en kWh, los criterios de evaluación y la modalidad.
4. **Given** una configuración sin destinatarios, con direcciones no registradas, umbral
   inválido o programación incompleta, **When** se intenta activar,
   **Then** se indican los datos que deben corregirse y no se habilitan envíos.
5. **Given** un resumen que incluye cambios administrativos de la spec-006,
   **When** se selecciona un Operador como destinatario,
   **Then** se impide activar esa combinación porque no puede consultar ese contenido.
6. **Given** una configuración activa con mensajes aún pendientes,
   **When** se pausa o se guarda una revisión que la sustituye,
   **Then** dejan de iniciarse entregas pendientes de la versión anterior y se conserva su historial.
7. **Given** una configuración de trazabilidad diaria,
   **When** se revisa su contenido,
   **Then** contiene información funcional autorizada y no señales internas de observabilidad.

---

### User Story 2 - Recibir un correo periódico (Priority: P1)

Como usuario configurado, quiero recibir el resumen programado en mi correo registrado
para revisar novedades sin tener que ingresar continuamente a la plataforma.

**Why this priority**: Es la modalidad periódica solicitada, incluido el ejemplo de las 06:00.

**Independent Test**: Configurar un resumen diario a las 06:00 y avanzar la fecha de prueba;
verificar destinatarios, ventana informada y una sola ocurrencia programada.

**Acceptance Scenarios**:

1. **Given** una notificación diaria a las 06:00 para un Administrador técnico,
   **When** llega esa hora en la zona configurada,
   **Then** se genera una ocurrencia con su resumen funcional y se inicia el envío dentro
   del plazo definido, aunque ninguna persona tenga una sesión abierta.
2. **Given** una programación periódica,
   **When** se genera su resumen,
   **Then** identifica la ventana entre la ocurrencia programada anterior y la actual,
   el corte y la diferencia entre fechas de recepción, cambios y mediciones cuando corresponda.
3. **Given** una ventana sin novedades pero con información disponible,
   **When** llega la programación,
   **Then** se envía el resumen indicando ausencia de novedades; no se afirma consumo cero
   por no haberse recibido nuevas mediciones.
4. **Given** un horario inexistente o repetido por cambio de hora, o un día mensual que no existe,
   **When** se calcula la ocurrencia,
   **Then** se aplica la política calendario documentada y se genera una sola ocurrencia lógica.
5. **Given** varios destinatarios válidos,
   **When** se envía el resumen,
   **Then** cada uno tiene su entrega y estado independientes, sin exponer a los otros destinatarios.
6. **Given** una nueva activación o cambio de programación,
   **When** se calcula su próxima ocurrencia,
   **Then** se informa la siguiente fecha admisible y no se reproducen todas las fechas anteriores.
7. **Given** un resumen programado y un transporte de correo de prueba local,
   **When** se ejecuta el escenario a su hora prevista,
   **Then** se verifican destinatario, contenido, primer intento y resultado del transporte
   sin un servicio remoto; el historial identifica la prueba sin afirmar entrega a un
   buzón externo y mantiene las mismas reglas de autorización y reintentos.
8. **Given** el despliegue final en VPS y una notificación con referencias a ECS-EC,
   **When** su destinatario abre una referencia desde una red externa,
   **Then** se dirige a la dirección pública de la aplicación y debe autenticarse con
   sus permisos vigentes; no se utiliza la dirección local del equipo de desarrollo.

---

### User Story 3 - Recibir alertas urgentes de consumo o del sistema (Priority: P1)

Como usuario configurado, quiero recibir una alerta cuando se detecte una condición
urgente para conocerla sin esperar el próximo resumen periódico.

**Why this priority**: La urgencia debe depender de una detección válida y no del horario del resumen.

**Independent Test**: Preparar consumos conocidos, datos incompletos y eventos funcionales;
comprobar activación, tiempo de primer intento, supresión de repeticiones y normalización.

**Acceptance Scenarios**:

1. **Given** una regla activa de energía mayor que 100 kWh y una ventana completa válida
   con 101 kWh, **When** se detecta su cumplimiento,
   **Then** se registra la alerta y se inicia el primer intento urgente dentro de 60 segundos
   con los servicios operativos, sin esperar el horario periódico.
2. **Given** un umbral estrictamente mayor que 100 kWh y una ventana de 100 kWh,
   **When** se evalúa, **Then** no se activa; con comparación mayor o igual sí se activa.
3. **Given** un episodio urgente ya detectado,
   **When** nuevas evaluaciones mantienen la misma condición,
   **Then** no se genera un correo por cada reevaluación; una normalización comprobada y
   posterior activación pueden producir un nuevo episodio.
4. **Given** una ventana incompleta o sin datos, incluido un total calculado al que le
   falta la lectura de alguna categoría de su base,
   **When** se evalúa una regla de consumo,
   **Then** se registra información insuficiente y no se interpreta el vacío como cero ni
   como normalización de un episodio abierto.
5. **Given** una regla funcional de ausencia de datos con plazo explícito,
   **When** se supera ese plazo sin nuevas actualizaciones válidas,
   **Then** se genera el evento correspondiente; el mínimo de 15 minutos entre recepciones
   no se usa por sí solo como una obligación de recibir datos cada 15 minutos.
6. **Given** una publicación con datos inválidos o un fallo funcional al generar un PDF,
   **When** corresponde a un tipo de alerta del sistema habilitado,
   **Then** puede notificarse su resultado funcional sin adjuntar logs, trazas o secretos.
7. **Given** un lote histórico con múltiples ventanas anteriores,
   **When** se incorpora,
   **Then** no se envía una alerta por cada ventana del archivo; se evalúa solo la más
   reciente admisible y se identifica su período real y cualquier retraso.
8. **Given** un mismo evento o una recepción reintentada ya reconocida,
   **When** vuelve a procesarse,
   **Then** no genera otra ocurrencia urgente para el mismo episodio.
9. **Given** una instalación sin medidor total con CAT-03 y CAT-05 presentes, un total
   calculado válido de 20 kWh y un umbral de CAT-01 mayor que 15 kWh,
   **When** se evalúa por primera vez esa ventana completa,
   **Then** se abre un único episodio cuya evidencia y notificación identifican el total
   calculado, su base CAT-03 y CAT-05 y su alcance, sin volver a sumar esas contribuciones.
10. **Given** una categoría parcial configurada sin medidor,
    **When** se evalúa una regla de ausencia de datos sobre ella,
    **Then** no se abre un episodio por no recibir lecturas de esa categoría ni se le
    atribuye consumo cero.

---

### User Story 4 - Revisar entregas y manejar fallos (Priority: P2)

Como Administrador técnico, quiero conocer el resultado de las notificaciones y sus
intentos para corregir problemas de envío sin duplicar mensajes ni perder trazabilidad.

**Why this priority**: La generación de una notificación y su aceptación por el correo
son hechos distintos y pueden fallar de forma independiente.

**Independent Test**: Simular aceptación, rechazo temporal, pérdida de confirmación,
reinicio del sistema y cambios de permisos de destinatarios antes de enviar.

**Acceptance Scenarios**:

1. **Given** una entrega aceptada por el servicio de correo,
   **When** se consulta su historial,
   **Then** figura como aceptada por ese servicio, sin afirmar lectura o recepción en la
   bandeja del usuario sin evidencia adicional.
2. **Given** un fallo transitorio que confirma que no se aceptó el mensaje,
   **When** se reintenta,
   **Then** se mantiene la identidad de la entrega y se respetan el número máximo y esperas definidos.
3. **Given** una interrupción o reinicio durante un intento que deja incierto si el correo fue aceptado,
   **When** se registra el resultado,
   **Then** se marca indeterminado y no se reenvía automáticamente; el Administrador técnico
   puede decidir un reenvío explícito dejando constancia de la posible repetición.
4. **Given** una cuenta desactivada, con permisos retirados o fuera de los destinatarios vigentes,
   **When** se prepara su siguiente intento,
   **Then** se cancela esa entrega sin impedir las de los demás destinatarios autorizados.
5. **Given** un reinicio tras varias ocurrencias periódicas vigentes y nunca intentadas,
   **When** se recupera la programación,
   **Then** se consolidan en un único resumen de recuperación por regla y destinatario,
   identificando los períodos omitidos, sin repetir entregas ya aceptadas o indeterminadas.
6. **Given** una sesión de Operador,
   **When** consulta el apartado de notificaciones,
   **Then** solo ve contenido e historial dirigidos a su cuenta, sin configurar reglas,
   consultar otros destinatarios ni ejecutar reenvíos.
7. **Given** el servicio de correo indisponible,
   **When** ECS-EC recibe mediciones o procesa consultas, costos y PDF,
   **Then** esas operaciones siguen sus reglas; el fallo de envío queda visible y no
   origina una cadena ilimitada de correos sobre el propio fallo.
8. **Given** una modificación administrativa o un intento de envío,
   **When** se inspecciona su referencia durante el plazo de conservación,
   **Then** se identifican versión de regla, origen, destinatario, fechas y resultado,
   manteniendo los contenidos técnicos sensibles fuera del historial y de la telemetría.
9. **Given** una cuenta destinataria activa cuyo correo se cambia antes de su primer intento,
   **When** se prepara una entrega todavía autorizada, **Then** se utiliza el correo vigente
   y no la dirección anterior, manteniendo identificable el destinatario efectivo del intento.

### Edge Cases

- Una regla nueva se guarda desactivada hasta que el Administrador técnico la activa
  con destinatarios, contenido y programación o condición válidos.
- Cada categoría conserva su significado; un umbral de consumo total usa la serie CAT-01,
  medida o calculada conforme a la spec-001, sin volver a sumar las categorías parciales.
  Cuando sea calculada, la evidencia identifica su base y alcance.
- Una categoría parcial sin medidor no tiene una frecuencia esperada de lecturas: no debe generar
  alertas de ausencia de datos por ese motivo ni evaluarse como consumo cero.
- La ventana de datos de consumo y el instante de recepción o detección son distintos;
  la urgencia comienza al detectar la condición, no antes de disponer de evidencia.
- Un dato incompleto no confirma normalidad. La falta de lecturas no debe crear un
  consumo cero ni rearmar una alerta de bajo consumo.
- Una corrección histórica no debe reproducir automáticamente toda una secuencia de urgencias.
- Pausar una regla o desactivar una cuenta no retira correos que el servicio ya aceptó;
  sí impide iniciar nuevas entregas que dejaron de estar autorizadas.
- Un cambio de correo se resuelve desde la cuenta vigente antes del envío; no se sigue
  enviando a una dirección anterior conservada en una entrega pendiente.
- Una condición puede aparecer en un resumen periódico aunque ya haya producido una
  alerta urgente; son comunicaciones con propósito y referencia distintos.
- Sin datos suficientes se informa esa limitación por contenido. «Sin novedades» requiere
  cobertura completa y conteo cero en todos los contenidos seleccionados; una fuente
  desconocida o una ventana con huecos conserva los resultados conocidos y no se presenta
  como cero eventos.
- Una entrega con resultado indeterminado no equivale a un rechazo confirmado y no
  permite prometer una única copia en una bandeja externa.
- La separación mínima de 15 minutos de recepción no limita envíos urgentes, ejecución
  de horarios ni reintentos de correo.
- Programador mantiene únicamente el alcance técnico de la spec-007 y no recibe acceso
  funcional por ser configurado como destinatario.

## Requirements *(mandatory)*

### Functional Requirements

La autorización funcional se amplía con estas acciones:

| Acción | Operador | Administrador técnico | Programador o sin autorización funcional |
| --- | --- | --- | --- |
| Consultar notificaciones dirigidas a la propia cuenta | Permitido | Permitido | Denegado |
| Consultar todas las reglas, destinatarios e historial funcional | Denegado | Permitido | Denegado |
| Crear, editar, activar, pausar y revisar reglas | Denegado | Permitido | Denegado |
| Configurar horarios, condiciones, contenidos y destinatarios | Denegado | Permitido | Denegado |
| Ejecutar un reenvío explícito autorizado | Denegado | Permitido | Denegado |

- **FR-001**: ECS-EC DEBE ofrecer un apartado funcional de notificaciones con envío por
  correo en modalidad periódica y urgente. La configuración y los reenvíos manuales DEBEN
  reservarse al Administrador técnico, con verificación de permisos en cada solicitud.
- **FR-002**: El Administrador técnico DEBE poder crear, consultar, editar, activar y pausar
  reglas, definiendo nombre, contenido funcional, modalidad, destinatarios y horario o
  condición. Los cambios DEBEN generar versiones y las reglas nuevas DEBEN iniciar desactivadas.
- **FR-003**: El catálogo inicial DEBE incluir recepción o procesamiento con rechazos,
  ausencia de datos con plazo configurado, fallos funcionales de cálculo o generación PDF
  y resúmenes de recepción, calidad y cambios administrativos. Los cambios administrativos
  solo DEBEN incluirse para destinatarios con permiso de consultar la auditoría de la spec-006.
  El cálculo real y sus resultados persistidos pertenecen a la spec-004; la generación real
  de PDF y sus resultados persistidos pertenecen a la spec-005. Sus propios planes y tareas
  DEBEN entregar también los eventos funcionales de fallo. Esta funcionalidad consume esos
  eventos; su integración no sustituye la construcción de los productores reales.
- **FR-004**: Las reglas configurables de consumo DEBEN indicar una categoría de las siete
  existentes, energía en kWh, ventana de intervalo, hora, día, mes o año, comparación mayor,
  mayor o igual, menor o menor o igual y umbral finito no negativo. CAT-01 DEBE utilizar
  su origen medido o calculado conforme a la spec-001, sin otra suma propia de la regla;
  las evidencias y notificaciones de un total calculado DEBEN identificar su base y alcance.
- **FR-005**: Los destinatarios DEBEN seleccionarse entre cuentas funcionales registradas
  y activas de la spec-006, usando su identidad y correo vigente. Se DEBE exigir al menos
  uno y comprobar que todos puedan consultar el contenido antes de activar una regla.
  NO DEBEN aceptarse direcciones externas arbitrarias ni credenciales técnicas como destinatarios.
- **FR-006**: La programación DEBE permitir intervalos de N minutos u horas y recurrencias
  diarias, semanales, mensuales o anuales, con N entero positivo, fecha de inicio, hora y
  zona horaria cuando correspondan. DEBE mostrar la próxima ocurrencia antes de activarse
  y ejecutarse sin requerir una sesión humana abierta.
- **FR-007**: Las recurrencias DEBEN respetar la zona horaria configurada. Una hora local
  inexistente DEBE trasladarse al primer instante válido posterior; una
  hora repetida DEBE usar solo su primera ocurrencia. Un día mensual o anual inexistente
  DEBE usar el último día válido del mes, conservando una sola ocurrencia lógica. Al iniciar
  una versión nueva, antes de habilitar el planificador, DEBE compararse la versión instalada
  de las reglas de zona horaria con la registrada. Si cambió, se DEBEN recalcular únicamente
  las fechas futuras todavía no materializadas, conservar las ocurrencias existentes e
  invalidar las previsualizaciones afectadas, manteniendo una sola ocurrencia lógica.
- **FR-008**: Para entregas elegibles, el primer intento periódico DEBE iniciarse dentro
  de 60 segundos de su hora programada y el urgente dentro de 60 segundos de su detección
  válida, con aplicación y servicio de correo operativos. La urgencia NO DEBE esperar al
  siguiente horario periódico ni a otra actualización de mediciones. El cumplimiento se
  acredita con el perfil reproducible de SC-003; ese perfil no constituye una garantía
  para un volumen de envíos no especificado.
- **FR-009**: Los resúmenes periódicos DEBEN identificar como ventana la comprendida entre
  la ocurrencia programada anterior y la actual, con inicio incluido y fin excluido y corte
  de datos explícito. DEBEN diferenciar recepción, cambios y períodos de medición.
  Cada contenido seleccionado —recepción, calidad o cambios administrativos— DEBE informar
  su cobertura: completa si existe historial funcional íntegro de toda la ventana; incompleta
  si se conocen intervalos faltantes, incluida conservación vencida; desconocida si no puede
  determinarse la integridad o consultarse la fuente. Los conteos conocidos se DEBEN conservar
  con su alcance; un conteo desconocido DEBE identificarse como ausente, nunca como cero.
  «Sin novedades» solo corresponde si todos los contenidos seleccionados tienen cobertura
  completa y conteo cero. Si todos están completos y existe algún suceso, el resumen indica
  información disponible. Si alguno tiene cobertura incompleta o desconocida, indica
  información insuficiente conservando los resultados conocidos y sus límites. La cobertura
  funcional no depende de la disponibilidad de logs o trazas técnicas.
- **FR-010**: Las condiciones de consumo DEBEN evaluarse solo con mediciones aceptadas
  o totales calculados válidos conforme a la spec-001 y ventanas completas con cobertura
  válida. Las categorías sin fuente configurada y los datos insuficientes DEBEN producir
  un estado no evaluable, sin generar un valor cero ni normalizar un episodio activo.
- **FR-011**: La primera evaluación válida que cumpla una condición DEBE abrir un episodio.
  Reevaluar una condición persistente NO DEBE producir otra urgencia del mismo episodio.
  Una evaluación válida que ya no cumpla DEBE permitir cerrar y rearmar el episodio.
  Para sucesos puntuales del catálogo se DEBE usar su identidad de evento para evitar repeticiones.
- **FR-012**: La ausencia de datos DEBE requerir un plazo de silencio configurado compatible
  con la frecuencia de recepción permitida, nunca inferior a 15 minutos. DEBE evaluarse
  desde la última aceptación de datos nuevos por categoría o, si no existe, desde la activación
  de la regla, también por el paso del tiempo y sin esperar otra medición. Duplicados y rechazos
  NO DEBEN reiniciar ese plazo. El mínimo entre actualizaciones
  de la spec-002 NO DEBE interpretarse como un máximo de silencio obligatorio. Las
  categorías sin fuente configurada NO DEBEN generar episodios por ausencia de lecturas.
  Para CAT-01 calculada con base no vacía, la ausencia DEBE referirse a la disponibilidad de
  totales válidos conforme a la spec-001, sin presuponer un medidor total físico.
- **FR-013**: Un lote histórico DEBE evaluar únicamente la ventana más reciente admisible
  de cada regla y no reproducir una urgencia por cada registro pasado. Se DEBEN excluir
  ventanas cerradas antes de activar la regla y ventanas superadas por la última evaluación válida;
  las correcciones de estas últimas DEBEN quedar en el historial o resumen. Toda alerta
  DEBE indicar el período real del dato y si se detectó con retraso.
- **FR-014**: Cada ocurrencia y entrega DEBE tener identidad estable por versión de regla,
  episodio o período programado y destinatario. Los reintentos o recuperaciones NO DEBEN
  crear duplicados lógicos ni repetir automáticamente entregas confirmadas como aceptadas.
- **FR-015**: Antes de cada intento DEBEN verificarse cuenta activa, destinatario vigente,
  correo actual, permisos sobre todo el contenido y vigencia de la regla. Una pérdida de
  elegibilidad DEBE cancelar solo la entrega afectada. Cada destinatario DEBE tener mensaje
  y resultado propios sin exponer las direcciones o información de los demás. La coordinación
  con cambios de cuenta, correo, permisos y regla DEBE estar disponible desde el primer
  incremento que envía correos. Si el cambio se confirma antes del inicio registrado del
  intento, DEBE impedirlo cuando lo vuelve inelegible; un intento ya iniciado conserva
  su resultado e historial. La selección del correo efectivo usa ese mismo límite.
- **FR-016**: La pausa o sustitución de una versión de regla DEBE cancelar sus entregas
  pendientes antes de nuevos intentos, sin alterar intentos ya registrados. Las nuevas
  programaciones DEBEN comenzar en su siguiente ocurrencia admisible y NO DEBEN reproducir
  automáticamente ocurrencias previas a su activación.
- **FR-017**: La programación, episodios y estados de entrega DEBEN sobrevivir a reinicios.
  Las ocurrencias periódicas vencidas, todavía autorizadas y nunca intentadas DEBEN
  consolidarse en un resumen de recuperación por regla y destinatario con sus períodos identificados.
  Entregas aceptadas, indeterminadas o ya intentadas NO DEBEN regenerarse como atrasos nuevos.
  Una entrega que estaba en intento al reiniciar DEBE verificarse; si no puede determinarse
  su aceptación o no aceptación, DEBE quedar indeterminada sin reintento automático.
- **FR-018**: La entrega DEBE distinguir pendiente, en intento, aceptada por el servicio de
  correo, fallida, cancelada e indeterminada. Aceptación por el servicio NO DEBE presentarse
  como lectura o recepción en bandeja sin evidencia adicional.
- **FR-019**: Un fallo transitorio con no aceptación confirmada DEBE admitir hasta tres
  intentos totales por entrega, con esperas iniciales de un minuto y cinco minutos para
  el segundo y tercero. Fallos definitivos o de configuración DEBEN detener los intentos
  automáticos y conservar la causa funcional visible para administración.
- **FR-020**: Un resultado incierto sobre aceptación DEBE marcarse indeterminado y NO DEBE
  reenviarse automáticamente. Solo el Administrador técnico DEBE poder autorizar un reenvío
  explícito vinculado al anterior, con la advertencia de posible repetición y registro de la decisión.
- **FR-021**: El contenido DEBE identificar edificio, tipo, prioridad, regla y versión,
  suceso o condición, período o fechas relevantes, corte y datos funcionales necesarios,
  con unidades y estados de calidad. Los enlaces a ECS-EC DEBEN exigir sus permisos normales;
  el correo NO DEBE crear accesos públicos a vistas o PDF protegidos.
- **FR-022**: La trazabilidad enviada DEBE limitarse a información funcional autorizada.
  NO DEBE incluir logs, métricas o trazas internas de la spec-007, contraseñas, claves,
  secretos de sesión, cuerpos de archivos de recepción ni detalles técnicos de excepción.
  La telemetría de envío DEBE cumplir también la protección de contenidos de la spec-007.
- **FR-023**: El Operador DEBE poder consultar exclusivamente sus notificaciones e historial
  de entrega sin administrar reglas, destinatarios o reenvíos. El Administrador técnico
  DEBE poder consultar el historial funcional completo y sus filtros por período, regla,
  destinatario y estado. Programador NO DEBE obtener acceso funcional por su rol técnico.
- **FR-024**: Configuraciones, episodios, entregas e intentos DEBEN conservar autor o proceso
  de origen, versiones, destinatario, fechas y resultados durante al menos 12 meses calendario
  desde su registro o revisión, con las reglas temporales de la spec-002. Las revisiones y
  reenvíos NO DEBEN borrar el registro anterior.
- **FR-025**: Un fallo de correo NO DEBE bloquear recepción, consultas, costos o PDF ni
  alterar sus datos. Los fallos de envío DEBEN mostrarse en el historial sin iniciar una
  cadena recursiva ilimitada de alertas por el mismo canal fallido. La lógica de reglas
  y programación DEBE mantenerse en el monolito; el servicio de correo se concreta en el plan.

- **FR-026**: El desarrollo local DEBE permitir verificar programación, condiciones,
  destinatarios, contenido y resultados de envío mediante un componente o sustituto de
  correo local, sin requerir un servicio remoto ni la futura VPS. El uso del transporte
  de prueba DEBE quedar identificado y conservar las reglas de permisos, reintentos y
  estados. Las referencias a ECS-EC DEBEN usar la dirección configurada para su entorno;
  en producción DEBEN dirigir a la aplicación de la VPS y mantener el acceso protegido.

### Key Entities *(include if feature involves data)*

- **Regla de notificación**: Contenido funcional, modalidad, programación o condición,
  destinatarios, vigencia, estado y versiones administradas por el Administrador técnico.
- **Programación y ocurrencia**: Recurrencia con zona horaria y su ejecución lógica concreta,
  con fecha prevista, ventana del resumen y condición de recuperación cuando corresponda.
- **Condición y episodio**: Criterio de consumo o estado funcional y su activación persistente
  o suceso puntual, con evidencia, estado de evaluación y referencias de origen.
- **Destinatario elegible**: Cuenta funcional registrada, activa y autorizada para consultar
  el contenido, con correo obtenido de su estado vigente al intentar el envío.
- **Notificación y entrega**: Contenido de una ocurrencia o episodio y su envío individual
  a una cuenta, con identidad, estado y vínculos a la versión de regla. Cada contenido del
  resumen incluye cobertura, conteo conocido o ausente y referencias al alcance de la historia.
- **Intento e historial**: Registro de fecha, destinatario efectivo, resultado, causa,
  proceso o actor y decisión de recuperación o reenvío, sin secretos técnicos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100 % de los casos de permisos, solo el Administrador técnico configura
  o reenvía notificaciones; los demás perfiles no modifican reglas ni consultan contenidos
  que no les corresponden, incluidos accesos directos. Los casos incluyen cambios
  concurrentes de correo/permisos/estado de una cuenta con varias reglas y pausa de regla;
  una pérdida de elegibilidad confirmada antes del inicio registrado impide el intento.
- **SC-002**: En todos los casos de programación, las ocurrencias y ventanas coinciden con
  el calendario esperado, incluidos el resumen diario de las 06:00, cambios horarios,
  días inexistentes y recuperación tras reinicio, sin duplicados lógicos. Ante una actualización
  de reglas horarias, las fechas futuras no materializadas se ajustan antes de planificar;
  las ocurrencias existentes conservan su fecha, evidencia y versión, y las previsualizaciones
  afectadas requieren renovación.
- **SC-003**: Con aplicación, datos y correo operativos, el 100 % de los 40 primeros intentos
  DEBE comenzar dentro de 60 segundos de su programación o detección válida. El perfil de
  aceptación usa 10 destinatarios elegibles y cuatro reglas coincidentes, dos periódicas
  y dos urgentes, cada una dirigida a esas diez cuentas; cola inicialmente vacía, cuatro
  plazas de envío y transporte de prueba que confirma cada aceptación en un máximo de
  un segundo. Se registran entorno, recursos, versiones y los tiempos observados con
  reloj real, desde la programación o detección hasta el inicio de cada intento.
- **SC-004**: Las reglas de consumo de referencia producen exactamente los episodios
  esperados en los límites de comparación, con cero alertas originadas por reemplazar
  datos ausentes con ceros o por recorrer íntegramente un lote histórico.
- **SC-005**: En todos los casos de envío se conserva el estado por destinatario y los
  límites de intentos; ninguna entrega aceptada o indeterminada se reenvía automáticamente.
- **SC-006**: El 100 % de los contenidos de referencia respeta los permisos vigentes del
  destinatario y la separación respecto de observabilidad, sin direcciones ajenas,
  credenciales ni acceso público a datos protegidos.
- **SC-007**: Durante los 12 meses mínimos pueden identificarse configuración, episodio u
  ocurrencia, destinatario, intentos y resultado de cada entrega de referencia, incluidas
  pausas, revisiones, cancelaciones y reenvíos explícitos.
- **SC-008**: En al menos 9 de 10 tareas con Administradores técnicos representativos,
  se configura sin ayuda el resumen diario de las 06:00 para un destinatario elegible
  y se identifica su siguiente envío en un máximo de tres minutos.

- **SC-009**: Los casos funcionales de programación, evaluación, contenido, aceptación y
  fallos de correo pueden ejecutarse localmente sin servicios remotos ni una VPS. Los
  resultados identifican el transporte de prueba y, durante la validación en VPS, todas
  las referencias a ECS-EC usan su dirección pública y exigen los permisos correspondientes.

## Assumptions

- **Entornos y correo de prueba**: Se aplica la fase local y el despliegue final en VPS
  de la spec-001. Las pruebas locales usan un componente o sustituto de correo local;
  su aceptación identifica ese transporte y no afirma una entrega real a un buzón externo.
  El plan concretará el servicio de producción y su configuración para la VPS, manteniendo
  la evaluación y programación dentro del monolito. Los enlaces usan la dirección de la
  aplicación correspondiente a cada entorno y conservan los permisos de la spec-006.
- **Canal y destinatarios**: El canal inicial es correo para ambas modalidades. Los
  destinatarios son cuentas funcionales activas de Operador o Administrador técnico, no
  direcciones externas ni identidades técnicas. La configuración inicial no habilita envíos.
- **Trazabilidad confirmada**: La persona solicitante confirmó recepción, calidad y cambios
  administrativos funcionales. La inclusión de auditoría administrativa obliga a que todos
  sus destinatarios tengan ese permiso; no se adjunta telemetría reservada a Programador.
- **Reglas de consumo**: Se utilizan energía y categorías de la spec-001 con las ventanas
  conservadas por la spec-002. El intervalo corresponde al definido para las mediciones
  de esa regla. En esta versión se requieren datos completos; no se añaden reglas con
  estimaciones, expresiones arbitrarias o umbrales monetarios.
- **Tiempo y ventanas**: El horario usa por defecto la zona del edificio, guardada en la regla.
  Un resumen diario de las 06:00 cubre desde las 06:00 programadas del día anterior hasta
  las actuales, mostrando sus límites, no necesariamente un día calendario de la spec-005.
  Los intervalos relativos se miden en tiempo transcurrido y las recurrencias calendario
  siguen la política de FR-007.
- **Activación y datos tardíos**: La evaluación urgente comienza con ventanas admisibles
  que cierren durante la vigencia de la regla. Se evalúa la más reciente disponible;
  insertar períodos anteriores no reproduce urgencias ya superadas. El contenido declara
  la ventana real y el retraso cuando exista, sin prometer detección antes de recibir los datos.
- **Persistencia de condición**: Una condición que continúa activa forma un solo episodio
  hasta una normalización comprobada. Sin datos suficientes se conserva su estado con
  esa limitación. Los sucesos puntuales se identifican individualmente y no se duplican
  por reintentos del procesamiento.
- **Urgencia y disponibilidad**: "De inmediato" se concreta como primer intento dentro
  de 60 segundos de la detección válida con servicios operativos; no garantiza llegada
  a bandeja ni lectura. La frecuencia mínima de recepción no limita este plazo.
- **Recuperación**: Hasta tres intentos totales, con las esperas de FR-019. La pausa o
  sustitución de una regla cancela intentos pendientes; un resultado indeterminado exige
  decisión administrativa para reenviar. Las ocurrencias nunca intentadas durante una
  interrupción se recuperan mediante un resumen consolidado identificado como tardío.
- **Contenido y reportes**: Los correos incluyen resumen funcional y referencias protegidas,
  sin adjuntar automáticamente los PDF de la spec-005. El envío programado de notificaciones
  no cambia el tamaño de página ni la selección de períodos de esos reportes.
- **Conservación y consulta**: El historial funcional de notificaciones usa el mínimo de
  12 meses del proyecto. La consulta propia del Operador no permite cambiar destinatarios,
  preferencias o suscripciones por sí mismo; esas acciones son configuración administrativa.
- **Relación con las specs anteriores**: Se amplía el alcance previo que excluía alertas
  y correo automático para incorporar esta función. Se mantienen la autorización de la
  spec-006 y la separación técnica de la spec-007; no se incorporan recuperación de
  contraseñas por correo ni notificaciones técnicas externas.
- **Dependencias y gobierno**: Se requieren datos y estados funcionales, cuentas y correos
  vigentes, zona horaria y servicio de correo configurado. Los entregables de costos y PDF
  se planifican en [spec-004](../004-costos-tarifa-bt43/plan.md) y
  [spec-005](../005-generar-reportes-pdf/plan.md), con tareas para sus resultados persistidos
  y eventos de fallo. Son prerrequisitos de sus alertas de sistema y de la aceptación integral;
  no bloquean la configuración, el correo periódico ni las alertas de consumo que ya cuenten
  con sus dependencias reales. El plan debe concretar su integración,
  ejecución programada y evidencia de aceptación sin seleccionar aquí proveedor o tecnología,
  manteniendo la arquitectura monolítica y documentación integral.

## Contexto de planificación compartido

La [arquitectura](../../docs/architecture.md) y la
[hoja de ruta](../../docs/implementation-roadmap.md) centralizan decisiones y orden del
sistema. La infraestructura es de [plataforma009](../009-fundaciones-plataforma/spec.md);
identidad/consumo/observabilidad se entregan en sus propias funcionalidades. Los contratos
y tareas de esta carpeta describen notificaciones y su integración con esas capacidades.
