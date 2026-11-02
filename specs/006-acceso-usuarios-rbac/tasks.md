---
description: "Tareas integrales de autenticación y permisos; conserva el traslado desde spec-008"
---

# Tasks: Autenticación y permisos por perfil

## Contexto compartido del proyecto (ECS-EC)

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [HTTP](contracts/http.md), [UI](contracts/ui.md),
[integraciones](contracts/integrations.md), [coordinación](contracts/coordination.md) y
[quickstart.md](quickstart.md).
**Contexto**: [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y
[constitución](../../.specify/memory/constitution.md).
**Selección**: `006-acceso-usuarios-rbac`; rama Git actual `develop`.
**Estado**: 69 de87 tareas completadas con ejecución local real;18 pendientes por gates
externos. Ver [aceptación parcial](validation/acceptance.md) y [dependencias pendientes](validation/integrations-pending.md). No se declara aceptación integral.

Plataforma009 posee scaffold, core, UoW, errores, reloj y auditoría/eventos. 006 posee
identidad y su fachada de seguridad; no implementa capacidades faltantes de otras specs.
El mecanismo común se consume, nunca se recrea en setup. Las seis entradas del borrador
se conservan mediante la matriz de trazabilidad al final, con IDs históricos explícitos.

**Pruebas**: Se incluyen las pruebas pedidas por los Independent Test, escenarios y SC de
spec.md, la validación constitucional y el plan/traslado que exige escribirlas antes de
capacidades nuevas. En cada bloque, escribirlas y comprobar el fallo esperado antes de
implementar; el checkpoint posterior exige éxito real. No crear tests que solo confirmen
que existen archivos. Documentar propósito y contratos de cada módulo, función, clase,
componente, prueba y script en el mismo cambio que añade/modifica su comportamiento.

## Format: `[ID] [P?] [Story] Description`

Todas las tareas usan `- [ ] TNNN [P?] [USn?] descripción con ruta`. IDs locales a esta
spec; en dependencias internas puede abreviarse el prefijo `spec-006/`. `[P]` permite
trabajo en archivos diferentes una vez satisfechos sus prerrequisitos explícitos; no
habilita ejecutar fases completas simultáneamente. No se ejecutan agentes o tareas por
el hecho de generar esta lista.

## Path Conventions

Rutas de código relativas a la raíz: `backend/src/ecs_ec/identity/`,
`backend/tests/{unit,integration,contract}/identity/`, `frontend/src/`,
`frontend/tests/`, `scripts/` y `deploy/README.md`. Enlaces documentales relativos al
archivo que los contiene. Una ruta propuesta no demuestra implementación existente.

## Gates externos por capacidad

| Gate | Capacidad y propietario | Cuándo se exige |
| --- | --- | --- |
| G0: Base | Scaffold, DB/UoW, reloj, errores, configuración, auditoría/eventos y composición reales de [009](../009-fundaciones-plataforma/plan.md), especialmente `backend/src/ecs_ec/core/unit_of_work.py` y `backend/src/ecs_ec/audit/events.py`. | Antes de T002 y cualquier implementación de 006. T001 registra faltantes sin construirlos. |
| G1: Consultas | Lectores y catálogo reales de [001](../001-visualizar-consumo-categorias/contracts/http.md), agregados de [002](../002-registro-retencion-consumo/contracts/http.md) y consultas de [004](../004-costos-tarifa-bt43/contracts/http.md). | Conexión T046 y aceptación integral US2. La política aislada de identidad no necesita esos productores. |
| G2: PDF | Captura/generación/descarga reales de [005](../005-generar-reportes-pdf/contracts/http.md) con sus fuentes de 001/002/004. | Conexión y aceptación de reportes en US2/US4; ningún stub acredita PDF funcional. |
| G3: Mantenimiento | Configuración/fuentes de 001, boletas/perfiles/suministro/recálculo de 004 y restricciones internas de recepción/retención de [002](../002-registro-retencion-consumo/plan.md). | Edición web de fuentes001/suministro/perfiles004 en US4; mínimos002 se verifican por sus puertos, sin edición web en006. |
| G4: Integración SFTP | Receptor/publicador técnico real de [003](../003-simulador-pas600-sftp/contracts/sftp-reception.md). | Escenario US4.7 y T077; no bloquea ingreso web ni cuentas. |
| G5: Emisión técnica | Emisor común real de [007](../007-observabilidad-externa/research.md), `backend/src/ecs_ec/observability/logging.py` y `tracing.py`. | Integración propia T082/T083; visores/recolectores no son requisito de disponibilidad funcional. |
| G6: Personas y VPS | Personas representativas y vista real de datos para SC-007; entorno de VPS/TLS de 009 y dirección pública para SC-008. | T085/T086 y aceptación final. No declarar aceptación con E2E o TLS local solamente. |

Los gates de G1 en adelante no bloquean las capacidades básicas US1/US3. Si falta un
proveedor, mantener pendiente su integración/aceptación y registrar propietario, contrato
y ruta en `validation/prerequisites.md`; no marcar una prueba omitida como éxito.
No hay gate sobre completar 008: su participante concreto y SMTP pertenecen a esa spec.

## Phase 1: Setup — preparar solo identidad

**Purpose**: Verificar G0 y ampliar el proyecto existente para 006, sin iniciar otra base.

- [X] T001 Verificar G0 contra `backend/src/ecs_ec/core/settings.py`, `backend/src/ecs_ec/core/clock.py`, `backend/src/ecs_ec/core/database.py`, `backend/src/ecs_ec/core/unit_of_work.py`, `backend/src/ecs_ec/core/errors.py`, `backend/src/ecs_ec/audit/events.py` y `backend/src/ecs_ec/main.py`; registrar capacidades reales/faltantes y su propietario009 en `specs/006-acceso-usuarios-rbac/validation/prerequisites.md`. Si falta la base, detener la implementación dependiente sin recrearla dentro de identidad; no exigir SMTP, 008 o visores.
- [X] T002 Con G0 disponible, añadir `argon2-cffi` y `email-validator` a `pyproject.toml`/`uv.lock`, comprobar instalación/build en CPython 3.14 y conservar el stack de plataforma; preparar `backend/src/ecs_ec/identity/__init__.py` y `frontend/src/components/identity/` sin crear otro proceso o scaffold. Documentar compatibilidad comprobada y costo inicial de hashing en `specs/006-acceso-usuarios-rbac/validation/dependencies.md`.
- [X] T003 Preparar `backend/tests/integration/identity/conftest.py` con PostgreSQL independiente, reloj inyectado, fábricas de ambos perfiles/estados, presesiones, dos administradores y barreras entre conexiones; sin endpoints públicos de fixtures ni dependencia de tablas008. Escribir `backend/tests/unit/identity/test_settings.py` para claves persistentes externas, origen/proxies y rechazo de modo HTTP público/producción antes de T004.
- [X] T004 Definir opciones propias en `backend/src/ecs_ec/identity/settings.py` y conectarlas a `backend/src/ecs_ec/core/settings.py` existente: origen público, proxies confiables, `IDENTITY_CSRF_KEY`, `IDENTITY_LOGIN_BUCKET_KEY`, sus IDs y concurrencia acotada de hashing. Actualizar `.env.example` solo con nombres/ejemplos no secretos; HTTP local requiere development explícito y loopback, y es inválido en producción. Mantener configuración común bajo propiedad009.

**Checkpoint**: G0 comprobado, dependencias de identidad reproducibles y fixtures aisladas.

## Phase 2: Foundational — entidades y contratos comunes de identidad

**Purpose**: Completar la base propia compartida por las cuatro historias. Prerrequisito:
T001–T004. T005–T008 pueden escribirse en paralelo; T009–T017 son posteriores a sus pruebas.

### Pruebas antes de la implementación

- [X] T005 [P] Escribir `backend/tests/integration/identity/test_models.py` para restricciones de todas las tablas del modelo: unicidad canónica entre activas/inactivas, roles/estados, FK RESTRICT, versiones positivas, singleton, digests únicos y UTC; verificar migración sin tablas de notificaciones ni duplicación de auditoría. Prerrequisito: fase 1.
- [X] T006 [P] Escribir `backend/tests/integration/identity/test_coordination.py` para cero participantes y participante sintético, registro inmutable/rangos inválidos, orden guardia→recursos previos→cuentas→sesiones→recursos posteriores, redescubrimiento/rollback y máximo tres intentos; comprobar que no hay commit/red dentro de participantes. Prerrequisito: fase 1.
- [X] T007 [P] Escribir `backend/tests/unit/identity/test_permissions.py` para toda la matriz fija de `contracts/integrations.md`, acción/rol/edificio desconocidos, sesión restringida, Programador/SFTP y perfiles manipulados; POST PDF es consulta y GET configuración es administración. Prerrequisito: fase 1.
- [X] T008 [P] Escribir `backend/tests/integration/identity/test_identity_audit.py` usando auditoría009 real para atomicidad de cuenta/revocación/participante/eventos, deduplicación por procedencia, payload saneado y rechazo en UoW nueva con actor confiable o no autenticado; DB caída no acredita durabilidad. Prerrequisito: fase 1.

### Implementación fundacional

- [X] T009 Definir `identity_account` en `backend/src/ecs_ec/identity/models.py` con `id` «UUID generado por la aplicación; identidad permanente.», `email` «Dirección normalizada para presentación administrativa.», `email_key` «Clave canónica no nula, UNIQUE entre todas las cuentas.», `role` «CHECK: `operador` o `administrador_tecnico`, exactamente uno.» y `status` «CHECK: `active` o `inactive`.». Añadir `password_hash` «PHC Argon2id con salt/parámetros; nunca se serializa ni audita.», `must_change_password` «Booleano no nulo; true en alta y restablecimiento.», `auth_version` «BIGINT positivo, inicialmente 1; invalida sesiones previas.» y `revision` «BIGINT positivo, inicialmente 1; concurrencia de la cuenta y procedencia de eventos.»; `created_at`, `updated_at`, `password_changed_at` «UTC; último cambio efectivo de cuenta/credencial.» y `created_by`, `updated_by` «Referencia confiable de cuenta o proceso bootstrap/recuperación.». Crear índices `email_key`, `(status,role,id)` y PK conforme al modelo; no tabla editable de roles. Depende de T005.
- [X] T010 Añadir `identity_session` en `backend/src/ecs_ec/identity/models.py`: `id` «UUID interno, distinto del secreto; no necesita publicarse.», `token_digest` «SHA-256 de 32 bytes aleatorios base64url; UNIQUE. No guardar bearer.», `account_id` «FK a cuenta, ON DELETE RESTRICT.», `auth_version` «Copia de la versión de cuenta al autenticar.», `mode` «`normal` o `password_change_required`; nunca lo determina el cliente.». Aplicar a `created_at`, `last_activity_at` «UTC; actividad inicialmente igual al ingreso.», `absolute_expires_at` «`created_at + 8 horas`, inmutable.», `idle_expires_at` «Inicialmente `created_at + 30 minutos`, nunca mayor al límite absoluto.», `revoked_at`, `revocation_code` «Nulos mientras no se revoque; código acotado, sin texto libre.» y `csrf_key_id` «Versión de la clave externa para derivar CSRF; no es la clave.». Crear índices de digest, cuenta/revocación y expiración; depende de T009.
- [X] T011 Completar `backend/src/ecs_ec/identity/models.py` con presesión `id` UUID, «`token_digest` único», «`expires_at=created_at+10min`», «`consumed_at|null`», `created_at` y `csrf_key_id`, «Sin `account_id`, rol o permiso.»; bucket con «`bucket_key` PK», HMAC de correo/origen con longitudes explícitas, «No tiene FK de cuenta», `failed_at` «lista tipada de instantes UTC de los fallos de la ventana móvil; máximo cinco.», «`blocked_until|null`, `updated_at`, `key_id`» y UTC sin correo/IP/contraseña almacenados. Añadir guardia «Una sola fila `id=1` creada por migración.» no expuesta/borrable. Depende de T010.
- [X] T012 Crear `backend/migrations/versions/identity_initial.py` enlazada al head real de Alembic, solo para las cinco tablas de T009–T011 e inserción de guardia; no recrear core/audit, usar timestamptz y restricciones/índices del modelo y probar upgrade sobre base009 real en `backend/tests/integration/identity/test_models.py`. Conservar «Cuentas se desactivan y conservan permanentemente para referencias históricas; no hay DELETE ni cascada.».
- [X] T013 Definir en `backend/src/ecs_ec/identity/schemas.py` los enums, principal interno y comandos/resultados tipados de cuenta, sesión y coordinación; validar campos adicionales y separar proyecciones públicas sin hash/digest/bearer. Copiar los campos obligatorios/nullables de `data-model.md`; actor de servidor, no del cuerpo, y `IdentityMutation` saneada sin hashes/tokens para participantes. Depende de T009–T012.
- [X] T014 Implementar repositorio/proyecciones en `backend/src/ecs_ec/identity/repository.py` y adaptador funcional en `backend/src/ecs_ec/identity/audit.py`, consumiendo UoW y `FunctionalAudit`/`EventWriter` de 009; registrar `identity.changed` y `administration.changed` por cuenta/revisión según el modelo, sin emails/secretos. Conservar «actor_kind=account|process|unauthenticated», resultado tipado y referencias; denegaciones no son cambios de cuenta y no se duplican entre capas por operation_ref. Depende de T008 y T013.
- [X] T015 Implementar registro/protocolo neutral en `backend/src/ecs_ec/identity/coordination.py`: `discover`, `lock`, `revalidate`, `apply`, cero participantes, registro congelado por composición y orden de `contracts/coordination.md`. Cambios de conjunto exigen rollback completo/redescubrimiento, «Máximo tres intentos internos», después 409 `identity_coordination_retry`; nunca importar notifications ni hacer SMTP/HTTP/commit del participante. Depende de T006 y T012–T014.
- [X] T016 Implementar orquestación común de mutaciones en `backend/src/ecs_ec/identity/services.py`: guardia FOR UPDATE, recursos previos, cuentas por UUID, sesiones afectadas y original del actor por UUID y recursos posteriores; revalidar cuenta/rol/revisión y sesión original tras locks con reloj nuevo, no timestamp de inicio. Comprobar estado posterior con al menos un admin activo; aplicar incremento de versiones, revocación, participantes y auditoría en una sola UoW; rechazos registran intento después de rollback. Exponer operaciones internas para bootstrap/renovación y futuras altas/ediciones sin endpoints todavía; depende de T014/T015.
- [X] T017 Implementar catálogo fijo y autorización por defecto denegada en `backend/src/ecs_ec/identity/permissions.py`, pasando T007; no roles personalizados, permisos de cliente ni autorización derivada del verbo HTTP. Permitir en restringida solo `session.read`, `session.logout`, `account.password.change`; principal técnico no es cuenta humana y edificio debe ser el configurado. Ejecutar T005–T008 con el protocolo ya implementado y registrar resultados en `specs/006-acceso-usuarios-rbac/validation/foundations.md`; pruebas de endpoints/sesión concretos continúan en US1/US3.

**Checkpoint**: Tablas/puertos y mutación transaccional neutral comprobados sobre PostgreSQL,
con política fija y auditoría009. Todas las historias dependen de este bloque.

## Phase 3: User Story 1 — Ingresar y salir con una cuenta identificada (P1, MVP)

**Goal**: Ingreso/salida, renovación, expiración y espera local sin identidad remota.
**Independent Test**: Con cuenta activa de cada perfil y cuentas inactivas, verificar
credenciales, renovación restringida, acceso directo rechazado, cierre y límites; US1.8
público se completa en T086. Prerrequisito: fase 2, sin exigir G1–G5.

### Pruebas de US1 antes de implementar

- [X] T018 [P] [US1] Escribir `backend/tests/unit/identity/test_credentials.py` para correo canónico/IDNA/casefold sin quitar puntos/`+`, `.test` solo local, contraseñas Unicode de 15/128 y rechazo de 14/129, espacios/mayúsculas exactos, PHC Argon2id sin reversibilidad y nueva contraseña distinta. Depende de fase 2.
- [X] T019 [P] [US1] Escribir `backend/tests/contract/identity/test_auth_api.py` para las cinco rutas `/auth/csrf`, `/auth/login`, `/auth/session`, `/auth/logout`, `/auth/password`, cuerpos y SessionView de `contracts/http.md`; CSRF también en login, Origin/Referer, cookies, no-store y errores 401/403/422/429/503 sin secretos. Depende de fase 2.
- [X] T020 [P] [US1] Escribir `backend/tests/integration/identity/test_login_wait.py` para ventana móvil/cinco fallos/espera15min, quinto fallo429, desconocidas/inactivas equivalentes, éxito limpia, otros orígenes, reinicio y solicitudes paralelas; cubrir bucket→preauth→cuenta, presesión consumida por un solo login y versión cambiada durante Argon2. Depende de fase 2.
- [X] T021 [P] [US1] Escribir `backend/tests/integration/identity/test_identity_boundaries.py` para sesiones opacas/restringidas, expiración exacta30min/8h, cierre de una sesión, no renovación por introspección/polling, no resurrección por concurrencia y reloj nuevo después de locks; cuenta/Programador/SFTP/edificio ajenos no autorizan. Con ingreso al minuto0, GET interactivo autorizado al29 mueve el límite inactivo al59; solo sondeos background vence al30; actividad continua no supera8h y `/auth/session` nunca renueva, incluso con interactive. Depende de fase 2; amplía en US3 la invalidación por APIs de cuentas reales.
- [X] T022 [P] [US1] Escribir `frontend/tests/unit/identity/SessionProvider.test.tsx`, `frontend/tests/unit/identity/AccessForms.test.tsx` y `frontend/tests/unit/identity/Activity.test.ts` para carga/error, 401/403/429, renovación, limpieza de secretos, retorno seguro, BroadcastChannel sin datos personales y pageshow sin datos privados previos. Probar montaje de ingreso/cuenta bajo el proveedor desde el layout sin Navigation de US2 y `sessionActivityHeaders(activity)` con interactive/background y valor predeterminado background antes de T033. Depende de fase 2.
- [X] T023 [P] [US1] Escribir `backend/tests/integration/identity/test_bootstrap.py` para TTY sin eco/argumentos de contraseña, instalación vacía, repetición/concurrencia con una sola cuenta y actor de proceso/auditoría/renovación; no exigir tablas008. Depende de fase 2.

### Implementación de US1

- [X] T024 [US1] Implementar correo y hashing en `backend/src/ecs_ec/identity/credentials.py`: «320 caracteres Unicode antes de validación» y «15..128 puntos de código, espacios incluidos, UTF-8 exacto, sin clases obligatorias» del modelo. Usar normalización común para alta/edición/login/throttle, `check_deliverability=False`, `test_environment=True` solo local y parámetros Argon2id 65536KiB/t3/p4/salt16/hash32 de research; hash fuera del bucle asíncrono/locks con concurrencia acotada, hash ficticio para desconocidas. Depende de T018–T023.
- [X] T025 [US1] Implementar presesión y derivación HMAC CSRF en `backend/src/ecs_ec/identity/security.py`: cookie `ecs_ec_preauth`, expiración10min no prolongable, GET reutiliza contexto vigente, namespaces separados de sesión, token solo en respuesta no-store y comparación segura de `X-CSRF-Token`; consumo de presesión solo al emitir sesión con bearer independiente. Depende de T019/T020/T024.
- [X] T026 [US1] Implementar política de espera en `backend/src/ecs_ec/identity/sessions.py`: fallos `(ahora-15min,ahora]`, eliminar «instantes `<=now-15min`», quinto fija «`blocked_until=now+15min`», durante «`now<blocked_until`» no autenticar/añadir/extender, vencimiento/success limpian. Crear/bloquear bucket atómicamente, confirmar rechazos y revalidar estado/hash/versión tras Argon2 y locks con reloj nuevo; correo inválido usa clave determinista y rechazo general. Depende de T020/T024/T025.
- [X] T027 [US1] Completar emisión/resolución/revocación/actividad en `backend/src/ecs_ec/identity/sessions.py`: token aleatorio32bytes y digest, cuenta activa/perfil reconocido/auth_version igual, «`now < absolute_expires_at` y `now < idle_expires_at`». La igualdad vence; actualizar actividad condicionalmente sin resucitar ni retroceder y nunca extender8h; `X-Session-Activity` default background e introspección no renuevan. UoW breve sin retener cuenta al módulo consumidor; cierre revoca solo la sesión utilizada. Depende de T021/T026.
- [X] T028 [US1] Completar `backend/src/ecs_ec/identity/security.py` y fachada `backend/src/ecs_ec/core/security.py`: resolver sesión/permiso de T017/T027, exigir CSRF/origen en todos los métodos mutantes, HTTPS efectivo/proxies confiables, no-store aun en errores y cookies HttpOnly/SameSite=Lax/Path=/host-only/Secure bajo TLS. Reutilizar core/errors009 y rechazar transporte inseguro antes de credenciales; no sustituir implementación de core. Depende de T025/T027.
- [X] T029 [US1] Implementar cambio propio en `backend/src/ecs_ec/identity/services.py`: contraseña actual, nueva distinta, versión/hash capturados antes de Argon2 y revalidados internamente sin If-Match público; conservar perfil/cuenta, renovación false, revision/auth_version+1 y revocación total, incluida sesión utilizada. Revalidar sesión original tras guardia/locks, incluso logout sin cambio de auth_version; éxito exige nuevo ingreso. Depende de T016/T024/T027/T028.
- [X] T030 [US1] Implementar `bootstrap-admin` en `backend/src/ecs_ec/cli.py` y registrar `ecs-ec` en `pyproject.toml`: email admisible, contraseña dos veces por getpass/TTY sin argumentos/logs, solo cero cuentas bajo guardia, administrador activo y renovación true, auditoría/eventos atómicos. No habilitar acceso normal hasta existir admin; prueba concurrente T023 debe pasar. Depende de T016/T024/T029.
- [X] T031 [US1] Implementar DTOs y las cinco rutas de autenticación en `backend/src/ecs_ec/identity/schemas.py` y `backend/src/ecs_ec/identity/api.py`, pasando T019: SessionView sin secretos, 204 para cambio/cierre, borrado de cookies, 401 general idéntico, 429 con Retry-After sin conteo y errores por campo saneados. Restringida solo introspección mínima/renovación/cierre; no registro público ni parámetros de rol/actor. Depende de T028–T030.
- [X] T032 [US1] Registrar router, fachada de seguridad y registro neutral congelado en `backend/src/ecs_ec/main.py` existente; enlazar auditoría de denegaciones administrativas tempranas en `backend/src/ecs_ec/identity/security.py`, por actor resuelto o unauthenticated, sin prolongar actividad ni persistir secretos. Mantener errores comunes y guardas por defecto en rutas protegidas, sin fabricar módulos ausentes; cambios de composición secuenciales. Depende de T031.
- [X] T033 [US1] Implementar cliente tipado en `frontend/src/lib/api/session.ts` para las cinco rutas, cookies del mismo origen, CSRF solo en memoria, estados normal/restringido, Retry-After y `Problem`; no localStorage, token en URL ni datos privados en build. Exportar `sessionActivityHeaders(activity)` que genera `X-Session-Activity: interactive|background`, con valor predeterminado background, para reutilizar en clientes de consultas. Las llamadas automáticas a `/auth/session` usan background y nunca prolongan actividad. Fijar interfaz de suscripción/limpieza para componentes. Depende de T031/T032 y pruebas T022.
- [X] T034 [US1] Implementar `frontend/src/components/identity/SessionProvider.tsx` con interfaz T033 y montarlo como componente cliente desde `frontend/src/app/layout.tsx`, envolviendo las páginas de ingreso y cuenta y conservando la exportación estática: comprobación runtime antes de datos, revalidación al activar pestaña/pageshow, limpieza/suscripción de estado privado, BroadcastChannel sin cuenta/token y manejo distinto de 401/403/red; no sondeos que renueven sesión. Completar el montaje antes de T035/T036/T039, sin depender de Navigation de US2. Depende de T033 y pruebas T022.
- [X] T035 [US1] Crear `frontend/src/components/identity/LoginForm.tsx` y `frontend/src/app/ingreso/page.tsx` con labels/foco/teclado/autocomplete, presesión antes de submit, mismo mensaje fallido y espera429; retorno solo a rutas relativas registradas/query validada, sin `//`, esquemas, backslashes o bucles. Fallback `/cuenta/` aislado y `/consumption/` solo cuando exista el módulo. Depende de T034.
- [X] T036 [US1] Crear `frontend/src/components/identity/PasswordForm.tsx` y `frontend/src/app/cuenta/page.tsx` para cambio propio/renovación/cierre, sin edición de rol; confirmar nueva contraseña localmente, permitir pegar/gestor y espacios, vaciar secretos tras cada envío y exigir reingreso tras cambio. Sesión restringida solo muestra estas acciones. Depende de T034/T035.
- [X] T037 [US1] Crear `scripts/seed_identity_reference.py` para fixtures explícitamente development/test y DB aislada, rechazando producción y leyendo credenciales de entrada protegida sin imprimirlas; cuentas por perfil/estado y revisión conocida sin sustituir bootstrap operativo. Documentar propósito/errores/efectos y preparación en `specs/006-acceso-usuarios-rbac/quickstart.md`. Depende de T030–T036.
- [X] T038 [US1] Ejecutar T018–T023 y suites fundacionales sobre PostgreSQL real; registrar versiones, comandos, tiempos/memoria de Argon2 y límite de concurrencia medido, bordes de tiempo/reinicio/locks y ausencia de secretos en `specs/006-acceso-usuarios-rbac/validation/authentication.md`. No dar aceptación de VPS por resultados locales; depende de T037.
- [X] T039 [US1] Escribir y ejecutar el tramo US1 de `frontend/tests/e2e/identity.spec.ts` sobre el monolito local real con SessionProvider ya montado desde el layout de T034 y contexto disponible en ingreso/cuenta antes de incorporar Navigation de US2: ambos perfiles, renovación inicial, CSRF/cookies, URLs directas, cierre, expiración y pestañas; revisar build exportado sin datos privados y verificar con TLS local cookie Secure. Registrar resultados en `specs/006-acceso-usuarios-rbac/validation/access-ui.md`; depende de T038.
- [X] T040 [US1] Ajustar comandos reales de arranque, bootstrap, cuentas de prueba y validación US1 en `specs/006-acceso-usuarios-rbac/quickstart.md`; documentar el alcance local SC-001/SC-004 y dejar US1.8/SC-008 público pendiente de T086, sin atribuir los SC integrales de otras historias al harness de identidad. Depende de T039.

**Checkpoint**: Acceso local y renovación/cierre reales, sin dependencia de consumidores
ni proveedores de datos. MVP de identidad: fases 1–3; no aceptación funcional completa.

## Phase 4: User Story 2 — Consultar información como Operador (P1)

**Goal**: Consultas de consumo/historial/costos/boletas y PDF con permiso de lectura, sin
mantenimiento. **Independent Test**: Con identidad real, recorrer matriz/URLs directas
como Operador y Administrador, generar/descargar PDF real y denegar cambios sin datos
administrativos ni efectos. Prerrequisito US1; G1/G2 para conexión/aceptación integral.

### Pruebas de US2 antes de integrar

- [X] T041 [P] [US2] Escribir `backend/tests/contract/identity/test_permission_matrix.py` para las acciones/rutas de `contracts/integrations.md` con sin sesión/Operador/Admin/restringida: accesos directos, rol/actor manipulados, objeto administrativo no revelado y acción desconocida denegada. Distinguir política aislada de proveedores reales y no crear endpoints de negocio ficticios; depende de US1.
- [ ] T042 [P] [US2] Escribir `backend/tests/integration/identity/test_read_integrations.py` contra interfaces reales001/002/004: siete categorías, detalle/agregados, costos/boletas/referencias visibles, mismo permiso para ambos perfiles y filtros que no modifican mediciones/tarifas/boletas/configuración. Preparar ejecución con G1 y registrar cualquier proveedor ausente, sin aceptación por skip; depende de US1.
- [ ] T043 [P] [US2] Escribir `backend/tests/integration/identity/test_report_access.py` con contrato005: POST PDF permitido como lectura con CSRF, descarga y replay idempotente vuelven a autorizar; después de cierre/desactivación/versiones nuevas no hay bytes ni metadatos privados. La captura REPEATABLE READ no concede permisos antiguos; ejecución requiere G2. Depende de US1.
- [X] T044 [P] [US2] Escribir `frontend/tests/unit/identity/Navigation.test.tsx` para menús por permisos, falta de admin para Operador, enlaces solo a módulos presentes, carga/403/renovación y limpieza de datos de vistas registradas al vencer/cerrar; no asumir permisos desde cache. Depende de US1.

### Integración de US2

- [X] T045 [US2] Exponer en `backend/src/ecs_ec/identity/services.py` `Identity.resolve_session`, `Identity.authorize(principal, action, building_id)` y `Identity.require_report_access` sobre política/sesión existentes: principal de esta petición, edificio confiable, lectura READ COMMITTED fresca, sin locks retenidos ni permisos obtenidos de una captura vieja; autorizar antes de replay o entrega. Depende de T041–T044.
- [ ] T046 [US2] Con G1/G2, enlazar dependencias de autorización actuales de `backend/src/ecs_ec/core/security.py` en las rutas propietarias existentes `backend/src/ecs_ec/consumption/router.py`, `backend/src/ecs_ec/costs/api.py` y `backend/src/ecs_ec/reports/api.py`: consultas permitidas, acceso administrativo siempre reservado y nueva comprobación de PDF/replay. Solo conectar la interfaz006; preservar cálculos/validaciones/idempotencia de sus propietarios y registrar faltantes, sin reimplementar módulos. Depende de T045; coordinar archivos secuencialmente con specs001/002/004/005.
- [X] T047 [US2] Crear `frontend/src/components/identity/Navigation.tsx` e integrar `frontend/src/app/layout.tsx` existente reutilizando SessionProvider ya montado por T034, sin duplicarlo ni posponer su montaje a esta historia; permisos runtime y módulos registrados: consultas para ambos perfiles, admin solo para Administrador normal y cuenta/cierre para ambos; no enlaces a capacidades ausentes ni panel técnico de Programador. Depende de T044/T045 y T034.
- [ ] T048 [US2] Con G1/G2, conectar suscripciones de limpieza de `frontend/src/components/identity/SessionProvider.tsx` y `frontend/src/lib/api/session.ts` con vistas privadas ya existentes de consumo/costos/reportes, respetando sus propietarios; conectar sus clientes a `sessionActivityHeaders(activity)` de T033: navegación de datos, Consultar, Actualizar y cambios de filtros iniciados por la persona envían interactive; sondeos y revalidaciones automáticas envían background. `/auth/session` nunca prolonga sesión, incluso con interactive, y 401/403 no se convierten en listas vacías. Verificar limpieza también tras pageshow/reactivación de pestaña y retorno seguro a PDF. Depende de T046/T047 y T033.
- [ ] T049 [US2] Ejecutar T041–T044 con proveedores G1/G2 reales y registrar cada combinación de matriz y referencia de datos/estado antes/después en `specs/006-acceso-usuarios-rbac/validation/operator-matrix.md`; comprobar SC-002/SC-003, sin permiso de escritura para PDF, y SC-004 en nueva descarga. Con faltantes conservar pendiente, no aceptar con stubs. Depende de T048.
- [ ] T050 [US2] Ampliar y ejecutar `frontend/tests/e2e/identity.spec.ts` con consultas reales por ambos perfiles, filtros, generación/descarga de PDF, accesos directos administrativos y solicitudes de boleta/tarifa/recálculo denegadas al Operador; con reloj interno de pruebas y red observable, comprobar interactive en acciones de la persona y background en sondeos: consulta al minuto29 prolonga hasta59, solo sondeos vence al30, introspección nunca renueva y ninguna actividad supera8h o revive sesión vencida. Registrar evidencia de navegación, tiempos y ausencia de cambios/filtraciones en `specs/006-acceso-usuarios-rbac/validation/operator-ui.md`. Depende de T049; sin endpoint público de avance de reloj.

**Checkpoint**: US2 completa solo con G1/G2 reales y matriz/descargas verificadas. Si faltan,
US3 puede avanzar sobre US1: no convertir esos proveedores en gate global de cuentas.

## Phase 5: User Story 3 — Administrar cuentas y sus perfiles (P1)

**Goal**: Alta/edición/desactivación/reactivación/reset con identidad estable, revocación y
al menos un admin activo. **Independent Test**: Admin gestiona ambos perfiles, prueba
unicidad/ETag, invalidación en varios dispositivos y dos retiros de admin simultáneos.
Prerrequisito US1 y fundamentos; no requiere completar US2/G1/G2.

### Pruebas de US3 antes de implementar

- [X] T051 [P] [US3] Escribir `backend/tests/contract/identity/test_accounts_api.py` para GET lista/detalle, POST alta, PUT edición y POST reset: admin exclusivo incluso GET, campos adicionales rechazados, ETag/If-Match 412/428, correo409, no DELETE/registro público y ningún hash/secretos en AccountView; reset propio remite a cambio personal. Depende de US1.
- [X] T052 [P] [US3] Escribir `backend/tests/integration/identity/test_account_concurrency.py` con conexiones/barreras PostgreSQL: correo equivalente concurrente, dos admins degradándose/desactivándose, actor pierde rol o cierra sesión esperando locks, tiempo cruza vencimiento, reset frente a login/cambio propio, no-op y revocación total en edición/reactivación. Depende de US1.
- [X] T053 [P] [US3] Escribir `frontend/tests/unit/identity/AccountAdministration.test.tsx` para listado/alta/edición/reset, 409/412/503, limpieza de contraseñas y campos no secretos conservados, cuenta propia/reingreso y ausencia de eliminar usuarios o recuperar contraseña anterior. Depende de US1.
- [X] T054 [P] [US3] Escribir `backend/tests/unit/identity/test_recipient_resolution.py` para UUID, estado/perfil/renovación/permisos actuales, versión y correo vigente; sin sesión humana ni tablas008, sin aceptar identidad técnica como cuenta. No probar SMTP ni un participante concreto. Depende de US1.

### Implementación de US3

- [X] T055 [US3] Añadir DTOs de cuentas en `backend/src/ecs_ec/identity/schemas.py`: AccountView `{id,email,role,status,must_change_password,revision,created_at,updated_at}` sin campos secretos; roles/estados fijos y validación de correo/contraseña de T024. Listados «`limit` 1..100, 25 por defecto», cursor ligado a filtros y orden `(created_at,id)`; campos de credencial solo write-only y errores sin valores recibidos. Depende de T051–T054.
- [X] T056 [US3] Implementar alta administrativa en `backend/src/ecs_ec/identity/services.py` con correo canónico único aun inactivo, perfil/estado explícitos, hash y renovación obligatoria, guardia y auditoría/eventos atómicos de T016; no autoasignación ni actor recibido del cliente. Traducir conflicto de índice a409 sin guardar cuenta parcial. Depende de T055.
- [X] T057 [US3] Implementar edición/desactivación/reactivación en `backend/src/ecs_ec/identity/services.py` con If-Match vigente bajo locks, no-op sin nueva revisión/revocación y cambio efectivo con revision/auth_version+1 y todas las sesiones revocadas. Proteger último admin, revalidar sesión original/rol y reloj después de esperar; conservar UUID/referencias históricas y nunca revivir sesiones al reactivar. Depende de T052/T056.
- [X] T058 [US3] Implementar reset por otro administrador en `backend/src/ecs_ec/identity/services.py`: If-Match, hash nuevo fuera de locks, renovación true, revocación total y eventos/auditoría sin revelar credencial anterior; reset de sí mismo422 `use_own_password_change`, cambio propio ya implementado en T029. Revalidar versión y actor después de hashing; depende de T057.
- [X] T059 [US3] Implementar `Identity.resolve_recipient` en `backend/src/ecs_ec/identity/services.py` usando proyección interna del repositorio: estado, correo vigente, perfil, auth_version/revisión y elegibilidad por todos los permisos solicitados, sin cookies ni sesión humana. Cuenta inactiva/perfil inválido/renovación pendiente resulta inelegible; no añadir endpoint público ni importar008. Depende de T054/T058.
- [X] T060 [US3] Añadir las cinco operaciones de cuentas en `backend/src/ecs_ec/identity/api.py` con cuerpos/ETag/Location/status de `contracts/http.md`, autenticación/admin antes de resolver objeto, CSRF/origen y precondiciones dentro del servicio; cambios propios borran cookie, errores no incluyen cuerpos y confirmación ambigua503 exige recarga. Sin DELETE ni contraseña en respuestas; depende de T055–T059.
- [X] T061 [US3] Implementar tipos, cliente de listado/alta/edición/reset y conservación de ETag en `frontend/src/lib/api/identity.ts` sobre cliente006, fijando props comunes de tabla/formulario; 409/412/428/503 distinguidos, credenciales solo durante submit y no en logs/storage. Depende de T060.
- [X] T062 [P] [US3] Crear `frontend/src/components/identity/AccountTable.tsx` con filtros/perfil/estado/renovación, paginación y estados carga/vacío/error, acciones restringidas y referencias de cuenta; no hashes, passwords o borrado. Puede realizarse junto con T063 después de T061/T053, sin editar cliente o página compartidos.
- [X] T063 [P] [US3] Crear `frontend/src/components/identity/AccountForm.tsx` con alta/edición/reset, revisión recibida, confirmación local, limpieza de secretos y avisos de renovación/invalidación/reingreso; ante412 pedir recargar y ante409 último admin/correo informar sin afirmar cambio. Puede realizarse junto con T062 después de T061/T053.
- [X] T064 [US3] Integrar tabla/formulario en `frontend/src/app/administracion/usuarios/page.tsx` con guard runtime, solo admin normal, sin datos en export y sin credenciales guardadas tras éxito/fallo; cambios propios limpian sesión y redirigen a ingreso. Depende de T062/T063.
- [X] T065 [US3] Ejecutar T051–T054 y ampliar `backend/tests/integration/identity/test_identity_boundaries.py` con las APIs reales de edición/reset/desactivación/reactivación, dos dispositivos y sesión original revocada mientras espera; registrar resultados de unicidad/último admin/atomicidad/SC-004/SC-005 en `specs/006-acceso-usuarios-rbac/validation/accounts.md`. Depende de T064; no acreditar carreras con SQLite o ejecución secuencial.
- [X] T066 [US3] Ampliar y ejecutar `frontend/tests/e2e/identity.spec.ts` para alta de ambos perfiles, correo duplicado, cambios, renovación/reset y cuenta propia; verificar UI ante conflicto/errores y sesiones viejas inútiles. Registrar comandos/evidencia y referencias saneadas de auditoría en `specs/006-acceso-usuarios-rbac/validation/accounts-ui.md`; depende de T065 y coordinar secuencialmente con cambios US2 al mismo archivo.

**Checkpoint**: Gestión de cuentas completa y concurrente sobre G0+US1; no depende de
notificaciones. El historial consultable de todos los cambios se presenta en US4.

## Phase 6: User Story 4 — Administrar el sistema con trazabilidad (P2)

**Goal**: Mantenimiento permitido y consulta de auditoría funcional, conservando reglas de
cada módulo y separación técnica. **Independent Test**: Admin consulta/genera PDF, cambia
configuración/boleta/perfil válidos, rechaza valores inválidos sin cambios y revisa actor,
fecha, acción, destino/resultado; comprobar SFTP sin sesión humana.
Prerrequisitos: US1/US3 para historial propio; G1–G4 y US2 para aceptación integral.

### Pruebas de US4 antes de integrar

- [X] T067 [P] [US4] Escribir `backend/tests/contract/identity/test_administration_history_api.py` para GET historial admin-only, filtros/cursor/corte, actor account/process/unauthenticated, referencias/revisiones/resultados, no-store y ausencia de edición/borrado o secretos; fuente real audit009. Depende de US1/US3.
- [ ] T068 [P] [US4] Escribir `backend/tests/integration/identity/test_system_administration.py` para configuración001 y suministro/perfiles/boletas/recálculo004 reales: admin hereda lecturas, Operador denegado incluso GET, validaciones/versiones/último estado y auditoría conservados; para US4.4, intentar asignar una misma fuente a dos categorías mediante configuración001 y comprobar rechazo sin cambio de revisión ni persistencia parcial. Por separado, verificar mediante puertos/validadores reales002 el rechazo de recepción anticipada a15min y retirada antes de12meses calendario de protección, sin configurar esos mínimos ni crear edición web/API nueva. Ejecución requiere G1/G2/G3, sin aceptación basada en dobles; depende de US1/US3.
- [ ] T069 [P] [US4] Escribir `backend/tests/integration/identity/test_technical_identity_separation.py` para publicación003 técnicamente válida sin cookie humana, cookie humana sin permiso SFTP y credenciales Programador sin permisos funcionales; ejecución de SFTP real requiere G4 y aceptación del entorno técnico real corresponde a007. Depende de US1/US3.
- [X] T070 [P] [US4] Escribir `frontend/tests/unit/identity/AdministrationHistory.test.tsx` para filtros/paginación/zona explícita, proceso/no autenticado/cuenta desactivada, carga/vacío/error y guard de admin; navegación solo a configuraciones registradas y nunca a consola técnica. Depende de US1/US3.

### Implementación e integración de US4

- [X] T071 [US4] Implementar consulta de auditoría común en `backend/src/ecs_ec/identity/history.py` y proyección del repositorio sin otro almacén: fecha/actor/acción/destino/revisión/resultado saneados, rango `[from,to)` con inicio<fin, últimas24h por defecto, `(occurred_at,id)` descendente y corte fijo entre páginas. Aplicar `limit`1..100/default25, referencias históricas estables y permisos actuales; depende de T067–T070.
- [X] T072 [US4] Añadir AdministrationEntry y GET `/identity/administration-history` en `backend/src/ecs_ec/identity/schemas.py` y `backend/src/ecs_ec/identity/api.py`: «Kind `account|process|unauthenticated`; result `allowed|denied|rejected`», `account_id|null`, `process_code|null`, destino `id|null`, `revision|null` según HTTP; cursor/filtros inválidos422, admin normal exclusivo y fuente inaccesible503, nunca vacío ficticio. Depende de T071.
- [X] T073 [US4] Extender `frontend/src/lib/api/identity.ts` para filtros/cursores/corte e historial tipado de T072 sin payloads originales; mantener cliente de cuentas y limpiar resultados al invalidar sesión. Depende de T072 y coordinar escritura después de T061.
- [X] T074 [US4] Crear `frontend/src/components/identity/AdministrationHistory.tsx` y `frontend/src/app/administracion/historial/page.tsx` sobre T073: consulta de solo lectura, fecha con zona explícita, actor/destino/revisión/resultado, filtros y paginación; sin acciones de edición/borrado ni datos privados exportados. Pasar T070; depende de T073.
- [ ] T075 [US4] Con G3, completar conexión de acciones administrativas006 desde `backend/src/ecs_ec/core/security.py` a `backend/src/ecs_ec/consumption/router.py` y `backend/src/ecs_ec/costs/api.py`, y enlaces runtime de `frontend/src/components/identity/Navigation.tsx` a fuentes/correspondencias001 y suministro/perfiles BT4.3 de004 ya implementados por sus propietarios. Preservar validadores, versiones y autor; mínimos de recepción15min/conservación12meses son restricciones obligatorias de002 sin edición web en006; no crear paneles ficticios, reglas de tarifa ni API de mantenimiento002. Depende de T074 y coordinar secuencialmente con T046/T047 y los propietarios.
- [ ] T076 [US4] Ejecutar T067/T068 y auditoría T008 con cambios reales y denegaciones GET/POST/PUT por falta de sesión/permiso/CSRF/origen, actor confiable y unauthenticated para inválida; verificar un solo registro por intento, rollback sin eventos huérfanos, conservación>=12meses calendario y DB caída503 sin afirmar durabilidad. Registrar comparaciones de estado/versiones/historial para SC-006 en `specs/006-acceso-usuarios-rbac/validation/system-administration.md`; requiere G1/G2/G3 y US2/US3.
- [ ] T077 [US4] Con G4 disponible, ejecutar T069 usando receptor/publicador003 reales sin sesión humana; demostrar aislamiento de cookies/SFTP y que Programador no adquiere permisos web por credencial técnica. Registrar comandos/resultados de US4.7/FR-023 en `specs/006-acceso-usuarios-rbac/validation/technical-separation.md`; sin esos proveedores, conservar pendiente y no implementar SFTP/gateway007 dentro de006.
- [ ] T078 [US4] Ampliar y ejecutar `frontend/tests/e2e/identity.spec.ts` con configuración/boleta/perfil/recálculo e historial reales, admin y Operador, valores inválidos sin cambios y actor/resultado correctos; registrar evidencia en `specs/006-acceso-usuarios-rbac/validation/administration-ui.md`. Requiere T074–T076, G1/G2/G3 y UI de proveedores; archivo compartido se modifica después de T050/T066.

**Checkpoint**: Historial propio verificable sobre009/identidad; US4 integral exige
mantenimiento/PDF/SFTP reales. Sin ellos la historia no se declara aceptada.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Operación y evidencia transversal, sin sustituir checkpoints previos.

- [X] T079 Escribir `backend/tests/integration/identity/test_session_maintenance.py` antes de T080 para limpieza acotada sin revivir sesiones/borrar historia, cuentas referenciables, retirada de clave CSRF y rotación de bucket que preserva espera activa. Usar reloj inyectado/locks PostgreSQL y cuenta/perfil reales; depende de US1/US3, sin exigir G1–G4.
- [X] T080 Implementar limpieza/rotación de estado de acceso en `backend/src/ecs_ec/identity/maintenance.py` y registrar su ciclo interno en `backend/src/ecs_ec/main.py` existente: presesiones consumidas/vencidas y sesiones revocadas/vencidas «tras 24 horas»; buckets solo sin espera/fallos de ventana y «24 horas sin actualización». Conservar cuentas/auditoría, validez independiente del job, clave CSRF retirada exige ingreso y bucket conserva clave anterior «al menos 30 minutos» migrando estado bajo lock sin borrar esperas. Pasar T079, sin otro worker ni secreto en logs/backups públicos; depende de T079.
- [X] T081 Completar recuperación operativa en `backend/src/ecs_ec/cli.py` y probarla en `backend/tests/integration/identity/test_recovery.py` antes de su cuerpo: `recover-admin` solo admin ya activo, TTY/getpass, motivo obligatorio<=500 caracteres, versión capturada revalidada, renovación/revocación total y auditoría de proceso. Documentar comandos reales, entrega inicial, claves/rotación, costo/concurrencia de hashes, riesgos de confirmación incierta y enlace a respaldo009 en `specs/006-acceso-usuarios-rbac/quickstart.md` y `deploy/README.md`; cuenta inexistente/inactiva/Operador no se crea/promueve/reactiva. Depende de US3/T080; ejecutar estas pruebas antes de cerrar la regresión T084.
- [ ] T082 Con G5, escribir `backend/tests/integration/identity/test_telemetry.py` para correlación/etapas/resultados de ingreso, autorización, mutación y recuperación, rechazo esperado frente a fallo, saneamiento sin passwords/correos/cookies/tokens/IP y red/cola técnica caída sin afectar autorización/commits; el historial funcional no se sustituye por logs. Depende de US1/US3, T081 y emisor007 real; no construir ese emisor.
- [ ] T083 Tras T082, instrumentar operaciones propias en `backend/src/ecs_ec/identity/telemetry.py` y conectarlas desde `backend/src/ecs_ec/identity/sessions.py`, `backend/src/ecs_ec/identity/services.py`, `backend/src/ecs_ec/identity/api.py` y `backend/src/ecs_ec/cli.py` usando emisor007 real; pasar T082 y registrar evidencia en `specs/006-acceso-usuarios-rbac/validation/observability.md`. No depender de visores/SMTP para confirmar ni crear recolectores o una cola común paralela.
- [ ] T084 Ejecutar regresión backend/frontend/build y revisar OpenAPI generado, contratos, docstrings/TSDoc de todo código/prueba/script006; ampliar solo checks006 en `.github/workflows/ci.yml` existente y registrar comandos/resultados en `specs/006-acceso-usuarios-rbac/validation/regression.md`. Revisar `backend/src/ecs_ec/identity/`, `backend/src/ecs_ec/core/security.py`, `backend/src/ecs_ec/cli.py`, componentes y tests propios; no marcar revisión/checklists sin evidencia. Depende de historias y T080/T081/T083.
- [ ] T085 Con G6-personas y vista real de G1, realizar diez tareas de ingreso→vista asignada con personas representativas; SC-007 requiere al menos9 sin ayuda en<=1min. Registrar tiempos, resultado y obstáculos sin credenciales en `specs/006-acceso-usuarios-rbac/validation/usability.md`; sin personas/resultados suficientes mantener pendiente aunque E2E pase. Depende de T050/T066/T078 y documentación T081.
- [ ] T086 Con G6-VPS ya provisto por009, comprobar desde red externa HTTPS público de ingreso/consultas/descargas por ambos perfiles, cookie Secure, no-store, falta de sesión, HTTP y X-Forwarded-Proto falsificado sin acceso/sesión, backend no accesible fuera de proxy y origen/Referer rechazados. Registrar entorno/comandos/resultados de US1.8/FR-024/SC-008 en `specs/006-acceso-usuarios-rbac/validation/vps.md`; no provisionar infraestructura dentro006 ni aceptar con TLS local. Depende de historias, T084 y gates de sus capacidades reales.
- [ ] T087 Ejecutar `specs/006-acceso-usuarios-rbac/quickstart.md` con dependencias reales y consolidar cobertura de FR-001..FR-024, SC-001..SC-008 y cada escenario en `specs/006-acceso-usuarios-rbac/validation/acceptance.md`, enlazando suites, carreras, UI, operación, personas y VPS de tareas anteriores. No cerrar aceptación ni declarar implementación completa con gates faltantes, skips, dobles o evidencia solo documental; depende de T076–T086 según sus prerrequisitos y resultados reales.

## Dependencies & Execution Order

### Grafo de ejecución

```text
G0 → T001..T004 → T005..T017 → US1 (T018..T040)
                                ├─ política/puertos/navegación US2 (T041..T045, T047)
                                │    └─ +G1/G2 → conexión y aceptación US2 (T046, T048..T050)
                                └─ US3 (T051..T066), sin depender de G1/G2
US1+US3 → historial propio US4 (T067/T070..T074)
US2+US3 +G1/G2/G3 → mantenimiento/aceptación US4 (T068/T075/T076/T078)
US1+US3 +G4 → separación SFTP (T069/T077)
US1+US3 → mantenimiento (T079/T080) → recuperación (T081)
US1+US3 +recuperación/T081 +G5 → telemetría (T082/T083)
Historias +T080/T081/T083 → regresión (T084)
Historias +G6-personas → T085; regresión/documentación +G6-VPS → T086
Evidencias reales anteriores → T087
```

El orden visual de fases conserva prioridades P1/P1/P1/P2. Los IDs son locales; las
referencias externas son capacidad+contrato+ruta, nunca IDs de otras specs sin contexto.
T081 y T083 se ejecutan antes de la regresión T084. T079–T083 pueden prepararse al completar US1/US3;
aceptación y regresión finales esperan los resultados exigidos.

### Dependencias dentro de cada historia

Pruebas primero → validación/modelos → servicios → endpoints → cliente/componentes →
integración/E2E/evidencia. US2 usa contratos/identidad para desarrollar política aislada,
pero exige productores reales al aceptar. US3 usa fábricas controladas de cuentas y no
necesita consultas/PDF para ser comprobable. US4 reutiliza identidad/gestión de cuentas y
mantiene validadores/revisiones en sus propietarios. La coordinación neutral ya existe
antes de exponer mutaciones y antes de conectar cualquier despacho008.

### Cambios compartidos y límites de paralelismo

`pyproject.toml`, `uv.lock`, `.env.example`, `main.py`, `core/security.py`,
`identity/models.py`, `schemas.py`, `services.py`, `api.py`, `session.ts`,
`identity.ts`, `layout.tsx`, `frontend/tests/e2e/identity.spec.ts` y deploy/CI se modifican
secuencialmente. US2/US3/US4 no se ejecutan enteras en paralelo sobre esos archivos.
Cuando una capacidad propia existe, los tests escritos previamente se ejecutan de nuevo;
no hace falta ejecutar tests repetidos sin cambios o incertidumbres que lo justifiquen.

## Parallel Examples por historia

Los ejemplos describen distribución posible, sin lanzar agentes automáticamente.

| Bloque/historia | Tareas independientes | Prerrequisito y reunión posterior |
| --- | --- | --- |
| Foundational | T005 modelos, T006 coordinación, T007 matriz, T008 auditoría. | Fase1 completa; cada prueba escribe archivos distintos. T009..T017 integran secuencialmente. |
| US1 | T018 credenciales, T019 HTTP, T020 espera, T021 límites/actividad, T022 UI/helper de actividad, T023 bootstrap. | Fase2 completa; T024 empieza después de esas pruebas. |
| US2 | T041 matriz HTTP, T042 lectores, T043 reportes, T044 navegación. | US1 completa; escribir pruebas contra contratos no acredita ejecución de productores. T045 integra, G1/G2 preceden aceptación. |
| US3 pruebas | T051 API, T052 carreras, T053 UI, T054 destinatario interno. | US1 completa, fixtures compartidas ya fijadas. T055 integra sin escribir junto a otro cambio de schemas. |
| US3 componentes | T062 AccountTable y T063 AccountForm. | Cliente/props T061 y T053 completos; archivos separados. T064 integra la página después de ambos. |
| US4 | T067 historial HTTP, T068 mantenimiento, T069 separación, T070 UI. | US1/US3 completos; ejecución real de T068/T069 espera sus gates. T071..T078 se coordinan secuencialmente. |

## Implementation Strategy

### MVP primero

Completar G0, Setup, Foundational y US1. Validar ingreso, renovación/cierre, espera,
expiración, transporte local/CSRF, bootstrap y ausencia de datos privados. Es un MVP del
módulo de identidad: no acredita consultas o aceptación integral del producto ni HTTPS
público. Todas las rutas incorporadas después mantienen autorización por defecto denegada.

### Entrega incremental

Añadir US2 sobre lectores/PDF reales cuando existan. Si aún faltan, avanzar US3 sobre US1
sin fabricar esos proveedores. Después incorporar historial y mantenimiento US4. Integrar
emisión007 cuando su capacidad exista, conservando disponibilidad ante caída técnica.
Cerrar operación, regresión y evidencias de personas/VPS por criterios separados.
No iniciar la implementación de otras specs automáticamente desde estas tareas.

## Trazabilidad del traslado y cobertura

### Entradas históricas conservadas

Esta tabla usa **IDs del borrador anterior de spec-006**, no referencias a las tareas
actuales con el mismo número. Su procedencia desde008 está en la hoja de ruta.

| Entrada histórica del borrador006 | Tareas actuales de spec-006 que conservan su alcance |
| --- | --- |
| anterior spec-006/T001: límites de identidad sin008 | T007, T018..T023, T038/T039, T041..T044, T051/T052/T054, T065 y T069/T077. |
| anterior spec-006/T002: protocolo neutral/sintético | T006, T015/T016, T032 y T052; pruebas reales con participante008 siguen en su propietario. |
| anterior spec-006/T003: cuentas/sesiones/bootstrap/migración | T005, T009..T014, T018..T021/T023..T027, T029..T031 y T055..T060. |
| anterior spec-006/T004: core/security, CSRF/errores | T019, T025/T028/T031/T032, T041/T045/T046 y T075/T076. |
| anterior spec-006/T005: ingreso/cuenta/session.ts | T022, T033..T036, T039/T040 y T047/T048. |
| anterior spec-006/T006: administración de cuentas | T008/T016, T051..T066, T067/T071..T074 y T076. |

Ninguna entrada se da por completada por trasladarla o generar esta lista.

### Requisitos y escenarios

| Requisito/criterio | Tareas actuales de spec-006 |
| --- | --- |
| FR-001..FR-003: perfil, acceso y unicidad | T005/T007/T009..T014, T018/T024/T027, T051..T060/T065. |
| FR-004: fallo general y espera | T019/T020, T024..T026/T031/T035/T038. |
| FR-005..FR-006: control vigente por defecto y protección directa | T007/T017/T021/T028/T032, T041/T045/T046/T049/T050, T060/T067/T072/T075/T076. |
| FR-007..FR-010: consultas/PDF, exclusión administrativa y navegación | T041..T050 y T068/T075/T078. |
| FR-011..FR-013: cuentas, desactivación y último admin | T005/T009/T011/T012/T016, T023/T030 y T051..T066. |
| FR-014..FR-018: credenciales, renovación y revocación | T018..T040, T051/T052/T055..T060/T065/T066, T079/T080/T081. |
| FR-019: configuraciones editables001/004 y restricciones obligatorias002 | T068/T075/T076/T078; US4.4 rechaza fuente duplicada y conserva revisión. |
| FR-020: boletas/recálculo administrativos y referencias de lectura | T042/T043/T046/T049/T050 y T068/T075/T076/T078. |
| FR-021..FR-022: auditoría, rechazo y estado válido | T008/T014/T016/T032, T051/T052/T057/T058/T065, T067..T068/T071..T076/T078/T081. |
| FR-023: separación técnica | T007/T017/T021/T041/T054/T059 y T069/T077. |
| FR-024: transporte | T003/T004/T019/T028/T039 y T086. |
| SC-001 | T018..T040; casos de renovación/reset de T065/T066. |
| SC-002..SC-003 | T041..T050, T068/T075/T076/T078; proveedores G1/G2 reales. |
| SC-004 | T020/T021/T022/T027/T029/T033/T038/T039, T043/T048..T050/T052/T057/T058/T065/T066/T079/T080; actividad interactiva/background, bordes de inactividad y duración absoluta. |
| SC-005 | T005/T009..T012/T016/T023/T030 y T051..T066. |
| SC-006 | T008/T014/T016/T032/T065 y T067..T078. |
| SC-007 | T085; pruebas UI apoyan, no sustituyen a personas. |
| SC-008 | T086; TLS local no sustituye VPS/red externa. |
| US1.1..US1.7 y US1.9 | T018..T040; inicial/reset se repite en T051..T066. |
| US1.8 | T086. |
| US2.1..US2.7 | T041..T050 y gestión de invalidación T057/T058/T065. |
| US3.1..US3.8 | T051..T066, cambio propio ya disponible por T029/T036. |
| US4.1..US4.6 | T067/T068/T070..T076/T078. |
| US4.7 | T069/T077, proveedor003 real. |

## Notes

No hay código de aplicación implementado por esta generación. Para empezar, revisar
consistencia con `$speckit-analyze` y resolver los gates reales por capacidad/propietario.
No modificar plantillas/scripts/skills oficiales ni checklists de revisión para ejecutar
estas tareas. Mantener todas las casillas pendientes hasta contar con evidencia propia.
