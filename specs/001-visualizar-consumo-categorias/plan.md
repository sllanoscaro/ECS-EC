# Implementation Plan: Consumo eléctrico por categorías

**Branch/contexto Spec Kit**: `001-visualizar-consumo-categorias` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Rama Git real**: `develop`; este flujo no crea ni cambia ramas.
**Input**: `specs/001-visualizar-consumo-categorias/spec.md` y el alcance trasladado, integrado en [tasks.md](tasks.md).
**Estado**: planificación completa; implementación parcial de 48/61 tareas verificada
localmente el 2026-11-02. Recepción real 002, consulta web y administración integradas;
aceptación integral pendiente. [Evidencia vigente](validation/increment-2026-11-02.md).
**Aclaraciones aplicadas**: I1, U1 y A1 aprobadas expresamente el 2026-11-01; modelo,
contratos, ejemplos y tareas sincronizados, sin acreditar implementación ni cerrar aceptación.

## Contexto compartido del proyecto (ECS-EC)

Rigen [AGENTS.md](../../AGENTS.md), la [arquitectura](../../docs/architecture.md),
la [hoja de ruta](../../docs/implementation-roadmap.md) y la
[constitución v1.0.0](../../.specify/memory/constitution.md). Las capacidades externas
son prerrequisitos asignados a su propietario, no trabajo de setup de esta spec.

## Summary

Ofrecer las siete categorías fijas con gráfico temporal y tabla de una única serie por
categoría. La instalación configura un subconjunto de medidores; CAT-01 utiliza
exclusivamente el medidor total cuando existe, o una suma identificada de parciales
presentes con intervalos exactamente alineados cuando no existe. Nunca rellenar ausencias
ni reemplazar lecturas generales faltantes con sumas. Gráfico y tabla comparten valores
exactos en kWh, período, zona, procedencia y estados de consulta.

La revisión global conserva auditoría; `category_revision` delimita la validez de cada
fuente y la firma calculada CAT-01. Las revisiones globales ajenas no invalidan lecturas.
Un cambio propio se rechaza por registro; cambiar la firma calculada dentro de un intervalo
produce diagnóstico con segmentos y conserva las parciales válidas.

001 posee catálogo, configuración de fuentes, validación de dominio, cálculo candidato de
CAT-01, consulta por intervalo y UI. 002 incorpora/persiste mediciones y totales, aplica
los 15 minutos reales por categoría y conserva detalle, agregados y trazabilidad. 003
resuelve archivos PAS600/SFTP y normalización desde contadores si corresponde. El diseño
de [integraciones](contracts/integrations.md) permite desarrollar reglas puras de 001
antes de la aceptación completa de 002; la aceptación integrada exige su almacenamiento
real. Ninguna consulta GET incorpora nuevos totales.

## Technical Context

**Language/Version**: Python `>=3.14,<3.15` convencional con GIL y TypeScript; versiones
base ya elegidas en arquitectura, sin reabrir su selección.

**Primary Dependencies**: FastAPI `0.162.0`, Pydantic 2, SQLAlchemy 2/Psycopg 3 asíncrono,
Alembic y Uvicorn de plataforma 009. React 19/Next.js 16 con exportación estática; SVG
nativo para intervalos, `decimal.js` solo para proyección geométrica y formato exacto.
`Decimal` y `ZoneInfo` en servidor. Pins restantes y lockfiles se comprueban al implementar.

**Storage**: PostgreSQL 18 real. 001 posee catálogo/configuración/fuentes y sus migraciones;
002 posee tablas de mediciones/totales, deduplicación, recepción y conservación. Una sola
serie persistida por categoría; no crear otra base ni tablas espejo en 001.

**Testing**: pytest/HTTPX; integración y concurrencia con PostgreSQL; Vitest/Testing Library
y Playwright. Datos conocidos, reloj controlado y pruebas anteriores a reglas nuevas.
Comparar valores e intervalos del SVG/tabla con la respuesta y con entradas independientes.

**Target Platform**: Docker Compose local; misma imagen monolítica Linux en VPS con HTTPS
y dirección pública posterior. Next no requiere servidor Node en ejecución.

**Project Type**: Aplicación web monolítica modular; API y frontend estático en un proceso
de aplicación, trabajos de recepción/reevaluación internos incorporados por sus propietarios.

**Performance Goals**: No existe SLO de latencia, concurrencia ni tiempo real aprobado.
SC-005 exige al menos 9/10 tareas humanas sin ayuda en <=60 s. Medir carga de historial
representativo durante implementación, sin convertir esa medición en un SLO inventado.

**Constraints**: Decimales HTTP como cadenas, UTC almacenado y zona IANA explícita,
intervalos `[inicio,fin)`, selección por contención completa, cero distinto de ausencia,
precisión conservada, sin prorrateo/interpolación ni agregación automática para dibujar.
Sesión y permisos actuales de 006; datos privados ausentes del build estático. Sin
dependencia de SMTP, notificaciones o disponibilidad de visores técnicos.

Dominio individual aprobado: `0 <= E < 10^30 kWh`, múltiplo exacto de `10^-15 kWh` tras
conversión; total CAT-01 hasta `6*(10^30-10^-15)` inclusive. Contexto Decimal 50 para
conversiones/suma de seis con detección de inexactitud, sin imponer ese contexto a los
agregados de 002. Configuración consulta límites aceptados por categoría e historia
persistente mediante `MeasurementStore.read_reconfiguration_bounds` de 002, en la misma
UoW de escritura y bajo bloqueos compartidos; falta/fallo del proveedor impide cambios.
Solo la primera configuración sin revisiones anteriores puede preceder a ese proveedor.

**Scale/Scope**: Un edificio, siete categorías, una serie consolidada por categoría,
cuatro historias. Detalle por intervalo en 001; hora/día/mes/año y conservación mínima
de 12 meses en 002. Sin múltiples edificios, conciliación, alarmas, costos o exportaciones
implementados aquí. No se presupone un muestreo físico fijo ni siete medidores instalados.

**Recepción/configuración**: Puerto interno de registros normalizados; mecanismo físico
PAS600/SFTP de 003. Su escenario inicial muestrea cada 15 minutos y separa publicaciones
al menos 15 minutos; eso no impone la duración de cada medición ni garantiza su llegada.
La aceptación real por categoría y la incorporación calculada respetan 002. La UI consulta
al abrir/cambiar filtros/actualizar manualmente; no se promete refresco automático.

**Decisiones resueltas**: [research.md](research.md). Zona real, medidores/correspondencias,
dominio y credenciales son configuración obligatoria antes de conectar una instalación,
no incógnitas del diseño ni valores que deban inferirse del equipo de desarrollo.

## Constitution Check

Gate previo a fase 0: **PASS** sobre los requisitos y la arquitectura seleccionada.
Reevaluación tras fase 1: **PASS de diseño**; no acredita implementación ni aceptación.

| Principio/gate | Comprobación previa | Evidencia posterior al diseño |
| --- | --- | --- |
| I. Monitoreo y fuentes explícitas | Las cuatro historias sirven al consumo del edificio; no asumir equipos ni frecuencia de llegada. | Catálogo, configuración y frontera PAS600 en modelo/integraciones; fixtures locales identificados. |
| II. Monolito modular | Reutilizar plataforma y separar dominio/consulta/UI de persistencia y transporte. | Puertos internos sin HTTP entre módulos ni worker desplegable nuevo; Next exportado. |
| III. Documentación integral | Cada tarea futura deberá documentar archivos, clases, funciones, componentes y pruebas. | Modelo, HTTP, UI, integraciones y quickstart; fórmulas junto al código, revisión de contratos/docstrings/TSDoc en el mismo cambio. |
| IV. Integridad/trazabilidad | Validar antes de aceptar; conservar originales, zona, duplicados y ausencias. | Conversión exacta, equivalencia, exclusión transaccional requerida a 002, contribuciones y revisiones inmutables. |
| V. Visualización verificable | Mismos filtros y datos para gráfico y tabla; estados separados. | Un solo resultado por consulta, SVG de intervalos independientes, formato compartido y descarte de respuestas obsoletas. |
| Restricciones y gobierno | No añadir SLA, arquitectura distribuida ni alcance ajeno. | FR-001..019/SC-001..007 trazados abajo; gates de integración/humanos/VPS pendientes de ejecución. |

No se detectan desviaciones constitucionales ni se requiere enmienda.

## Project Structure

### Documentation (this feature)

```text
specs/001-visualizar-consumo-categorias/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.json
│   ├── http.md
│   ├── integrations.md
│   └── ui.md
└── tasks.md             # lista integral generada; implementación pendiente
```

### Source Code (repository root, this feature)

Estructura de diseño; disponibilidad y límites actuales en la evidencia vigente:

```text
backend/src/ecs_ec/consumption/
├── models.py           # objetos/contratos de dominio; semántica 001
├── catalog.py
├── configuration.py    # revisiones, fuentes y autorización administrativa delegada
├── catalog_storage.py  # solo persistencia de catálogo/configuración 001
├── validation.py
├── totals.py           # evaluación pura; incorporación pertenece a 002
├── ports.py            # límites de recepción/almacenamiento compartidos
├── queries.py          # fachada de detalle/estado de fuentes 001
├── schemas.py
└── router.py
backend/migrations/versions/<revision_real>_consumption_catalog.py
backend/tests/unit/consumption/
backend/tests/integration/consumption/test_measurement_semantics.py
backend/tests/integration/consumption/test_configuration.py
backend/tests/integration/consumption/test_detail_queries.py
backend/tests/contract/consumption/
frontend/src/app/consumption/page.tsx
frontend/src/app/administration/consumption/page.tsx
frontend/src/components/consumption/
frontend/src/lib/api/consumption.ts
frontend/tests/unit/consumption/
frontend/tests/e2e/consumption.spec.ts
```

**Structure Decision**: `models.py` recoge semántica/DTO; los modelos ORM de mediciones
se concretarán con 002, preferentemente en `consumption/persistence.py`, evitando que dos
specs creen la misma tabla. Sus borradores citan archivos compartidos: coordinar esos
cambios secuencialmente al planificar 002. 001 integra su router y componentes después
de existir la composición/layout de 009/006; no crea de nuevo `core`, identidad,
auditoría, Compose ni recolectores. Cada migración depende del head real de Alembic.

## Phase 0 — Investigación

Se investigaron mediante agentes las fronteras 001/002/003 y los consumidores 004/005/008,
y la precisión, fechas y estado de la UI. Se contrastaron decisiones con documentación
primaria; [research.md](research.md) registra decisiones, razones y alternativas.
Resultado: sin aclaraciones técnicas abiertas. La confirmación de la instalación real
sigue siendo un prerrequisito operativo antes de conectarla.

## Phase 1 — Diseño

1. [Modelo](data-model.md): configuración versionada, medición validada, total candidato,
   resultado de recepción y consulta; separa propiedad y persistencia.
2. [HTTP](contracts/http.md) y [OpenAPI](contracts/openapi.json): lecturas autenticadas y
   configuración administrativa versionada. No existe endpoint público de inyección.
3. [Integraciones](contracts/integrations.md): reglas puras 001 → orquestación/almacenamiento
   002 → consultas 001; transporte 003 como llamador. Consumo no importa notificaciones.
4. [UI](contracts/ui.md): siete categorías, filtros, estado, gráfico/tabla y configuración.
5. [Quickstart](quickstart.md): guía ejecutable una vez implementadas las dependencias,
   con resultados conocidos y evidencia pendiente explícita.

### Prerrequisitos por capacidad

| Capacidad | Propietario/documento | Ruta prevista / condición |
| --- | --- | --- |
| Scaffold, DB/UoW, reloj, eventos, build y operación | [009](../009-fundaciones-plataforma/plan.md) | `core/`, `audit/`, `main.py`, manifiestos; pendientes reales, no creados en 001. |
| Sesión, CSRF, permiso de consulta/configuración y shell administrativo | [006](../006-acceso-usuarios-rbac/spec.md) | `identity/` y UI de acceso; dobles solo para pruebas aisladas. |
| Aceptación, almacenamiento, bloqueo, límites históricos de reconfiguración, límite temporal e incorporación calculada | [002](../002-registro-retencion-consumo/spec.md) y [puerto acordado](contracts/integrations.md) | `consumption/reception.py`, proveedor `MeasurementStore.read_reconfiguration_bounds`, almacenamiento y migraciones de mediciones; diseño propio aún requerido, sin implementar esos proveedores desde 001. |
| Agregados/cobertura, retención y ventanas de consumidores | [002](../002-registro-retencion-consumo/spec.md) | `consumption/aggregates.py`, `retention.py`; no implementarlos desde esta spec. |
| Archivos nativos, entrega completa y SFTP | [003](../003-simulador-pas600-sftp/spec.md) | Adaptador de recepción por definir por 003; fixtures llaman al puerto real sin acreditar SFTP. |
| Emisor técnico y visores | [007](../007-observabilidad-externa/spec.md) | `observability/`; instrumentar el módulo al existir el emisor, sin bloquear consultas por visores caídos. |

### Orden y trazabilidad de las tareas

Primero contratos/reglas puras y catálogo; después integración de persistencia real de 002
y permisos de 006; a continuación consultas/UI P1, filtros/estados P2 y aceptación
transversal. No esperar la aceptación completa de 001 para comenzar 002: recibe reglas
de dominio y contratos; 001 recibe su almacenamiento. No ejecutar automáticamente tareas
de otras funcionalidades. El flujo de planificación produjo el diseño; la posterior
generación de tareas lo concreta en 61 tareas organizadas por las cuatro historias.

| Alcance | FR / SC | Diseño y verificación prevista |
| --- | --- | --- |
| US1, catálogo/configuración/ambas vistas | FR-001/006..010; SC-001/002/005 | Modelo, HTTP, UI; fixtures de tres intervalos por categoría, total 100 frente a parciales 60, total calculado 12+8 y prueba humana. |
| US2, datos confiables | FR-002..006/010; SC-003 | Puerto de recepción, equivalencia, conflicto, solapamiento, unidades y concurrencia PostgreSQL con 002. |
| US3, período y zona | FR-011..013; SC-002/004 | Contención, aviso de cruces, período inicial global, rango inválido, DST y zona distinta del navegador. |
| US4, estados y aislamiento | FR-014..016; SC-004 | Cero/ausencia/sin medidor/incompleto, un punto, huecos, error/reintento y carreras de solicitudes. |
| Local/VPS/acceso | FR-017..019; SC-006/007 | Contratos reales locales; perfiles de integración 003/007/008 cuando existan, HTTPS y red externa en aceptación final. |
| Traslado 008 → 001 | [Trazabilidad en tasks.md](tasks.md#trazabilidad-del-traslado), T001/T002/T003 del borrador anterior de 001 | Pruebas semánticas, catálogo/validación y consulta/CAT-01 conservados e integrados en las cuatro historias; siguen pendientes. |

La lista integral [tasks.md](tasks.md) ya fue generada con `$speckit-tasks`; sus marcas y la evidencia vigente reflejan el trabajo realizado y pendiente. Revisar la consistencia entre artefactos y satisfacer los
gates de capacidad aplicables antes de implementar; la generación no acredita aceptación.

## Complexity Tracking

Sin violaciones que justificar. SVG y un único resultado evitan añadir un subsistema de
gráficos o una segunda serie de consumo; la persistencia incorporada sigue en 002.
