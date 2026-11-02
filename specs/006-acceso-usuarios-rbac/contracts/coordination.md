# Contrato de coordinación de mutaciones de identidad

Propietario: spec-006. Se completa la entrada trasladada de 008 conservando ruta,
protocolo neutral y garantías originales. [Arquitectura](../../../docs/architecture.md),
[modelo](../data-model.md), [puertos](integrations.md). No depende del consumidor de
notificaciones ni acredita su implementación.

## Participantes y composición

`IdentityMutation` contiene cuenta objetivo, revisión esperada, campos afectados,
estado candidato no secreto, actor/proceso confiable y referencia de operación. La
coordinación conserva una referencia interna a la sesión original para reautorizar
mutaciones HTTP; los participantes no reciben cookies, tokens, contraseñas o hashes.
La credencial preparada queda privada al servicio de identidad. Los participantes solo
reciben los datos necesarios; nunca son responsables de autenticar al actor.

`IdentityMutationParticipant` expone:

| Operación | Contrato |
| --- | --- |
| `discover(mutation, uow)` | Devuelve referencias afectadas, firma/versiones y claves previas/posteriores de bloqueo; sin efectos ni commit. |
| `lock(plan, phase, uow)` | Bloquea solo su fase en el orden global; no abre otra transacción. |
| `revalidate(mutation, plan, uow)` | Redescubre conjunto y elegibilidad bajo locks; devuelve estable o exige rollback/reintento. |
| `apply(mutation, plan, uow)` | Aplica ajustes de su dominio en la misma UoW; no red ni commit. |

El registro se configura en `main.py` antes de servir tráfico y queda inmutable.
Identidad funciona con cero participantes y no importa tablas/servicios de `notifications`.
Nombres duplicados, rangos de orden incompatibles o participantes incompletos impiden
arrancar con una configuración que prometa coordinación inexistente. Los rangos se
registran explícitamente; no dependen del orden de importación de Python.

## Orden y algoritmo transaccional

1. Validar forma del comando y preparar hash cuando corresponda sin mantener locks.
   Resolver inicialmente identidad del actor sin retener un lock de cuenta.
2. Abrir UoW READ COMMITTED; adquirir guardia singleton de identidad FOR UPDATE. Todas
   las mutaciones de cuenta, incluidas CLI y contraseña propia, siguen esta entrada.
3. Descubrir referencias de todos los participantes y reunir planes. Bloquear recursos
   previos por rango de dominio y UUID ascendente; para 008, reglas afectadas por UUID.
4. Bloquear cuentas necesarias por UUID ascendente, incluido el actor cuando es cuenta.
   Después, sesiones afectadas y sesión original del actor por UUID; finalmente recursos
   posteriores de participantes por rangos registrados, para 008 entregas. Mantener un
   orden único entre dominios; ningún participante adquiere cuentas después de esta fase.
5. Volver a leer cuenta/actor/revisiones y obtener un instante actual después de los locks.
   En HTTP, revalidar sesión original, revocación, vencimientos, modo y auth_version:
   un logout concurrente puede revocarla sin cambiar la versión de cuenta. CLI usa proceso
   confiable y no necesita sesión humana. Comprobar autorización, revisión esperada,
   conjunto de administradores activos y elegibilidad. Redescubrir referencias de cada
   participante. No usar una captura REPEATABLE READ anterior ni hora previa a los locks.
6. Si el conjunto o sus versiones relevantes cambiaron, rollback completo, liberar todos
   los locks y empezar de nuevo con descubrimiento actualizado. No adquirir una regla
   nueva mientras se mantiene bloqueada cuenta. Máximo tres intentos internos; después
   409 `identity_coordination_retry` reintentable, sin efectos parciales.
7. Aplicar cambio de cuenta, incremento de versiones, revocación de sesiones y ajustes
   de participantes. Registrar auditoría/eventos en esa misma UoW y hacer un solo commit.
   Una denegación no confirma ajustes; registra intento saneado después de rollback.

La guardia evita que dos administradores se retiren simultáneamente basándose en el
mismo conteo. El invariante se evalúa tras bloquearla y con el estado posterior; nunca
puede confirmarse cero administradores activos. El bootstrap usa esa misma guardia y
solo permite instalación vacía. Locks de cuenta tomados por dependencias genéricas de
autorización antes del paso 3 invertirían el orden y están prohibidos.

## Obligaciones del participante de notificaciones (spec-008)

La proyección del orden sigue siendo **reglas por UUID → cuenta → entrega**. La guardia
solo la toman mutaciones de identidad; despacho/edición de reglas no la adquieren ni
mutan cuentas. No mantener transacción abierta durante SMTP.

El participante descubre reglas que referencian a la cuenta, revalida conjunto y
eligibilidad y ajusta trabajos todavía no iniciados según su dominio. Altas/cambios de
destinatarios bloquean regla y cuenta y vuelven a leer elegibilidad: si una referencia
nueva confirma antes del lock de cuenta de identidad, la redetección obliga a reintentar;
si espera detrás de identidad, al continuar observa el nuevo estado. No basta con
consultar una lista de reglas una sola vez antes de los locks.

El inicio durable de un intento de correo revalida regla, activación, cuenta, correo y
permisos bajo ese mismo orden. Una mutación confirmada antes de ese inicio impide un
intento inelegible. Si el intento ya fue iniciado durablemente, conserva resultado,
historia y correo efectivo; no se promete retirar un mensaje ya iniciado. Pausa/revisión
de regla comparte ese protocolo. SMTP ocurre después de liberar la UoW.

Spec-006 implementa registro/protocolo neutral y pruebas con participante sintético.
Spec-008 implementa participante concreto, límite durable y pruebas concurrentes reales
antes del primer envío. No convertir su implementación en prerrequisito de ingreso web;
una prueba sintética no acredita esa integración final.

## Pruebas de contrato previstas

- Cero participantes: alta, renovación, edición y recuperación sin tablas de notificaciones.
- Participante sintético: orden de locks, ajuste atómico y rollback por fallo de participante.
- Referencia nueva/revisión cambiada entre descubrimiento y bloqueo: rollback completo,
  redescubrimiento, éxito con conjunto correcto o conflicto tras tres intentos.
- Dos administradores se degradan/desactivan a la vez: permanece al menos uno activo.
- Actor pierde perfil/estado durante su propia operación: revalidación posterior rechaza.
- Cierre de sesión mientras una mutación espera guardia/hashing: no confirma con esa
  sesión revocada. Espera de lock que cruza vencimiento: revalidación temporal rechaza.
- Contraseña restablecida mientras se verifica ingreso: la credencial anterior no crea
  una sesión utilizable después del cambio.
- En 008: probar ambos órdenes de commit de revocación frente al inicio durable, alta
  concurrente de regla/destinatario y pausa/revisión, sin SMTP dentro de transacciones.

Pruebas con conexiones independientes a PostgreSQL 18. SQLite, mutex Python y existencia
de documentos no acreditan estas garantías.
