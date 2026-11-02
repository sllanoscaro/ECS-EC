# Contrato HTTP: Acceso, cuentas e historial

Base `/api/v1`, mismo origen que la UI estática. Diseño para [spec.md](../spec.md),
[modelo](../data-model.md) y [puertos](integrations.md). Las formas siguientes se
implementarán en `identity/schemas.py` y en OpenAPI generado por FastAPI; no existe aún
servidor ejecutable. Campos adicionales se rechazan, incluidos actor/permisos enviados
en cuerpos que no los admiten.

## Transporte y seguridad comunes

En producción, exigir HTTPS efectivo antes de procesar credenciales o recursos protegidos.
Esquema/origen público proceden de configuración; confiar forwarded exclusivamente desde
los proxies previstos por plataforma009. Solicitud insegura devuelve 403 `https_required`,
sin sesión ni datos. El backend no debe ser accesible públicamente fuera de ese proxy.
HTTP de desarrollo solo se habilita explícitamente con URL loopback; se rechaza tal modo
en producción. El listener HTTP público puede redirigir navegación, pero rechaza las
APIs de autenticación/protegidas antes de procesarlas.

Cookie de sesión `ecs_ec_session`: HttpOnly, SameSite=Lax, Path=/, sin Domain, Secure
cuando se usa HTTPS; Max-Age no mayor al vencimiento absoluto. Cookie separada de
presesión `ecs_ec_preauth` con mismos atributos y Max-Age de hasta 600 segundos. No usar
bearers en URL, HTML exportado, localStorage o logs. Respuestas de autenticación y todas
las protegidas, incluidos errores, llevan `Cache-Control: no-store`; no hay CORS con
credenciales para otros orígenes.

Todo POST/PUT/PATCH/DELETE exige JSON cuando tenga cuerpo, `X-CSRF-Token` de su contexto
y `Origin` exacto permitido. Si falta Origin, validar origen de Referer; sin ambos, 403.
CSRF de ingreso usa presesión; las demás operaciones usan sesión. GET obtiene el token
del mismo origen sin enviarlo en parámetros. Formas cross-origin y métodos no registrados
no conceden acceso. No devolver redirects HTTP con cuerpos privados en APIs.

## Sesión y actividad

Cada petición protegida resuelve estado/permisos actuales desde DB, sin reutilizar un
principal entre peticiones. Introspección y sondeos no prolongan sesión. Las rutas
interactivas de mutación autorizada cuentan como actividad; GET de datos comunes admite
`X-Session-Activity: interactive|background`, por defecto background. Una navegación o
filtro iniciado por la persona usa interactive; polling periódico usa background. Esa
cabecera nunca concede permisos ni evita el vencimiento absoluto. Se comprueban ambos
límites antes de actualizar actividad, sin revivir sesiones vencidas/revocadas.
El helper `sessionActivityHeaders(activity)` de `frontend/src/lib/api/session.ts` genera
esa cabecera con valor predeterminado `background`. Los clientes de consultas lo usan
explícitamente para distinguir navegación, Consultar, Actualizar y filtros de los sondeos.
`/auth/session` nunca renueva actividad, aunque reciba `interactive`.

Con ingreso en el minuto 0, una consulta interactiva autorizada al minuto 29 mueve el
límite inactivo al 59, acotado por el vencimiento absoluto. Con solo sondeos automáticos,
la sesión vence al minuto 30. Actividad continua no desplaza las ocho horas absolutas;
una solicitud que llega después de cualquiera de sus límites no reactiva la sesión.

La sesión restringida permite solo GET `/auth/session` para identidad mínima/CSRF,
POST `/auth/password` y POST `/auth/logout`. La introspección no otorga acceso funcional;
las demás rutas responden 403 `password_change_required`. El rol efectivo de acceso
normal no se habilita hasta renovar y autenticarse de nuevo.

## Operaciones de acceso

| Método/ruta | Contexto | Entrada y respuesta |
| --- | --- | --- |
| GET `/auth/csrf` | Público, transporte/origen permitido | Crea o reutiliza presesión vigente; 200 `{csrf_token, expires_at}` y cookie preauth, sin datos de cuentas. No renueva una sesión. |
| POST `/auth/login` | Presesión + CSRF | `{email,password}`; 200 `SessionView`, cookie nueva y eliminación de preauth. Fallo general 401 o espera 429. |
| GET `/auth/session` | Sesión normal o restringida | 200 `SessionView`; 401 si no es válida. Nunca renueva actividad. |
| POST `/auth/logout` | Sesión normal o restringida + CSRF | Sin cuerpo; revoca sesión utilizada, borra cookie, 204. Sesión ya inválida devuelve 401 y borra cookie; no atribuye actor autenticado. |
| POST `/auth/password` | Sesión normal o restringida + CSRF | `{current_password,new_password}`; 204, revoca todas las sesiones y borra cookie. Debe iniciarse sesión de nuevo. |

`SessionView`: `{account:{id,email,role}, session_state, must_change_password,
absolute_expires_at, idle_expires_at, csrf_token, permissions}`. `session_state` es
`normal|password_change_required`; `permissions` contiene nombres de acciones fijas
permitidas. En estado restringido solo incluye `session.read`, `session.logout`,
`account.password.change`. Ni el rol ni esta lista sustituyen verificación en servidor.
No contiene hash, digest, secreto de cookie, datos de terceros ni detalles de red.

Email de login es string de hasta 320 caracteres; sintaxis inválida dentro de ese límite
recibe el mismo rechazo general, no una confirmación de existencia. Password de login
admite string de hasta 128 caracteres; longitudes inadmisibles no se hashean. Error de
forma JSON/tipo/límite de cuerpo es 422 sin evaluar existencia. Para nuevas contraseñas
y altas/reset rige 15..128 puntos de código, sin transformación. Password actual errónea
en cambio propio devuelve 422 `current_password_invalid`, sin cambiar nada; nueva igual
a actual, 422 `password_unchanged`. El servicio nunca recupera la contraseña anterior.
El cambio propio no requiere If-Match público: captura versión/hash antes de Argon2 y
los revalida bajo el protocolo de locks. Las mutaciones HTTP revalidan además la sesión
original después de esperar locks, incluyendo revocación, modo y vencimientos con un
instante nuevo; si se cerró/venció durante la espera, no confirman el cambio.

Desconocida, incorrecta o inactiva: 401 `invalid_credentials`, detalle común
«No fue posible ingresar con esas credenciales». Misma política de cuerpo/cabeceras y
verificación de costo comparable para desconocidas. Quinto fallo de la pareja correo/origen
en ventana móvil: 429 `login_wait`, detalle general de espera y `Retry-After` en segundos
redondeados hacia arriba. No revelar conteo, cuenta/estado o causa interna. Durante los
15 minutos de espera tampoco autenticar una contraseña correcta; no extender el plazo.
Los valores y carreras se detallan en [modelo](../data-model.md#intentos-identity_login_bucket).

## Administración de cuentas

Solo sesión normal de Administrador técnico; todas las rutas se protegen también en GET.
Primero autenticar/autorizar, después resolver el objeto para no revelar cuentas al Operador.

| Método/ruta | Entrada | Respuesta |
| --- | --- | --- |
| GET `/identity/accounts` | Query opcional `status`, `role`, `cursor`, `limit` | 200 `{items:[AccountView],next_cursor}`. |
| POST `/identity/accounts` | `{email,role,status,initial_password}` | 201 `AccountView`, Location y ETag; renovación siempre true. |
| GET `/identity/accounts/{account_id}` | UUID | 200 `AccountView` y ETag. |
| PUT `/identity/accounts/{account_id}` | `{email,role,status}`, `If-Match` | 200 `AccountView`/ETag; reemplaza solo esos campos editables. |
| POST `/identity/accounts/{account_id}/password-reset` | `{new_password}`, `If-Match` | 200 `AccountView`/ETag; solo otra cuenta, renovación true, revocación total. |
| GET `/identity/administration-history` | Query `from`, `to`, `action`, `result`, `actor_id`, `target_id`, `cursor`, `limit` | 200 `{items:[AdministrationEntry],next_cursor,cutoff_at}`. |

`AccountView`: `{id,email,role,status,must_change_password,revision,created_at,updated_at}`.
Roles `operador|administrador_tecnico`; estados `active|inactive`. No aceptar cambios de
rol/estado en `/auth/password`. No hay DELETE ni registro público. Reset de sí mismo por
la vía administrativa devuelve 422 `use_own_password_change`; usar la ruta personal.

ETag fuerte `"identity:<uuid>:<revision>"`; `If-Match` exacto obligatorio para PUT/reset:
ausente 428, obsoleto 412, sintaxis no admitida 422. Comparación bajo lock, no solo en
controlador. No-op con precondición vigente conserva revisión/sesiones. Cambio efectivo
incrementa revisión y auth_version y revoca todas las sesiones de la cuenta. Si el admin
modifica su propia cuenta, la respuesta puede confirmar el cambio pero elimina su cookie;
la siguiente petición exige ingreso. No permitir que el cambio deje cero admins activos:
409 `last_active_administrator`. Correo equivalente ocupado, incluso inactivo: 409
`email_conflict`, solo visible a admin autorizado.

Una repetición de alta no crea otra cuenta: la unicidad de correo devuelve 409; no se
devuelve ni se genera otra contraseña. Tras pérdida de respuesta, un admin consulta y
recarga revisión antes de reintentar PUT/reset. No hay idempotencia implícita que eluda
la autorización o la precondición. Los replays de otros módulos mantienen sus contratos
y siempre vuelven a autorizar antes de recuperar resultados confirmados.

Listados: `limit` 1..100, 25 por defecto; cursor opaco ligado a filtros/orden, inválido 422.
Cuentas ordenadas por `(created_at,id)` ascendente. Historial por `(occurred_at,id)`
descendente, corte fijado en primera página y conservado en cursor; solo `[from,to)` con
ambos instantes RFC3339 UTC/offset e inicio<fin, por defecto últimas 24 h. No publicar
cadenas de conexión ni mensajes de excepciones dentro de cursores/errores.

`AdministrationEntry`: `{id,occurred_at,actor:{kind,account_id|null,process_code|null},
action,target:{module,entity_type,id|null,revision|null},result,reason_code,operation_ref}`.
Kind `account|process|unauthenticated`; result `allowed|denied|rejected`. Acciones/códigos
son catálogo tipado; no devolver cuerpos originales. Cuenta desactivada conserva UUID.
La API permite consulta, nunca editar/borrar eventos. Cambios ajenos se leen del escritor
común de 009, sin importar sus tablas a identidad.

## Errores y auditoría

`Problem`: `{code,detail,operation_ref,field_errors:[{path,code,message}]}` saneado,
compatible con `core/errors.py`. Nunca incluye valores de contraseñas, hashes, cookies,
CSRF, cuerpo recibido, SQL ni stack trace. Validar autorización antes de responder errores
de objeto administrativo. Estado 401: sesión ausente/inválida; 403: permiso, renovación,
CSRF/origen o HTTPS; 404: recurso inexistente después de autorizar; 409: correo/invariante/
coordinación; 412/428: revisión; 422: campos; 429: espera; 503: DB/dependencia inaccesible.

Errores de coordinación tras tres intentos completos: 409 `identity_coordination_retry`,
reintento explícito sin cambios parciales. Ante 503 de confirmación ambigua, recargar
recurso con otra sesión vigente o ingresar de nuevo; no afirmar rollback si no se conoce
el resultado del commit. Una indisponibilidad no se convierte en lista vacía ni acceso
permisivo.

Todo cambio administrativo y todo acceso administrativo denegado (incluidos GET,
ausencia de sesión y CSRF/origen rechazados) registra acción, destino saneado y actor
confiable o condición no autenticada. Para denegación temprana, resolver identidad solo
con la cookie válida, sin efectos de actividad; si falta/no es válida usar unauthenticated.
El rechazo se audita en UoW propia después de rollback. Si DB impide auditar, responder
503 sin atribuir evidencia durable; no guardar secretos como sustituto en logs. Un error
HTTPS temprano tampoco ejecuta cambios ni refleja un actor declarado por el cliente.
