# Research: Autenticación y permisos por perfil

**Fecha**: 2026-11-01. Investigación de diseño para [spec.md](spec.md), sobre
[arquitectura](../../docs/architecture.md), [hoja de ruta](../../docs/implementation-roadmap.md)
y [constitución](../../.specify/memory/constitution.md). Se revisó el
[traslado previo](tasks.md) y se investigaron por separado seguridad e integraciones.
Las fuentes respaldan las decisiones; no acreditan instalación, rendimiento ni ejecución.

## R1. Pila y límites del módulo

**Decisión**: Reutilizar Python 3.14, FastAPI, SQLAlchemy/Psycopg asíncronos, PostgreSQL 18
y Next.js con export estático definidos por plataforma009. Añadir `argon2-cffi` y
`email-validator` como dependencias de identidad. Fijar versiones y transitivas en el lock
durante implementación; verificar construcción real sobre la imagen CPython 3.14 elegida.
**Razón**: Identidad debe existir sin SMTP, fuentes de consumo, visores ni notificaciones.
No necesita un servidor de identidad externo ni otro proceso propio.
**Alternativas consideradas**: IdP remoto y sesiones gestionadas por un servidor Next
añaden dependencias y contradicen el despliegue seleccionado. JWT con permisos embebidos
complica la invalidación inmediata y obliga igualmente a consultar estado vigente.

## R2. Credenciales y correo

**Decisión**: Argon2id mediante `argon2-cffi`; parámetros iniciales explícitos de 65536 KiB,
3 iteraciones, paralelismo 4, salt de 16 bytes y salida de 32 bytes, almacenada en formato
PHC. Ejecutar el hashing fuera del bucle asíncrono, con concurrencia acotada por memoria;
medir en el contenedor antes de fijar el límite operacional. La versión publicada 25.1.0
declara Python 3.14, lo que no sustituye la comprobación de sus bindings en la imagen.
**Razón**: Hash no recuperable y sin el límite de 72 bytes de bcrypt. La contraseña usa
los 15..128 puntos de código Unicode de la spec, UTF-8 exacto, sin recorte, normalización,
conversión de mayúsculas ni truncamiento. La renovación propia exige un valor distinto
del actual; no se introduce historial de contraseñas.
**Alternativas consideradas**: bcrypt puede truncar contraseñas admisibles; PBKDF2 no
resuelve una necesidad adicional del proyecto; cifrado reversible incumple FR-018.
**Fuentes**: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[parámetros de argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/parameters.html),
[publicación del mantenedor](https://pypi.org/project/argon2-cffi/).

**Decisión**: Una sola función de correo para alta, edición, ingreso y espera: quitar
espacios exteriores, validar sintaxis con `email-validator`, conservar su dirección
normalizada y construir `email_key` con local-part casefold y dominio IDNA ASCII minúsculo.
La normalización Unicode admitida por la biblioteca se aplica al correo, nunca a la
contraseña. No quitar puntos ni sufijos `+`. No consultar DNS/MX (`check_deliverability=False`).
El índice único incluye cuentas inactivas. `example.test` se admite mediante
`test_environment=True` exclusivamente en desarrollo/pruebas.
**Razón**: FR-003 define equivalencia por mayúsculas y espacios; una clave común impide
divergencias entre unicidad, ingreso y bloqueo. El alta no debe depender de red externa.
**Alternativas consideradas**: Comparación sensible a mayúsculas contradice la spec;
aplicar reglas particulares de proveedores uniría direcciones distintas. Verificación
automática por correo pertenece a un alcance no solicitado.
**Fuentes**: [email-validator](https://github.com/JoshData/python-email-validator),
[OWASP Email Validation](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html).

## R3. Sesión durable y renovación

**Decisión**: Token aleatorio de 32 bytes codificado base64url, solo en cookie
`ecs_ec_session`; almacenar únicamente SHA-256 del token. Cuenta con `auth_version`:
todo cambio efectivo de correo, perfil, estado o contraseña incrementa esa versión y
revoca sus sesiones en la misma transacción. Un cambio propio de contraseña también
revoca la sesión utilizada y termina con nuevo ingreso, sin sesión excepcional.
**Razón**: Cada petición comprueba cuenta y versión actuales, sin confiar en perfil del
cliente. Se comprueban los límites de 30 minutos y 8 horas antes de actualizar actividad;
reiniciar la aplicación no prolonga ni restaura una sesión.
**Alternativas consideradas**: Cookies firmadas autosuficientes, memoria del proceso y
tokens en localStorage dificultan revocación, reinicios o protección del secreto.
**Fuente**: [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

La autorización ordinaria usa una lectura fresca READ COMMITTED en una UoW breve, sin
retener locks de cuentas al entrar al módulo consumidor. Una operación ya admitida puede
terminar; después del commit de invalidación ninguna admisión nueva acepta la sesión
antigua. El límite durable de envíos tiene revalidación propia en spec-008. Una captura
REPEATABLE READ de PDF no puede reutilizar una identidad obtenida de una captura antigua.

## R4. CSRF, presesión y actividad

**Decisión**: Mismo origen para API/UI; token `X-CSRF-Token` y comprobación de origen para
POST/PUT/PATCH/DELETE, incluidos ingreso, cierre y generación PDF. Una presesión de 10
minutos, con cookie HttpOnly separada, permite obtener el token para ingreso; nunca se
promueve a sesión. Al ingresar se destruye y se emite un secreto completamente nuevo.
El token CSRF se deriva mediante HMAC-SHA-256 de una clave externa persistente, namespace
de presesión/sesión y secreto de su cookie; no exige guardar el bearer en texto claro.
GET del contexto correspondiente entrega el token solo al mismo origen, con no-store.
**Razón**: SameSite ayuda, pero no sustituye CSRF ni protege por sí solo el login.
Validar `Origin` exacto; si falta, usar el origen de `Referer`; sin ambos, rechazar.
**Alternativas consideradas**: Solo SameSite es insuficiente; token en URL filtra secretos;
un token persistente en el build estático no pertenece a una sesión individual.
**Fuente**: [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

Introspección, obtención de CSRF y sondeo automático no renuevan actividad. Las acciones
interactivas se identifican por ruta/política del módulo: login, navegación/consulta
solicitada por la persona y mutaciones autorizadas. En endpoints reutilizados por polling,
el cliente declara `X-Session-Activity: interactive|background`; omitirlo significa
background. Es una indicación de UX, nunca una autorización ni un permiso. La duración
absoluta de ocho horas rige incluso con actividad continua.

El helper `sessionActivityHeaders(activity)` de `frontend/src/lib/api/session.ts` centraliza
esa clasificación con default background. Las pruebas cubren la cabecera generada y su
conexión a consultas reales: interactive al minuto29 desplaza inactividad al59; solo
sondeos deja vencer al30. Introspección nunca renueva aunque reciba interactive y la
duración absoluta no se desplaza.

## R5. Intentos fallidos y concurrencia del ingreso

**Decisión**: Bucket durable sin FK a cuenta, identificado por HMAC de correo canónico y
origen de red confiable. Ventana móvil `(ahora-15min,ahora]`; quinto fallo activa espera
hasta `ahora+15min`. El quinto fallo y los intentos durante espera responden 429 con
Retry-After; no extienden la espera. Un éxito fuera de espera limpia los fallos. Al vencer
la espera se reinicia el bucket. Desconocidas e inactivas siguen las mismas respuestas.
**Razón**: La política debe sobrevivir a reinicios y aplicarse también a correos que no
existen. Hash ficticio del mismo costo para desconocidas; nunca devolver motivo interno.
**Alternativas consideradas**: Contador por cuenta filtra existencia; bloqueo permanente
o límite solo por IP cambia la regla aprobada; memoria local pierde el estado al reiniciar.
**Fuente**: [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

Calcular Argon2 sobre una captura sin mantener locks. En UoW posterior bloquear/crear
atómicamente el bucket, revalidar espera y versión/hash/estado de la cuenta y solo entonces
registrar fallo o emitir sesión. Una cuenta cambiada durante el hashing obliga a rechazar
ese resultado y repetir el ingreso; nunca autenticar contra la contraseña anterior.
La espera no se elude mediante solicitudes paralelas. El origen procede del peer o de un
proxy explícitamente confiable, no de cabeceras arbitrarias. Para correo mal formado se
aplica una clave determinista del texto recortado/casefold y el mismo rechazo general.

## R6. Último administrador y coordinación neutral

**Decisión**: Guardia singleton persistida, bloqueada FOR UPDATE por toda mutación de
cuenta, bootstrap y recuperación. Después: recursos previos de participantes ordenados,
cuentas por UUID (incluido actor si corresponde), sesiones y recursos posteriores.
Contar administradores activos después de adquirir guardia; impedir que el cambio deje
cero. Revalidar autorización del actor, su sesión original y revisiones después de los
locks, tomando un instante nuevo para vencimientos. Un cierre puede revocar sesión sin
cambiar auth_version; comprobar solo la cuenta sería insuficiente.
**Razón**: Dos degradaciones concurrentes no deben basarse en el mismo conteo anterior.
El registro neutral funciona con cero participantes y nunca importa `notifications`.
**Alternativas consideradas**: Mutex Python no protege otros procesos; COUNT sin lock
permite write skew; bloquear primero cuenta invierte el orden de spec-008 y puede bloquear
mutuamente con un despacho.
**Fuentes**: [PostgreSQL 18, locks](https://www.postgresql.org/docs/18/explicit-locking.html),
[contrato de coordinación](contracts/coordination.md),
[integraciones de notificaciones](../008-notificaciones-programables/contracts/integrations.md).

El registro se congela al componer la aplicación. Si cambian las referencias descubiertas,
rollback completo y redescubrimiento; máximo tres intentos internos, luego 409 reintentable.
Los participantes tienen rangos de orden explícitos; no pueden adquirir recursos previos
después de cuentas. El participante concreto, su cierre de carreras de alta de reglas y
el inicio durable de SMTP pertenecen a 008, antes de su primer envío.

## R7. Auditoría, integración y recuperación

**Decisión**: Usar `FunctionalAudit`/`EventWriter` de plataforma009. Cambios permitidos y
eventos `identity.changed`/`administration.changed` se confirman con la cuenta. Denegaciones
administrativas se registran en UoW propia tras rollback; actor resuelto por servidor o
`unauthenticated`, acción/destino/resultado saneados, sin cuerpo ni credenciales.
**Razón**: Historial consultable sin depender de logs técnicos ni consumidores. Una base
caída produce 503 y no permite afirmar que existe auditoría durable.
**Alternativas consideradas**: Tabla paralela de auditoría en identidad duplica propiedad
de 009; emisión HTTP/SMTP dentro del cambio acopla su disponibilidad.
**Fuentes**: [contrato común](../009-fundaciones-plataforma/contracts/integrations.md),
[modelo común](../009-fundaciones-plataforma/data-model.md).

Bootstrap por CLI con contraseña leída dos veces desde TTY, nunca por argumento; solo
instalación sin cuentas. Recuperación operativa restablece una cuenta administrativa ya
activa y exige motivo, acceso al host y renovación, sin alta pública ni elevación de rol.
Las dos operaciones usan los mismos locks, validación y auditoría que el servicio.

## R8. Transporte, UI y alcance de aceptación

**Decisión**: En VPS rechazar ingreso y API protegida si el esquema efectivo no es HTTPS;
cookie Secure, HttpOnly, SameSite=Lax, host-only y Path=/. Plataforma009 posee TLS/proxy;
006 configura exigencia y pruebas. Confiar cabeceras forwarded solo desde sus proxies.
HTTP local requiere modo development explícito, URL loopback y sin exposición pública;
la aceptación HTTPS se ejecuta además con TLS local y finalmente con dirección pública.
**Razón**: Una redirección después de recibir contraseña por HTTP no la protege.
**Alternativas consideradas**: Confiar en cualquier X-Forwarded-Proto permite eludir el
control; exigir una VPS para pruebas locales impediría US1.9.
**Fuente**: [FastAPI detrás de un proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).

UI estática sin datos privados; sesión consultada en runtime, navegación por permisos,
retorno limitado a rutas locales de la aplicación. Autorización en cada API y nueva
descarga PDF. No añadir configuraciones ni validaciones de consumo/costos a identidad.
El proveedor de sesión se monta desde `frontend/src/app/layout.tsx` durante US1 para
ingreso/cuenta; Navigation se añade en US2 sobre ese mismo contexto, sin bloquear el MVP.
FR-019 administra las configuraciones editables de001/004; los mínimos de recepción de
15min y conservación de12meses de002 son restricciones obligatorias sin edición web en006.
El rechazo administrativo de referencia es una fuente duplicada entre categorías001;
las restricciones002 se verifican por separado mediante sus capacidades reales.
Personas representativas y VPS requieren evidencia real futura, separada de pruebas
aisladas. No quedan decisiones de diseño pendientes de aclaración; direcciones,
credenciales, dimensionamiento y versiones exactas son configuración/verificación de
implementación, sin nuevas garantías de rendimiento.
