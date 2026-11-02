# Implementation Plan: Autenticación y permisos por perfil

## Contexto compartido del proyecto (ECS-EC)

Este diseño aplica [AGENTS.md](../../AGENTS.md), la
[arquitectura](../../docs/architecture.md), la [hoja de ruta](../../docs/implementation-roadmap.md)
y la [constitución 1.0.0](../../.specify/memory/constitution.md). Plataforma009 posee
infraestructura, core y auditoría; identidad006 posee cuentas, sesiones y autorización.
Al planificar se leyó el borrador de seis tareas trasladadas. Este plan cubre las cuatro
historias; [tasks.md](tasks.md) ya contiene la generación integral de `$speckit-tasks`
con trazabilidad del traslado. La revisión previa consta en la hoja de ruta. Implementación y validación local propias
constan en [aceptación parcial](validation/acceptance.md); los gates externos siguen pendientes.

**Branch/contexto Spec Kit**: `006-acceso-usuarios-rbac` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: `specs/006-acceso-usuarios-rbac/spec.md`.
**Rama Git actual**: `develop`; setup seleccionó la funcionalidad en `.specify/feature.json`,
sin crear ni cambiar la rama Git.
**Estado**: Implementación propia validada localmente; integración/aceptación integral pendientes según los gates.

## Summary

Incorporar identidad humana al monolito con dos perfiles fijos: Operador y Administrador
técnico. Autenticar por correo/contraseña, exigir renovación inicial, controlar expiración
y espera por intentos fallidos y verificar los permisos actuales en cada petición. El
Operador consulta y genera/descarga PDF; las cuentas y configuraciones quedan reservadas
al Administrador, con auditoría y protección concurrente del último administrador activo.

Usar sesiones opacas persistidas, Argon2id, CSRF/origen, `auth_version` y transacciones
PostgreSQL. La UI exportada de Next.js obtiene datos privados en runtime. El registro
neutral de participantes permite coordinar mutaciones sin importar notificaciones. No
se implementan aquí consumo, SFTP, costos, PDF, SMTP, visores ni infraestructura común.

## Technical Context

**Language/Version**: CPython 3.14 convencional con GIL y TypeScript de la arquitectura común.
**Primary Dependencies**: FastAPI 0.162.0, Pydantic 2, Uvicorn, SQLAlchemy 2/Psycopg 3
asíncronos y Alembic; `argon2-cffi` y `email-validator`; React 19.x/Next.js 16.x App Router
con export estático. uv/npm y locks de plataforma; versiones restantes comprobadas y
fijadas durante implementación, sin actualizar la pila común en esta planificación.
**Storage**: PostgreSQL 18; tablas de cuentas, sesiones, presesiones, intentos y guardia
propias de identidad. Auditoría/eventos en tablas comunes de 009, sin duplicarlas.
**Testing**: pytest/HTTPX y PostgreSQL real para concurrencia, reloj inyectable de core;
Vitest/Testing Library para UI y Playwright para navegación, cookies y permisos.
**Target Platform**: Linux/Docker Compose local y VPS posterior con HTTPS; Node >=20.9
solo para construir el frontend, un proceso inicial Uvicorn.
**Project Type**: Módulo de identidad dentro del monolito modular web.
**Performance Goals**: Sin SLO nuevo de latencia/capacidad. SC-007 exige 9/10 tareas con
personas en <=1 minuto. Medir costo/memoria de hashing antes de dimensionar concurrencia.
**Constraints**: Dos perfiles, un edificio, sin registro público, MFA, federación ni
recuperación automática por correo. Contraseñas 15..128 caracteres exactos; sesión 30 min
de inactividad/8 h absolutas; cinco fallos por correo/origen en 15 min activan 15 min de
espera. Datos privados fuera del export estático; HTTPS exigido en publicación pública.
FR-019 administra configuraciones editables de fuentes001 y suministro/perfiles004;
recepción mínima15min y conservación mínima12meses son restricciones obligatorias de002
sin edición web en006.
**Scale/Scope**: Cuatro historias, FR-001..024 y SC-001..008; sin tamaño de usuarios ni
caudal garantizados por la spec. No requerir notificaciones ni visores para acceder.

## Constitution Check

GATE previo a investigación y reevaluado después del diseño:

| Principio/restricción | Antes de Phase 0 | Después de Phase 1 |
| --- | --- | --- |
| I. Propósito eléctrico | Acceso y mantenimiento de las funciones del edificio. Cumple. | Matriz limitada a capacidades especificadas; no crea funciones de negocio. Cumple. |
| II. Monolito modular | Identidad y UI en la unidad existente; DB externa permitida. Cumple. | Puertos internos y participantes sin dependencias inversas; sin IdP/worker adicional. Cumple. |
| III. Documentación integral | Contratos, operación y pruebas planificados. Cumple en diseño. | Documentar cada archivo, función/clase/componente y prueba, entradas/salidas/errores/efectos en el mismo cambio; quickstart reproducible previsto. Cumple en diseño. |
| IV. Integridad y trazabilidad | Correo único, validación, UTC y transacciones. Cumple. | Locks, revisiones, revocación y auditoría atómica; no modifica lecturas ni plazos de otros módulos. Cumple. |
| V. Visualización verificable | Permisos y estados de acceso explícitos. Cumple. | UI distingue carga, error y sesión restringida/vencida; no convierte rechazo en ausencia de datos. Cumple. |
| Pila y criterios medibles | Pila compartida y límites aprobados en spec. Cumple. | Fuentes y alternativas en research; aceptación de personas/VPS sigue pendiente. Cumple en diseño. |

Sin desviaciones ni excepciones. La comprobación documental no acredita cumplimiento en
ejecución. Antes de integrar código deben existir documentación y resultados aplicables.

## Project Structure

### Documentation (this feature)

```text
specs/006-acceso-usuarios-rbac/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http.md
│   ├── ui.md
│   ├── integrations.md
│   └── coordination.md
├── tasks.md                  # tareas integrales; conserva el traslado pendiente
└── checklists/requirements.md # revisión previa; no modificar sus marcas por este plan
```

### Source Code (repository root, estructura propuesta)

```text
backend/src/ecs_ec/
├── identity/
│   ├── models.py, schemas.py, repository.py
│   ├── credentials.py, sessions.py, permissions.py
│   ├── coordination.py, services.py, api.py
│   └── security.py           # implementación de sesión, CSRF y transporte
├── cli.py                   # bootstrap y recuperación controlados, propiedad de 006
├── core/security.py         # fachada de integración de seguridad, alcance heredado
└── main.py                  # solo registrar rutas/participantes en composición de 009
backend/migrations/versions/identity_initial.py
backend/tests/{unit,integration,contract}/identity/
frontend/src/app/{ingreso,cuenta,administracion/usuarios,administracion/historial}/page.tsx
frontend/src/app/layout.tsx   # montar SessionProvider durante US1; Navigation se añade en US2
frontend/src/components/identity/
frontend/src/lib/api/session.ts # cliente de acceso y sessionActivityHeaders(activity)
frontend/tests/unit/identity/
frontend/tests/e2e/identity.spec.ts
scripts/seed_identity_reference.py
```

**Structure Decision**: `identity` posee dominio, persistencia y mecanismos de acceso.
`core/security.py` conserva el punto trasladado como fachada hacia identidad; no recrea
configuración, reloj, UoW ni errores de core, cuyo propietario sigue siendo 009. El alta
del router y configuración amplía la composición común secuencialmente cuando exista.
La migración se enlaza al head real y crea solo tablas de 006; no reserva número global.
Ninguna ruta propuesta prueba que ya exista código.

## Phase 0: Research

[research.md](research.md) resuelve hashing y correo, sesiones, CSRF de ingreso, espera,
concurrencia, auditoría, bootstrap y transporte con decisiones, razones, alternativas y
fuentes primarias. Se investigaron seguridad e integración en paralelo. No quedan
aclaraciones abiertas de diseño; secretos, dominio público y recursos se comprueban al
implementar sus contratos.

## Phase 1: Design & Contracts

[data-model.md](data-model.md) define entidades, índices, validaciones y transiciones.
[HTTP](contracts/http.md) fija cuerpos, errores, cookies y precondiciones; [UI](contracts/ui.md)
fija navegación y estados; [integraciones](contracts/integrations.md) fija permisos y
consumo de puertos externos. Se completa el [contrato trasladado](contracts/coordination.md)
sin cambiar su URL ni las garantías regla → cuenta → entrega.

1. Crear cuenta con correo canónico único, hash y renovación obligatoria. Preparación
   inicial y recuperación mediante CLI/TTY, sin contraseña predeterminada ni alta pública.
2. Ingresar con presesión CSRF de 10 min; aplicar rechazo general y espera durable
   por correo/origen. Hash fuera de locks, seguido de revalidación antes de emitir sesión.
3. Resolver sesión por cookie y DB actual. Sesión restringida solo usa metadatos mínimos,
   renovación propia y cierre. Renovar contraseña revoca todas las sesiones y exige ingreso.
4. Exponer matriz fija de acciones. No derivar permisos de verbos HTTP: POST PDF es
   consulta funcional; GET configuración es administración. Autorizar antes de replay
   idempotente y de cada entrega de PDF. Ignorar perfiles declarados por el cliente.
5. Mutar cuentas con revisión esperada y guardia singleton → participantes → cuentas
   ordenadas → sesiones/recursos posteriores. Revalidar actor, sesión original e
   invariantes con reloj actualizado tras los locks; cambio de
   referencias obliga a rollback/reintento acotado, sin adquirir locks fuera de orden.
6. Confirmar cambio, revocación, auditoría y eventos juntos. Registrar denegaciones
   administrativas después de rollback en UoW propia. Historial solo lectura para admin.
7. Integrar controles y navegación con módulos reales de consumo/costos/PDF. Cada
   propietario mantiene sus formularios, validaciones, revisiones y producción de auditoría.
8. Exigir HTTPS público y confiar solo proxies configurados; comprobar también acceso
   directo al backend, sesiones vencidas, cargas manipuladas y descargas antiguas.

Durante US1, montar `SessionProvider` como componente cliente desde
`frontend/src/app/layout.tsx`, envolviendo ingreso/cuenta y manteniendo el export estático.
El checkpoint local no depende de Navigation de US2; esta reutiliza el proveedor ya
montado. `frontend/src/lib/api/session.ts` aporta `sessionActivityHeaders(activity)` con
default background y pruebas previas. US2 conecta interactive a navegación/consultas/filtros
iniciados por la persona y background a sondeos; `/auth/session` nunca renueva actividad,
incluso con interactive. Verificar consulta al minuto29→límite59, solo sondeos→vence30,
duración absoluta8h y ausencia de resurrección después de vencer.

FR-019 se acepta con edición real de fuentes/correspondencias001 y suministro/perfiles
BT4.3 de004. US4.4 rechaza una fuente asignada a dos categorías sin cambiar la revisión
anterior. Las restricciones de recepción/retención002 se comprueban por separado mediante
sus puertos/validadores, sin prometer edición web de esos mínimos.

### Cobertura por historia y aceptación

| Historia | Requisitos cubiertos | Validación prevista |
| --- | --- | --- |
| US1, P1: ingreso/salida | FR-002..006, 015..018, 024 | Credenciales por perfil, mensajes, espera, CSRF, proveedor montado en layout, renovación, actividad interactiva/background, expiración/cierre, local y HTTPS. SC-001/004/008. |
| US2, P1: consultas del Operador | FR-001, 005..010, 018, 020, 023 | Matriz, URL directa, perfil manipulado, referencias de negocio y PDF real protegido. SC-002/003. |
| US3, P1: cuentas | FR-001..003, 011..018, 021..022 | Duplicados, revisiones, desactivar/reactivar, reset y cambio propio, último admin concurrente. SC-004/005/006. |
| US4, P2: sistema trazable | FR-005..006, 009, 017..024 | Configuración editable001/004, fuente duplicada rechazada, boletas/tarifas/recálculo reales, restricciones002 sin edición web, historial y separación SFTP. SC-002/006/008. |
| Transversal de UI | FR-010 y escenarios de ingreso | Diez tareas con personas representativas; >=9 sin ayuda en <=1 min. SC-007. |

La aceptación completa cubre todos los escenarios de las cuatro historias y ocho SC.
Un harness sintético acredita la política de identidad, no el funcionamiento real de
consumo, costos, PDFs, SFTP, notificaciones, personas o VPS.

### Conservación del traslado

| Entrada histórica del borrador anterior de spec-006 | Diseño que la conserva y amplía |
| --- | --- |
| spec-006/T001 | Pruebas de límites, sesiones, matriz y separación Programador, incluidas cuentas sin 008 instalado. |
| spec-006/T002 | Coordinación neutral y participante sintético, revalidación y carreras documentadas. |
| spec-006/T003 | Cuentas, bootstrap, sesiones, credenciales, intentos, migración y recuperación. |
| spec-006/T004 | Fachada core/security, implementación identity/security, origen/CSRF y errores comunes. |
| spec-006/T005 | `/ingreso/`, `/cuenta/`, cliente session y retorno seguro, sin datos privados exportados. |
| spec-006/T006 | Administración de cuentas, historial y bloqueo del último admin; nuevas pruebas US2/US4. |

Los seis ítems históricos se integraron con su trazabilidad en la lista completa de
[tasks.md](tasks.md), que identifica su correspondencia con los IDs actuales y añade
cobertura, operación y aceptación. Los IDs de esta tabla son los del borrador anterior,
no dependencias por números actuales. No iniciar implementación sin revisar consistencia.

## Dependencies & Delivery

1. Requerir capacidades reales de plataforma009: scaffold, DB/UoW, reloj, configuración,
   errores, auditoría/eventos y composición, según [su plan](../009-fundaciones-plataforma/plan.md)
   y [contrato](../009-fundaciones-plataforma/contracts/integrations.md). La base está disponible
   y validada localmente; su VPS sigue pendiente. No recrearla en el setup de006.
2. Implementar US1 y capacidades base de US3 sobre esa plataforma; US2 incorpora matriz
   y pruebas de denegación desde el primer endpoint protegido, sin esperar US4 para protegerlo.
3. Integrar lectores de 001/002 y configuración001, costos004 y PDF005 a medida que existan.
   US2/US4 integrales esperan esas capacidades reales, sin ejecutar sus tareas dentro de 006.
   Los mínimos de recepción/retención002 son restricciones obligatorias sin edición web
   en006; sus puertos reales se prueban por separado. 003 mantiene SFTP separado.
4. Coordinar instrumentación propia con el emisor común de 007 cuando exista, sin
   implementar recolectores/visores ni depender de ellos para autenticar o confirmar cambios.
5. No depender de 008. Su participante concreto y pruebas de revocación contra el inicio
   durable son responsabilidad de [008](../008-notificaciones-programables/contracts/integrations.md)
   antes del primer despacho; aquí se valida el protocolo neutral con cero/sintético.
6. Documentar y ejecutar [quickstart.md](quickstart.md), concurrencia PostgreSQL y checks
   locales. Posteriormente obtener evidencia de personas y del HTTPS público. Plataforma
   posee TLS/operación común; 006 exige y comprueba su política de acceso.

Las pruebas de capacidades nuevas y contratos preceden a su implementación, conservando
el compromiso del traslado. Cambios de composición, manifiestos y deploy son secuenciales.

## Complexity Tracking

Sin violaciones constitucionales. La guardia singleton serializa mutaciones de cuentas
en el alcance de un edificio y evita un protocolo distribuido; no serializa lecturas ni
hashing. PostgreSQL mantiene sesión, espera y auditoría, sin Redis ni otro servicio propio.
