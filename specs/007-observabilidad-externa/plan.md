# Implementation Plan: Observabilidad técnica externa y Programador

**Branch de contexto Spec Kit**: `007-observabilidad-externa` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Rama Git real**: `develop`; setup resuelve el identificador de funcionalidad, sin crear
ni cambiar una rama Git. **Estado**: fases 0/1 de diseño; implementación y aceptación pendientes.

## Contexto compartido del proyecto (ECS-EC)

Aplican [arquitectura](../../docs/architecture.md), [hoja de ruta](../../docs/implementation-roadmap.md),
[AGENTS.md](../../AGENTS.md) y [constitución 1.0.0](../../.specify/memory/constitution.md).
Se leyó el borrador de tareas y se conservó su trabajo y procedencia. El archivo actual
de [tareas integrales](tasks.md) cubre las cuatro historias; revisión de consistencia,
implementación y aceptación siguen pendientes.

## Summary

Instrumentar el monolito para emitir logs estructurados, métricas derivadas y trazas sin
condicionar sus resultados funcionales. Loguru emite JSON saneado mediante una cola
acotada y spool rotativo; Alloy lo lleva a Loki, Grafana muestra logs y métricas LogQL;
OpenTelemetry exporta OTLP a Jaeger 2.22 con Badger persistente. Nginx es la frontera
técnica de infraestructura: Programador consulta mediante Basic sobre TLS, con autorización
externa individual por entorno y revisión en cada petición. No hay visor funcional ni
perfil Programador asignable desde identidad006.

La [investigación](research.md) completa las decisiones trasladadas. Los contratos definen
[emisión y cobertura](contracts/integrations.md), [métricas](contracts/signals.md)
y [acceso, políticas y despliegue](contracts/technical-access.md). La cobertura incompleta
limita explícitamente las métricas derivadas de logs; no se añade un almacén de métricas nativas.

Un intento002 parcialmente fallido conserva su identidad al recuperarse y solo cierra
su ejecución técnica; `reception.completed` corresponde al cierre lógico durable con
resumen completo. Operaciones y ejecuciones tienen proporciones de error separadas.
El heartbeat distingue recolección de logs y exportación OTLP, mientras los visores
contrastan cobertura propia de cada señal con lo efectivamente consultable.

## Technical Context

**Language/Version**: CPython 3.14 convencional con GIL, `>=3.14,<3.15`; configuración
Alloy, YAML, JSON y Nginx. React 19/Next.js 16 para el frontend funcional común, sin páginas nuevas.

**Primary Dependencies**: FastAPI `0.162.0` y lifespan común de 009; Loguru, OpenTelemetry
API/SDK y exportador OTLP/HTTP; Alloy, Loki TSDB, Grafana, Nginx; Jaeger `2.22.0`/Badger.
Las versiones restantes, lockfile y digests se fijan y prueban al implementar sobre
CPython 3.14; la investigación no acredita ejecución ni compatibilidad del conjunto.

**Storage**: colas en memoria, spool JSON rotativo, posiciones persistentes de Alloy,
Loki filesystem/TSDB y Badger en volúmenes distintos por entorno. Sin tablas ni
migraciones SQL propias; consume referencias de trabajo de los productores. PostgreSQL
18 y auditoría durable pertenecen a 009 y sus dominios.

**Testing**: pytest/HTTPX/jsonschema, PostgreSQL real para resultados y aislamiento;
Docker Compose con stack técnico real; Playwright para navegación técnica y aislamiento
funcional. Fixtures internas, fallos, saturación, reinicio, reenvío, retención, redacción,
revocación y diez tareas con Programadores para SC-008.

**Target Platform**: Linux/Compose local, un proceso Uvicorn y una imagen de aplicación;
VPS posterior con HTTPS. Los componentes técnicos son infraestructura opcional.

**Project Type**: módulo interno del monolito web e infraestructura externa de consulta.

**Performance Goals**: sin SLO de latencia nuevo. Verificar admisión sin espera por red/disco:
1024 logs de <=16 KiB, 2048 spans pendientes, exportador con timeout 5 s, heartbeat cada
15 s y continuidad desconocida tras 45 s. Diez consultas de referencia producen ocho
éxitos, dos fallos y 20 % de error con cobertura íntegra. Límites adicionales en contrato técnico.

**Constraints**: saneamiento antes de cualquier cola/almacenamiento; sin cuerpos,
credenciales, valores energéticos/financieros ni datos personales. Revocación antes de
la siguiente consulta; sin streams largos que eludan revalidación. Credenciales humanas,
funcionales y de ingesta separadas. Retención técnica 168 h, perfil desechable 24 h,
trazas al 100 % en aceptación; no heredar los 12 meses funcionales.

**Scale/Scope**: un edificio por despliegue inicial, un emisor y stack técnico por entorno;
cobertura real de operaciones 001–006. Dimensiones cerradas; referencias únicas solo
como campos. 008 añade su instrumentación después y no es prerrequisito de 007.

## Constitution Check

Gate previo a fase 0 y reevaluación posterior a fase 1:

| Principio / restricción | Diseño y evidencia prevista | Antes | Después |
| --- | --- | --- | --- |
| I. Propósito | Diagnóstico de recepción, consumo, costos, PDF e identidad; sin inventar fuentes o frecuencias energéticas. | PASS | PASS |
| II. Monolito modular | Emisor y trabajos en lifespan; colectores, visores y gateway son infraestructura, sin worker de negocio nuevo. | PASS | PASS |
| III. Documentación | Contratos, catálogo, guía y procedimientos acompañarán cada módulo, función, prueba, dashboard y script implementado. | PASS | PASS |
| IV. Integridad/trazabilidad | UTC y reloj monotónico; referencias confiables, resultados tipados, cobertura y pérdidas; sin alterar fuentes ni auditoría funcional. | PASS | PASS |
| V. Presentación verificable | Visores externos con unidad, ventana, entorno y limitaciones; distinguen cero observado y ausencia. | PASS | PASS |
| Web, pila y rendimiento | Acceso web separado; selección investigada; sin prometer SLO no aprobado. | PASS | PASS |
| Propiedad y aceptación | Capacidades ajenas como prerrequisitos; pruebas reales pendientes, ninguna checklist de revisión marcada. | PASS | PASS |

Sin desviaciones constitucionales ni aclaraciones abiertas de diseño. Los PASS evalúan
el diseño; no certifican implementación, seguridad desplegada o aceptación.

## Project Structure

### Documentation (this feature)

```text
specs/007-observabilidad-externa/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── integrations.md
│   ├── signals.md
│   ├── technical-access.md
│   └── log-event.schema.json
└── tasks.md                 # tareas integrales; traslado conservado y pendiente
```

### Source Code (repository root, this feature)

Rutas previstas; todavía no existen implementaciones de aplicación:

```text
backend/src/ecs_ec/observability/
├── __init__.py
├── context.py               # referencias, contextvars y continuidad confiable
├── events.py                # catálogo y validación del sobre
├── sanitization.py          # allowlist antes de emitir
├── logging.py               # cola no bloqueante, spool y pérdidas
├── tracing.py               # spans de dominio y exportación OTLP por lotes
├── health.py                # heartbeat, secuencias y limitaciones
└── lifecycle.py             # registro en lifespan común
backend/tests/{unit,integration,contract}/observability/
backend/tests/integration/test_observability_isolation.py
scripts/observability/{prepare_local.sh,manage_programmer.sh}
deploy/technical-gateway/{nginx.conf,README.md}
deploy/observability/
├── alloy.alloy
├── loki.yaml
├── jaeger.yaml
├── grafana/{grafana.ini,provisioning/,dashboards/platform.json}
└── README.md
frontend/tests/e2e/observability-isolation.spec.ts
```

**Structure Decision**: 009 conserva scaffold, core, auditoría y composición inicial.
007 registra su lifecycle e integra el perfil opcional `observability` en `compose.yaml`
después de existir plataforma, con cambios secuenciales en archivos compartidos.
Cada productor incorpora instrumentación en su módulo, sin reimplementar negocio.
Sin migraciones ni frontend funcional propios; Grafana/Jaeger sirven las vistas técnicas.
Los scripts auxiliares preparan recursos técnicos, no usuarios ni datos funcionales.

## Phase 0 — Research

Resueltas selección heredada, límites de Loguru/OTel, deduplicación y cobertura,
autorización por entorno, consultas, conservación y compatibilidad pendiente de ejecución.
Se consultaron fuentes primarias y se delegó investigación conforme a la skill.
Resultado: [research.md](research.md); se conservan los anclajes citados desde otras specs.

## Phase 1 — Diseño e integración

1. Emisor sobre plataforma009: sobre, sanitización, contexto, colas, spool, spans,
   heartbeat y cierre acotado, verificables con receptores detenidos.
2. US1: gateway local TLS, provisión/revocación externa, Grafana Viewer, consultas de
   Jaeger/Loki y denegaciones directas/funcionales/entre entornos.
3. US2/US3: almacenamiento y dashboard, catálogo y navegación agregado → eventos → trazas.
   Vincular instrumentación a productores reales cuando existan.
4. US4: privacidad, saturación, pérdidas, retención, muestreo y operación local sin servicios
   remotos. SC-008 requiere personas; no lo sustituye una prueba E2E.

Después de la aceptación local técnica de T060, T061 (personas) y la cadena documental
T062→T063→T064 pueden avanzar por separado. T065 conserva ambos prerrequisitos, T061 y
T064: documentación completada no equivale a SC-008 ni a aceptación integral.

El [modelo](data-model.md) y los contratos completan esta fase. La generación posterior
con `$speckit-tasks` ya produjo la [lista integral](tasks.md), conservando el traslado;
no se ejecutaron tareas de implementación por generar esos documentos.

### Prerrequisitos por capacidad y propietario

| Capacidad externa | Documento / ruta prevista | Qué habilita |
| --- | --- | --- |
| Scaffold, configuración, reloj, lifecycle, DB/UoW | [009 plan](../009-fundaciones-plataforma/plan.md); `backend/src/ecs_ec/core/`, `main.py`, `compose.yaml` | Emisor y perfil técnico. No implementar plataforma desde 007. |
| Evidencia/eventos funcionales durables | [009 integración](../009-fundaciones-plataforma/contracts/integrations.md); `backend/src/ecs_ec/audit/` | Probar que caída técnica no altera commits/retención. |
| Publicación/recepción confiables | [003 SFTP](../003-simulador-pas600-sftp/contracts/sftp-reception.md); `backend/src/ecs_ec/acquisition/` | Correlación de archivos/reintentos sin modificar PAS600/SFTP. |
| Validación, consultas, conservación, agregados | [001 integración](../001-visualizar-consumo-categorias/contracts/integrations.md), [002 integración](../002-registro-retencion-consumo/contracts/integrations.md); `backend/src/ecs_ec/consumption/` | Cobertura de consumo, sin inventar receptores/series. |
| Identidad, permisos, cambios e historial | [006 integración](../006-acceso-usuarios-rbac/contracts/integrations.md); `backend/src/ecs_ec/identity/` | Aislamiento funcional y señales de acceso/administración. |
| Cálculo/contraste y PDF reales | [004 integración](../004-costos-tarifa-bt43/contracts/integrations.md), [005 integración](../005-generar-reportes-pdf/contracts/integrations.md); `backend/src/ecs_ec/costs/`, `backend/src/ecs_ec/reports/` | Cobertura completa, sin implementar productores desde 007. |

Sin ciclo: el emisor puede construirse antes de esos productores; la aceptación integral
espera su instrumentación. Los productores operan sin receptores/visores.

### Cobertura y trazabilidad

| Alcance | Artefacto principal | Validación |
| --- | --- | --- |
| US1; FR-001–004/022; SC-001 | Acceso técnico | Roles, revocación, bypass, entornos y permisos funcionales |
| US2; FR-005–007/011–014; SC-002/004 | Integraciones y modelo | Operaciones reales, rechazos, fallos, continuidad y reenvíos |
| US3; FR-008–010/014/018; SC-003 | Catálogo de señales | 10 consultas, 5 registros, distribuciones, ceros/ausencias y cardinalidad |
| US4; FR-015–024; SC-005–009 | Políticas y quickstart | Secretos sintéticos, saturación, retención, muestreo, personas y stack local |
| Traslado T001 de 007, antes T029 de 008 | Emisor/modelo/políticas | Cola 1024/16 KiB, heartbeat 15/45 s, OTel 2048/5 s |
| Traslado T002 de 007, infraestructura anterior de T102 de 008 | Acceso | Basic/TLS externo, Viewer, revocación y fuentes privadas |
| Traslado T003/T004 de 007, antes T100/T101 de 008 | Investigación/catálogo/despliegue | Alloy/Loki/Grafana/Jaeger, Badger, TTL y perfil opcional |
| Traslado T005 de 007, pruebas comunes anteriores de T103 de 008 | Quickstart/aislamiento | 10/8/2, 20 %, cobertura, colas, privacidad y permisos |

IDs como procedencia local a sus specs, no dependencias de ejecución. Todas las tareas
trasladadas siguen pendientes.

## Complexity Tracking

Sin violaciones que justificar. La infraestructura técnica externa respeta la unidad
del monolito y no introduce otro servicio propio de aplicación.
