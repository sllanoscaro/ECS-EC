# Quickstart y validación: Identidad y permisos

Guía para la implementación prevista en [plan.md](plan.md). Hoy no existen los módulos
de aplicación ni las suites indicadas: los comandos de aplicación serán ejecutables al
implementar las tareas integrales. Esta planificación no acredita autenticación real,
pruebas aprobadas ni aceptación de personas/VPS.

## Prerrequisitos y preparación

Plataforma009 debe proporcionar herramientas/locks, PostgreSQL 18, migraciones, UoW,
reloj, errores, auditoría/eventos y composición según [hoja de ruta](../../docs/implementation-roadmap.md).
Configurar `DATABASE_URL` y secretos externos `IDENTITY_CSRF_KEY`/
`IDENTITY_LOGIN_BUCKET_KEY`, el origen público y proxies confiables en la configuración
validada; valores reales nunca se versionan. El modo local HTTP requiere development
explícito y loopback. Producción rechaza esa excepción. No habilitar SMTP ni visores para
probar identidad. Bloquear acceso funcional normal hasta terminar bootstrap.

Comandos previstos desde la raíz; DB de pruebas independiente con PostgreSQL real:

```sh
uv sync --locked
npm --prefix frontend ci
docker compose up -d db
uv run alembic -c backend/alembic.ini upgrade head
uv run ecs-ec identity bootstrap-admin --email admin@example.test
docker compose up -d app
```

El bootstrap pide contraseña dos veces por TTY y no la imprime; `example.test` solo en
desarrollo/pruebas. Ingresar en `/ingreso/`, renovar en `/cuenta/` y volver a ingresar.
Crear otra cuenta administrativa y un Operador, con credenciales locales propias y
renovación. No hay contraseña compartida pública ni alta web sin administrador.

`scripts/seed_identity_reference.py` será una herramienta de fixtures solo para pruebas:
rechaza producción, lee credenciales de entrada protegida y crea cuentas activas/inactivas,
sesiones y revisiones conocidas sin imprimir secretos. No altera DB real del edificio.
La migración `identity_initial.py` se encadena al head existente sin recrear tablas de 009.

## Ejecución de suites previstas

```sh
uv run pytest backend/tests/unit/identity backend/tests/integration/identity backend/tests/contract/identity
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend exec playwright test tests/e2e/identity.spec.ts
```

Configurar previamente DB de pruebas, origen y URL de Playwright según el entorno de
plataforma. Las pruebas usan reloj inyectable interno y barreras/conexiones concurrentes;
no hay endpoint público para avanzar tiempo o cambiar permisos. Leer [HTTP](contracts/http.md),
[modelo](data-model.md) y [coordinación](contracts/coordination.md) para cuerpos/invariantes,
sin copiar implementación en esta guía.

## 1. Ingreso, espera, renovación y expiración — US1, SC-001/004

Probar cuenta activa por perfil, inactiva, correo desconocido y contraseña incorrecta.
Desconocida/incorrecta/inactiva reciben el mismo 401 general; no aparece correo o causa
interna en errores/logs. Espacios de contraseña y mayúsculas se conservan; correo ignora
mayúsculas y espacios exteriores. Contraseñas de 15/128 caracteres Unicode funcionan;
14/129 se rechazan sin truncar. Verificar hash no recuperable y ausencia de secretos en
listados, historial, respuestas y export estático.

Cinco fallos de la misma pareja correo/origen dentro de 15 minutos: quinto y siguientes
responden 429/Retry-After; incluso una contraseña válida espera. No extender plazo con
intentos bloqueados; al cumplir 15 minutos puede ingresar. Repetir con correo desconocido,
origen diferente y solicitudes paralelas, antes/después del borde de ventana; reiniciar
app no borra la espera. Un éxito fuera de bloqueo limpia fallos previos.

Login exige presesión/CSRF y origen válido; rechazar sin token, token de otro contexto,
origen ajeno o presesión consumida/vencida. Cookies HttpOnly/SameSite y secreto nuevo
después de login; no aceptar la cookie de presesión como sesión. Token CSRF no va en URL.

Credencial inicial/reset solo habilita renovación/cierre e introspección mínima. Intentar
consumo, PDF y cuentas desde sesión restringida devuelve 403. Renovación exige contraseña
actual y nueva distinta, invalida todas las sesiones y requiere nuevo ingreso.

Verificar cierre de una sesión sin cerrar las otras, y vencimiento exactamente a 30
minutos de inactividad o 8 horas absolutas. Actividad antes de 30 min mueve solo el límite
inactivo; polling/introspección no lo mueve. No revive una sesión por solicitudes paralelas
o tardías ni por reiniciar aplicación. Reutilizar cookie vieja después de cierre/vencimiento
da 401. Probar cambio de credencial concurrente con Argon2 de login y retorno a UI.

Casos de actividad con ingreso al minuto0 y reloj interno de pruebas:

| Caso | Resultado esperado |
| --- | --- |
| GET autorizado con interactive al minuto29 | Límite inactivo en59, sin superar el absoluto. |
| Solo sondeos background durante los primeros30min | Sesión vencida exactamente en30. |
| `/auth/session` repetido con interactive | Sin actualización de actividad; vence en30 sin otras acciones. |
| Actividad interactiva continua | Vence al cumplir8h desde ingreso. |
| Solicitud posterior a cualquiera de los límites | Rechazo sin reactivar sesión. |

Las pruebas unitarias verifican `sessionActivityHeaders(activity)` de `session.ts`, incluidos
ambos valores y default background. Las pruebas de consultas reales de US2 comprueban
las cabeceras enviadas por navegación, Consultar, Actualizar y filtros frente a sondeos.
Se usa reloj inyectado internamente, sin endpoint público para avanzar tiempo.

Hacer que una espera de lock cruce el vencimiento de sesión/presesión o el fin de espera
de login: el resultado usa el reloj obtenido después del lock, no el anterior.

## 2. Matriz de acceso y consultas reales — US2, SC-002/003

Ejecutar cada fila de la matriz de [integraciones](contracts/integrations.md) sin sesión,
con Operador, con Administrador y con sesión restringida. Cubrir URL directa y perfil/actor
manipulado en cabecera/cuerpo: nunca concede permisos. GET administrativo es denegado al
Operador; POST de generación PDF sigue permitido con sesión normal y CSRF.

La política aislada puede usar harness sintético. La aceptación integral requiere reales:
catálogo/detalle de 001, agregados de 002, costos/boletas/referencias de 004 y generación/
descarga de 005. Administrador conserva todas las consultas del Operador; este ve precios,
vigencias y versiones usados en resultados sin acceder al panel completo de configuración.
No modificar mediciones, tarifas, boletas o configuraciones al filtrar/generar PDF.

Generar PDF real, cerrar sesión o desactivar cuenta y usar su URL/clave idempotente vieja:
se deniega nueva entrega, sin bytes ni metadatos privados. Repetir con cuenta autorizada:
la descarga funciona sin regenerar por el hecho de descargar. El PDF ya descargado
mantiene su comportamiento sin conexión. Credenciales SFTP/Programador no permiten estas
acciones humanas; una cookie humana no concede SFTP.

## 3. Administración y carreras PostgreSQL — US3, SC-004/005

Crear ambos perfiles activos/inactivos; duplicado variando mayúsculas/espacios y duplicado
de cuenta inactiva producen conflicto. Roles inválidos o cambios de campos no admitidos
se rechazan sin persistencia parcial. Actualizar con revisión vigente y luego obsoleta:
éxito con nueva revisión/ETag, después 412; no-op vigente conserva revisión y sesiones.

En dos pestañas/dispositivos de la cuenta objetivo, cambiar correo, perfil, estado y
contraseña: ninguna admisión nueva después del commit acepta sesiones anteriores.
Desactivar/reactivar conserva UUID/historia y no restaura cookies previas. Reset por otro
admin exige renovación y no devuelve contraseña anterior. Cambio propio no puede cambiar
perfil/otras cuentas; admin que modifica su propia cuenta debe ingresar de nuevo.

Usar conexiones independientes, barreras y resultado durable para estas carreras:

- Dos administradores se degradan/desactivan simultáneamente: una operación se rechaza
  y permanece al menos uno activo; repetir mezclando estado y perfil.
- Dos bootstraps en instalación vacía: una sola cuenta inicial; una repetición posterior
  rechaza sin nueva cuenta ni cambio de contraseña.
- Altas/ediciones simultáneas con correo equivalente: solo una identidad lo posee.
- Reset frente a login/cambio propio: no se confirma una contraseña antigua ni una sesión
  que conserve acceso tras invalidación.
- Actor pierde su rol mientras intenta editar otra cuenta: revalidación tras locks rechaza.
- Cerrar la sesión original mientras cambio propio/administrativo espera hashing o
  guardia: se rechaza la mutación aunque la cuenta conserve rol y auth_version.

Sin SQLite como evidencia de exclusión PostgreSQL. No aceptar resultados solo por conteos
en memoria o una ejecución secuencial.

## 4. Coordinación neutral sin notificaciones — traslado spec-006/T002

Ejecutar identidad con cero participantes y sin tablas de 008. Registrar participante
sintético: comprobar orden, atomicidad, rollback, nuevo conjunto de referencias y máximo
de tres reintentos. Un fallo no deja cuenta cambiada, ajustes parciales o eventos huérfanos.

La prueba real del participante de 008, nueva regla concurrente y ambos órdenes de
revocación frente al inicio durable corresponde a 008 antes del primer envío. No ejecutar
SMTP en transacciones ni declarar esa integración aceptada por este harness.

## 5. Administración del sistema e historial — US4, SC-006

Con 001/004 reales, admin modifica configuración válida, suministro/perfil BT4.3 y
boleta, ejecuta recálculo con revisión y consulta resultado/historia. Operador ve consultas
permitidas pero no lee ni modifica paneles administrativos. Para US4.4, intentar asignar
una misma fuente de medición a dos categorías mediante configuración001: rechazo sin
cambio de revisión ni persistencia parcial, conservando la última configuración válida.

La edición web de FR-019 comprende fuentes/correspondencias001 y suministro/perfiles
BT4.3 de004. Recepción mínima15min y conservación mínima12meses son restricciones
obligatorias de002 sin edición web en006. Verificarlas por separado mediante sus
puertos/validadores reales: recepción anticipada y retirada antes de12meses calendario
de protección se rechazan. No crear endpoints o formularios para modificar esos mínimos.

Cada cambio y solicitud administrativa denegada, incluidos GET, sin sesión y CSRF,
deja fecha, actor confiable/no autenticado, acción, destino y resultado. Revisar historial
con admin, denegarlo al Operador y verificar que no hay edición/borrado. Los actores
desactivados siguen referenciables. Forzar rollback/fallo de participante: no hay cambios
ni eventos aislados, pero el intento administrativo rechazado queda en nueva UoW.
Con DB caída responder 503, sin afirmar auditoría o confirmaciones inexistentes.

Probar publicación SFTP autorizada de 003 sin sesión humana. Se recibe por su contrato
técnico propio, no por las credenciales humanas. Si faltan esas capacidades externas,
mantener los escenarios integrales pendientes; no implementarlas dentro de identidad.

## 6. Navegación y personas — FR-010, SC-007

Playwright recorre ingreso, renovación, cuenta, consultas y administración por perfil;
prueba acceso directo, cierre/vencimiento en varias pestañas y restauración de página.
En el checkpoint US1, ingreso/cuenta reciben el contexto de `SessionProvider` montado
desde `frontend/src/app/layout.tsx`, antes de incorporar Navigation de US2; conservar
el export estático. US2 reutiliza ese contexto y conecta el helper de actividad a los
clientes reales: acciones de la persona envían interactive y sondeos envían background.
Comprobar limpieza de datos privados y retorno exclusivamente local seguro, carga/error
distintos y falta de secretos/datos en el build. Operador no recibe menús administrativos.

Con vista real de datos disponible, registrar diez tareas con personas representativas:
desde ingreso hasta la vista asignada a su perfil, sin ayuda. Al menos nueve terminan
en <=1 minuto. Registrar tiempos, éxitos y obstáculos sin credenciales. Sin personas
o resultados suficientes, SC-007 permanece pendiente aunque E2E pase.

## 7. HTTPS y operación — FR-024, SC-008

Validar cookies Secure con TLS local y después desde una red externa contra la dirección
pública real de VPS. Recorrer ingreso, consultas y descargas por ambos perfiles. Solicitudes
API por HTTP no procesan credenciales ni entregan datos; no hay sesión válida emitida.
Intentar falsificar X-Forwarded-Proto y alcanzar backend fuera del proxy no debe eludir el
control. Rechazar Origin/Referer ajenos o ausentes y comprobar no-store incluso en errores.
La infraestructura TLS es de 009; esta validación comprueba la política funcional de 006.

Ensayar recuperación en entorno de ensayo con admin activo sin credenciales conocidas:

```sh
uv run ecs-ec identity recover-admin --email admin@example.test --reason 'Ensayo de recuperación local'
```

Contraseña solo por TTY, renovación requerida, sesiones antiguas revocadas y auditoría
con actor de proceso. Cuenta inexistente/inactiva/Operador no se promueve ni reactiva por
esta herramienta. Revisar documentación de claves HMAC y su rotación, sin borrar esperas
activas ni restaurar sesiones revocadas. La restauración común de DB sigue siendo de 009.

## Evidencia de aceptación

Guardar en `validation/` de esta funcionalidad versiones/locks y comandos realmente
ejecutados, entorno sintético, resultados de suites/matriz, carreras, auditoría, revisión
UI y resultados de personas/HTTPS público. Usar referencias sintéticas; no cookies,
CSRF, contraseñas, hashes ni datos personales reales. Una guía o la existencia de archivos
no marca criterios de éxito, tareas o checklists como completados.
