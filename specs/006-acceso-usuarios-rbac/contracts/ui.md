# Contrato de interfaz: Acceso y administración

UI de React/Next.js exportada y servida por el monolito. [HTTP](http.md) suministra datos
en runtime; [integraciones](integrations.md) determina la matriz. El build contiene solo
estructura pública, sin cuentas, correos reales, permisos efectivos ni datos del edificio.

## Rutas y navegación

| Página estática | Sin sesión | Sesión restringida | Operador normal | Administrador normal |
| --- | --- | --- | --- | --- |
| `/ingreso/` | Formulario | Ir a renovación | Ir a datos/retorno seguro | Ir a datos/retorno seguro |
| `/cuenta/` | Ir a ingreso | Solo renovación y cierre | Cambio propio y cierre | Cambio propio y cierre |
| `/administracion/usuarios/` | Ir a ingreso | Ir a renovación | Acceso denegado sin datos | Listado, alta, edición y reset |
| `/administracion/historial/` | Ir a ingreso | Ir a renovación | Acceso denegado sin datos | Consulta de historial |
| Consultas/PDF de 001/002/004/005 | Ir a ingreso | Ir a renovación | Disponibles cuando existan | Mismas consultas disponibles |
| Configuraciones propietarias | Ir a ingreso | Ir a renovación | Sin entrada de navegación | Enlaces a módulos existentes |

No hay registro público ni enlace de autoasignación de perfil. El panel administrativo
común ofrece usuarios/historial y solo enlaces a configuraciones reales registradas por
sus propietarios. La edición de fuentes/correspondencias pertenece a 001 y la de
suministro/perfiles BT4.3 a 004. Los mínimos de recepción de 15 minutos y conservación
de 12 meses son restricciones de 002 sin edición web en 006. No presenta formularios
ficticios de recepción, retención, SFTP o tarifas; sus validaciones y estados pertenecen
al módulo correspondiente.

`SessionProvider` se monta como componente cliente desde `frontend/src/app/layout.tsx`
durante US1 y envuelve las páginas de ingreso y cuenta, conservando la exportación
estática. Consulta `/auth/session` al entrar/recargar y antes de habilitar vistas privadas.
Estado inicial de carga sin mostrar datos previos ni asumir permisos desde localStorage.
El cliente conserva CSRF únicamente en memoria, cookie de sesión solo HttpOnly. Reactivar
una pestaña revalida; toda API mantiene control vigente en servidor. La navegación de
US2 reutiliza ese proveedor ya montado; el acceso local de US1 no depende de incorporarla.

Los clientes de consulta usan `sessionActivityHeaders(activity)` de
`frontend/src/lib/api/session.ts`: navegación de datos, Consultar, Actualizar y filtros
iniciados por la persona envían `interactive`; sondeos/revalidaciones automáticos envían
`background`, que es el valor predeterminado. La consulta interna `/auth/session` nunca
prolonga la sesión, incluso con `interactive`. [HTTP](http.md#sesión-y-actividad) define
el comportamiento temporal; esta cabecera no concede permisos.

## Ingreso, renovación y cierre

Formulario de ingreso: correo y contraseña, labels y mensajes accesibles, autocompletado
`username`/`current-password`. No recortar contraseña ni modificar mayúsculas. Obtener
presesión/CSRF antes del envío; mostrar espera de envío y evitar doble submit. Un error
401 usa el mensaje común del servidor sin sugerir si existe la cuenta. 429 muestra el
tiempo de Retry-After; al terminar permite intentar otra vez, sin autenticar automáticamente.

Ingreso restringido dirige a `/cuenta/` con explicación de renovación obligatoria y
solo campos actual/nueva/confirmación y cierre. La confirmación es local y no se envía
como otro secreto. Comunicar 15..128 caracteres, espacios permitidos y sin clases
obligatorias; permitir pegar y usar gestor de contraseñas. El servidor vuelve a validar.
Tras cambio exitoso, borrar campos/contexto y volver a ingreso: todas las sesiones,
incluida la actual, están revocadas. No habilitar datos privados antes de nuevo login.

Cierre invalida sesión por POST con CSRF, vacía datos/contextos en memoria y dirige a
ingreso. Comunicar cierre/cambio de credencial a otras pestañas mediante BroadcastChannel
sin enviar cuentas, cookies o tokens; estas también vacían estado. En 401, limpiar datos
privados y pedir ingreso; en 403 diferenciar permiso de renovación/CSRF. El back/forward
cache de navegador debe revalidar en pageshow y no mostrar datos hasta entonces. No
persistir respuestas privadas en service workers, caches de aplicación o almacenamiento
del navegador. Un fallo de red es error, nunca prueba de cuenta vacía o sesión autorizada.

Retorno tras ingreso: solo rutas relativas en lista local registrada, incluida query
validada de filtros/UUID de reporte. Rechazar URLs absolutas, `//`, esquemas, backslashes,
encodings que cambien origen y bucles hacia ingreso. Fallback de navegación a la vista
de consumo de 001 cuando exista (`/consumption/`); durante validación aislada usar `/cuenta/`.
El retorno no concede acceso: la API de destino vuelve a autorizar.

## Administración de cuentas

Listado paginado con correo, perfil, estado y renovación pendiente; estados de carga,
vacío y error distintos. Filtros por perfil/estado, sin mostrar hashes ni secretos de
otras cuentas. Alta pide correo, uno de los dos perfiles, estado y contraseña inicial
con confirmación; el formulario explica que el titular debe renovarla. No conservarla
después de éxito ni incluirla en confirmación/historial; la entrega usa procedimiento
operativo fuera de esta función, sin correo automático.

Edición modifica correo/perfil/estado usando revisión recibida. Desactivar es el
mecanismo normal y conserva identidad, sin botón de borrado. Reset de otra cuenta pide
nueva contraseña inicial y explica invalidación de sesiones y renovación obligatoria;
no muestra la anterior. La cuenta propia usa el formulario personal para contraseña.
Un cambio propio de correo/perfil/estado que confirma revoca la sesión y lleva a ingreso.

412 exige recargar antes de editar, manteniendo solo campos no secretos para comparación;
409 de correo/último administrador muestra causa comprensible sin afirmar cambios.
El servidor controla la concurrencia aunque dos pantallas permitan solicitar un cambio.
Error por campo mantiene datos no secretos; campos de contraseñas se vacían después de
envío fallido o confirmado. 503 distingue fallo de confirmación: pedir recarga/ingreso
antes de repetir una operación cuyo resultado sea incierto.

## Historial y consultas propietarias

Historial solo lectura con fecha (UTC almacenado y zona de presentación explícita),
actor identificado/proceso/no autenticado, acción, destino y resultado. Filtros de
período/acción/resultado/actor/destino y paginación estable; sin edición ni borrado.
No incluir valores anteriores/nuevos de contraseñas ni secretos. El actor desactivado
mantiene referencia estable; no se sustituye por un perfil declarado en la solicitud.

El Operador ve referencias funcionales necesarias en costos/boletas y puede generar
PDF; no recibe paneles completos de configuración ni acciones de recálculo/revisión.
Abrir por URL una descarga existente vuelve a autenticar. Al cerrar/vencer sesión se
limpian también datos de consumo, costos e historial presentes en memoria de sus vistas.
La autorización de archivos ya descargados conserva el alcance sin conexión de 005.

## Verificación de UI y personas

Vitest comprueba estados/navegación y manejo saneado de errores. Playwright verifica
ambos perfiles, sesión restringida, URLs directas, manipulación de perfil, limpieza al
salir/vencer, pestañas y ausencia de datos privados en export. Labels, foco, teclado y
mensajes por campo forman parte de la revisión. Las pruebas automatizadas no sustituyen
SC-007: diez tareas con personas representativas, al menos nueve completadas sin ayuda
en un minuto desde ingreso hasta la vista de datos asignada. Registrar resultados reales
y obstáculos; sin participantes se mantiene pendiente.
