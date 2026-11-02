# Arquitectura compartida de ECS-EC

Estado: plataforma spec-009 y capacidades propias de identidad 006 implementadas y validadas localmente; integraciones de negocio y VPS pendientes. Este documento centraliza decisiones ya presentes
en la planificación de notificaciones; su traslado no acredita instalación, pruebas ni
despliegue. La [hoja de ruta](implementation-roadmap.md) asigna propietarios y etapas.
La constitución local `.specify/memory/constitution.md` conserva su precedencia.

Consumo 001 tiene catálogo/configuración y reglas puras verificadas, con componentes web
aislados; la incorporación durable y almacenamiento de 002 ya están disponibles; su fachada/consulta
web de 001 y la integración de agrupaciones siguen pendientes.
[Estado de 002](../specs/002-registro-retencion-consumo/validation/acceptance.md).
[Aceptación parcial](../specs/001-visualizar-consumo-categorias/validation/acceptance.md).

## Unidad de aplicación y herramientas

ECS-EC es un monolito modular: una imagen y un proceso Uvicorn inicial sirven la API
FastAPI y la exportación estática de React/Next.js. Los trabajos internos viven en su
`lifespan`, sin worker propio desplegado por separado. PostgreSQL, SMTP y los recolectores
y visores técnicos son dependencias de infraestructura.

| Elemento | Decisión heredada del diseño |
| --- | --- |
| Python | CPython 3.14 convencional con GIL; `requires-python = ">=3.14,<3.15"`; uv, `.python-version`, `pyproject.toml` y `uv.lock` en raíz. |
| API/datos | `fastapi==0.162.0`, Pydantic 2, Uvicorn, SQLAlchemy 2, Psycopg 3 asíncrono y Alembic. |
| Interfaz | TypeScript, React 19.x y Next.js 16.x App Router con `output: 'export'`; Node >=20.9 solo para construcción; npm y `frontend/package-lock.json`. |
| Persistencia | PostgreSQL 18 como versión inicial dentro de 18+; no hay upgrades mayores automáticos. |
| Pruebas | pytest/HTTPX y PostgreSQL real; Vitest/Testing Library y Playwright. SQLite no acredita exclusión/concurrencia PostgreSQL. |
| Ejecución | Docker Compose local; VPS posterior con HTTPS y dirección pública, mediante configuración. |
| Correo | Adaptador SMTP y Mailpit local, propiedad de spec-008. |
| Observabilidad | Loguru JSON → Alloy → Loki/LogQL y Grafana; OpenTelemetry/OTLP → Jaeger, propiedad de spec-007. |

Las versiones exactas comunes, transitivas y digests se fijaron y comprobaron localmente
en los manifiestos/lockfiles e imágenes de plataforma 009. Los módulos posteriores validan
sus dependencias al incorporarse. El [registro de investigación](../specs/009-fundaciones-plataforma/research.md)
conserva sus fuentes y alternativas; cada módulo conserva las decisiones de su dominio.

## Estructura prevista del código

```text
pyproject.toml, uv.lock, .python-version, .env.example, Dockerfile, compose.yaml
backend/
├── src/ecs_ec/
│   ├── main.py                # composición de módulos, propiedad de plataforma
│   ├── cli.py                 # bootstrap de identidad, propiedad de spec-006
│   ├── core/                  # configuración, reloj, DB/UoW, errores y ciclo de vida
│   ├── audit/                 # almacenamiento/eventos/cobertura funcional comunes
│   ├── identity/              # cuentas/sesiones/autorización, spec-006
│   ├── consumption/           # mediciones/consultas/agregados, specs-001/002
│   ├── acquisition/           # recepción/adaptación PAS600/SFTP, spec-003
│   ├── costs/                 # spec-004
│   ├── reports/               # spec-005
│   ├── notifications/         # spec-008
│   ├── observability/         # instrumentación, spec-007
│   └── web/                   # export Next copiado durante build
├── migrations/versions/
├── alembic.ini
└── tests/{unit,integration,contract}/
tools/pas600_simulator/        # fuente externa opcional de pruebas, spec-003
frontend/
├── package.json, package-lock.json, next.config.ts
├── src/app/
├── src/components/
├── src/lib/api/
└── tests/{unit,e2e}/
deploy/
├── observability/             # spec-007
├── technical-gateway/         # spec-007
├── backup.sh, restore.sh      # plataforma
└── README.md                  # procedimientos comunes y enlaces a guías de módulos
```

`core`, `audit`, la composición y el scaffold web ya existen; los módulos de negocio de
la estructura prevista se incorporan por sus propietarios. Los contratos implementados
están en [plataforma](platform.md). La exportación estática no usa SSR
por solicitud, Server Actions ni un servidor Node en ejecución. Las rutas que seleccionan
entidades usan query/estado cliente; los datos privados se obtienen de la API autenticada.

## Persistencia y contratos comunes

Usar UUID generados por la aplicación, revisiones positivas, instantes UTC en `timestamptz`
y zona IANA explícita. Los intervalos son `[inicio,fin)` con inicio < fin. Energía y dinero
usan NUMERIC/Decimal; los contratos HTTP transmiten decimales como cadenas. Datos ausentes
son NULL con razón y cobertura, nunca cero implícito. JSONB tiene esquemas tipados.

La unidad de trabajo asíncrona y Alembic pertenecen a plataforma. Cada funcionalidad
posee sus tablas/migraciones y las enlaza al head real; no reserva un número global libre
ni recrea tablas compartidas. La auditoría funcional y `FunctionalEvent` pertenecen a
`audit`, con contrato en [spec-009](../specs/009-fundaciones-plataforma/contracts/integrations.md).
Cada productor registra resultado/evento en la misma transacción sin importar notificaciones.

La conservación funcional es al menos 12 meses calendario desde el registro o revisión
sustantiva correspondiente. La utilidad común de aniversario conserva la segunda hora
repetida y avanza al primer instante válido si no existe; la política de dependencias y
el instante que inicia el plazo pertenecen a cada spec. Nunca sustituir meses por 365 días.
Los registros protegidos no se eliminan por cascada. Telemetría tiene conservación propia.

## Identidad, coordinación y aislamiento

La spec-006 provee sesiones, CSRF y permisos actuales en servidor. Operador y Administrador
técnico son perfiles funcionales. Programador se autentica por el entorno técnico de
spec-007 y no obtiene permisos funcionales por ese acceso.

El contrato común de [coordinación de identidad](../specs/006-acceso-usuarios-rbac/contracts/coordination.md)
permite registrar participantes sin importar `notifications` desde `identity`. Notificaciones
implementa su participante antes de habilitar envíos: reglas por UUID ordenado → cuenta →
entrega, con revalidación y reintento si cambia el conjunto. No existe dependencia inversa
de identidad, consumo, costos o PDF sobre el consumidor, scheduler o SMTP de la spec-008.

Correo y telemetría no condicionan la disponibilidad funcional ni los commits de negocio.
Las colas técnicas son acotadas y las pérdidas visibles. Cada módulo documenta sus errores,
límites, pruebas y procedimientos en el mismo cambio que implementa su comportamiento.

## Entornos

Compose espera salud de PostgreSQL y migraciones antes de habilitar la aplicación.
PostgreSQL 18 monta `/var/lib/postgresql`, con PGDATA `/var/lib/postgresql/18/docker`.
Mailpit y observabilidad se incorporan por sus funcionalidades a perfiles opcionales.
La VPS requiere HTTPS, URL pública, secretos externos y respaldo/restauración comprobados.
`America/Santiago` y direcciones `example.test` son valores locales de prueba, no confirmación
de la instalación real. Dominio, zona real y credenciales siguen siendo configuración.
