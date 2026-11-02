# Implementation Plan: Registro temporal y retención del consumo

**Branch**: `002-registro-retencion-consumo` (identificador devuelto por Spec Kit);
rama Git actual: `develop`, sin creación de rama.
**Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: `specs/002-registro-retencion-consumo/spec.md` y las cinco tareas del borrador
trasladado, conservadas en la trazabilidad de [tasks.md](tasks.md).
**Estado**: diseño revisado y 25/71 tareas implementadas/verificadas localmente.
Fundaciones y recepción interna disponibles; T024/T025 parciales, US2–US4 y aceptación
integral pendientes. [Evidencia y gates](validation/acceptance.md).

## Contexto compartido del proyecto (ECS-EC)

Aplican [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y constitución v1.0.0 en
`.specify/memory/constitution.md`. La spec-009 posee plataforma/auditoría; 006,
identidad; 001, catálogo/fuentes, validación y cálculo puro CAT-01; 002, recepción,
almacenamiento, agregados y conservación; 003, adquisición PAS600/SFTP; 007,
instrumentación común; 008, notificaciones. La plataforma, identidad, dominio/configuración001 y proveedores internos002 existen;
la fachada/UI001 y las capacidades externas pendientes se detallan en la evidencia.

## Summary

Incorporar por categoría novedades válidas con separación mínima de 900 segundos,
independencia entre categorías e idempotencia durable. Reutilizar reglas 001 y conservar
la primera aceptación física o incorporación calculada. Mantener hora/día/mes/año
con energía exacta y cobertura real, y ampliar la página de consumo existente para
alternar detalle y agrupaciones conservando categoría/filtro y una respuesta común
para gráfico y tabla.

El adaptador confiable persiste `attempt_id` y entrada canónica antes de `Reception.accept`;
`Reception.read_attempt` consulta resultados sin efectos y permite distinguir inexistencia
de fallo. La recuperación completa solo lo no confirmado con el mismo ID/entrada;
un reenvío explícito crea otro intento, incluso después de un `too_early` confirmado.
El [contrato interno](contracts/integrations.md) fija firma, exclusión concurrente y
`attempt_payload_conflict`; estos puertos y su almacenamiento siguen siendo de002.

Cada incorporación confirma en PostgreSQL medición/total, estado de recepción,
contribuciones, agregados afectados y eventos comunes en la misma transacción.
CAT-01 calculada tiene su propio límite y solicitudes de evaluación durables, confirmadas
con las parciales antes de existir candidato. Un trabajo del `lifespan` recupera esas
solicitudes y los candidatos pendientes de incorporación, sin reenvío de la fuente.
La conservación mínima usa el aniversario de doce meses en la zona
del edificio. Un registro auxiliar durable mantiene identidad, intervalos y aportes aun
tras una retirada permitida del detalle; los agregados protegidos no dependen de volver
a sumar el detalle restante.

## Technical Context

**Language/Version**: CPython 3.14 con GIL; TypeScript, React 19.x y Next.js 16.x,
según arquitectura. No se cambia la selección compartida.

**Primary Dependencies**: FastAPI 0.162.0, Pydantic 2, Uvicorn, SQLAlchemy 2,
Psycopg 3 asíncrono, Alembic; `zoneinfo`/tzdata; utilidades 009 de reloj/UoW/aniversario;
`decimal.js` y componentes 001 para proyección gráfica. Versiones restantes/locks se
resuelven al implementar plataforma, sin afirmar ejecución compatible desde este plan.

**Storage**: PostgreSQL 18 real; UUID, `timestamptz`, NUMERIC exacto sin escala coercitiva,
rangos `[inicio,fin)`, unicidad y exclusión GiST. La migración propia requiere
`btree_gist` disponible y se enlaza al head real; no recrea tablas 001/009.

**Testing**: pytest/HTTPX, PostgreSQL real para concurrencia y retirada; Vitest/Testing
Library y Playwright para correspondencia UI/API. Reloj y tzdata controlados en pruebas.
Evaluación con personas para SC-005; todavía sin resultados.

**Target Platform**: Linux/Docker Compose y VPS posterior; frontend estático servido
por FastAPI desde la misma imagen/proceso inicial. Sin worker externo.

**Project Type**: aplicación web monolítica modular.

**Performance Goals**: la spec no aprueba SLO de latencia ni caudal. La siguiente consulta
iniciada después del commit debe reflejar las novedades y cobertura; SC-005 exige
9/10 tareas humanas correctas en <=60 s. Medir consultas con >=12 meses de siete
categorías sin inventar un objetivo de rendimiento.

**Constraints**: 900 segundos transcurridos por categoría, no por medición; sin máximo
entre envíos; cero y ausencia distintos; solo contención completa; ninguna estimación;
doce meses calendario desde aceptación/incorporación sustantiva, sin borrado obligatorio.
Zona IANA obligatoria de configuración; `America/Santiago` es solo fixture.
Estado temporal independiente de cobertura: `not_started` antes del inicio,
`ongoing` desde el inicio incluido hasta fin excluido, `finished` desde el fin incluido.
Conservar bloques futuros contenidos y el filtro, sin etiquetarlos “En curso”.

**Scale/Scope**: un edificio, siete categorías fijas, cuatro granularidades y detalle.
Un lote puede contener muchas lecturas; la cadencia no impone duración mínima a estas.
Sumas de agregados usan coeficientes enteros de quantum `10^-15 kWh`, sin heredar el
contexto 50 de la suma de hasta seis contribuciones 001.

## Constitution Check

Puerta previa a investigación y revisión posterior al diseño:

| Principio / restricción | Antes de fase 0 | Después de fase 1 / evidencia |
| --- | --- | --- |
| I. Monitoreo y fuentes explícitas | PASS: amplía historial de las siete categorías; no supone siete medidores. | PASS: [integraciones](contracts/integrations.md) conserva identidad, revisión y frontera 003. |
| II. Monolito modular | PASS: almacenamiento y trabajo interno en consumo. | PASS: UoW/lifespan comunes; sin servicio propio ni dependencia inversa de 008. |
| III. Documentación integral | PASS: se exige documentación de archivos, clases, funciones/componentes y pruebas en el mismo cambio. | PASS de diseño: contratos, fórmulas, guía reproducible y responsabilidades definidos; revisión del código pendiente. |
| IV. Integridad/trazabilidad | PASS: reglas 001, rechazo/duplicado, intervalos y zona explícitos. | PASS: [modelo](data-model.md), registro durable, cobertura exacta, pruebas de calendario y conservación. |
| V. Visualización verificable | PASS: gráfico/tabla comparten respuesta y filtro. | PASS: [UI](contracts/ui.md), cero/ausencia, offsets, estados separados y pruebas con fuente conocida. |
| Pila, alcance y garantías aprobadas | PASS: adopta arquitectura, sin SLO nuevo. | PASS: ninguna capacidad ajena incorporada al setup; configuración real y aceptación externa pendientes. |

No hay desviaciones constitucionales ni aclaraciones de diseño pendientes. Confirmar zona,
fuentes y credenciales reales es prerrequisito de instalación, no una decisión de producto
inventada. La compatibilidad física de fuentes y reenvíos se valida con 003 antes de
afirmar recepción PAS600/SFTP.

## Project Structure

### Documentation (this feature)

```text
specs/002-registro-retencion-consumo/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http.md
│   ├── integrations.md
│   └── ui.md
└── tasks.md                 # lista integral; conserva trazabilidad del borrador
```

### Source Code (repository root, this feature)

Rutas previstas; no acreditan implementación:

```text
backend/src/ecs_ec/consumption/
├── models.py                # ampliar con tablas propias 002, coordinado con 001
├── ports.py                 # contratos comunes 001/002
├── reception.py
├── store.py
├── aggregates.py
├── calendar.py
├── retention.py
├── pending_totals.py
├── queries.py               # ampliar fachada de lectura 001
├── schemas.py               # ampliar esquemas HTTP existentes de 001
└── router.py                # añadir consulta agrupada al router único 001
backend/migrations/versions/consumption_002_initial.py
backend/tests/{unit,integration,contract}/consumption/
frontend/src/app/consumption/page.tsx
frontend/src/components/consumption/
frontend/src/lib/api/consumption.ts
frontend/tests/{unit,e2e}/
```

**Structure Decision**: ampliar el módulo común `consumption`, sin crear otro catálogo,
validador, endpoint de inyección o página paralela. Modificar archivos compartidos y
registro de rutas/lifespan secuencialmente después de existir sus propietarios.
`consumption_002_initial.py` es nombre orientativo, no revisión global reservada.

## Phase 0 — Investigación y decisiones

[research.md](research.md) resuelve coordinación, reloj, idempotencia, calendario,
exactitud, retención, pendientes y contratos con consumidores, con fuentes primarias.
Los puertos puros 001 y los de almacenamiento 002 rompen la dependencia de aceptación
completa entre ambas specs. Toda lectura compuesta usa una captura REPEATABLE READ;
las escrituras coordinadas usan READ COMMITTED y estado leído después de bloqueos.

## Phase 1 — Diseño y contratos

1. [data-model.md](data-model.md): recepción por categoría, evidencia durable,
   mediciones/totales conservados, `TotalEvaluationRequest` antes del candidato,
   pendientes de incorporación, agregados y plazos.
2. [contracts/integrations.md](contracts/integrations.md): recepción interna, puertos
   requeridos por 001/004/005/008, eventos 009 y recuperación.
3. [contracts/http.md](contracts/http.md): GET agrupado autenticado, parámetros, campos,
   fórmulas y errores. El detalle/configuración conserva el contrato 001.
4. [contracts/ui.md](contracts/ui.md): selector Detalle/Hora/Día/Mes/Año, estados,
   cobertura/procedencia y coherencia entre vistas.
5. [quickstart.md](quickstart.md): comandos previstos, escenarios verificables,
   prerrequisitos reales y evidencia de aceptación aún pendiente.

## Dependencias y orden de implementación para la siguiente fase

| Capacidad / documento propietario | Integración 002 | Condición |
| --- | --- | --- |
| Plataforma009: [plan](../009-fundaciones-plataforma/plan.md), [contrato](../009-fundaciones-plataforma/contracts/integrations.md) | `core` UoW/reloj/aniversario, `audit` y registro de ciclo de vida | Debe existir realmente antes de migraciones/pruebas integradas; 002 no implementa plataforma. |
| Consumo001: [modelo](../001-visualizar-consumo-categorias/data-model.md), [puertos](../001-visualizar-consumo-categorias/contracts/integrations.md) | Catálogo/configuración, validación y cálculo puros; ampliar modelos/consultas/puertos/esquemas y el router único `backend/src/ecs_ec/consumption/router.py` con su UI | Acordar puertos primero; implementar capacidades coordinadamente, sin ciclo de aceptación completa. |
| Identidad006: [spec](../006-acceso-usuarios-rbac/spec.md) | Sesión/autorización de GET y protección de UI | Necesaria para aceptación web; sin crear cuentas/permisos propios. |
| Adquisición003: [spec](../003-simulador-pas600-sftp/spec.md) | Publicaciones lógicas, identidad y reenvío tras rechazo temporal | Fixtures internos permiten comenzar; aceptación SFTP espera adaptador real. |
| Observabilidad007: [spec](../007-observabilidad-externa/spec.md) | Señales saneadas de recepción/consulta/trabajo/retirada | Instrumentación al existir emisor; los visores no condicionan commits ni consultas. |
| Consumidores004/005/008 | Puertos de lectura y eventos documentados | 002 produce datos reales sin implementar costos, PDF, reglas ni SMTP. |

Orden: contratos/fixtures y coordinación 001/009 → pruebas y aceptación persistida US1 →
agregados/calendario y consulta US2 → conservación/retirada US3 → completar estados,
datos tardíos e integración UI US4 → verificación transversal, documentación y SC-005.
Los casos incompletos y exactitud se prueban desde el primer agregado; US4 integra su
presentación. Las pruebas de nuevas reglas se escriben antes de su implementación.
Las tareas sitúan esquema, calendario, escritor de aportes y vencimientos iniciales en
fundaciones compartidas: US1 debe confirmar agregados/plazos atómicamente desde su
primera incorporación. US2 añade proyecciones/API/UI; US3 completa dependientes y retirada.
La ruta del router se concilia con el plan 001, sin crear un archivo de API alternativo.

## Trazabilidad del alcance completo y del traslado

| Historia / requisitos | Diseño y validación |
| --- | --- |
| US1, FR-001..006/014, SC-001 | Recepción/bloqueos/solicitudes/pendientes, PostgreSQL concurrente, 14m59s/15m, siete categorías y recuperación sin reenvío tras caída antes del candidato. |
| US2, FR-007..013, SC-002 | Cuatro calendarios, contención, origen CAT-01, fórmulas exactas, selector y gráfico/tabla. |
| US3, FR-015..019, SC-004 | Aniversario, registros tardíos, referencias protegidas, retirada y deduplicación posterior. |
| US4, FR-010..014/019, SC-003 | Huecos/ceros/futuros/en curso/terminados, fronteras inicio/fin, exclusiones y siguiente lectura tras commit tardío. |
| Todas, SC-005 | Diez tareas humanas en ambas vistas; >=9 correctas sin ayuda en <=60 s. |
| Traslado 002 T001/T002, procedente de 008 T010/T020 | Conservar pruebas de recepción y persistencia/límite; ampliar para todos los resultados y pendientes calculados. |
| Traslado 002 T003/T004, procedente de 008 T010/T021 | Conservar agregados, cobertura y última ventana admisible; añadir UI, calendario y contratos completos. |
| Traslado 002 T005 | Conservar retención con helper 009 y protección tras retirada; ampliar pruebas de referencias/ledger y los nueve escenarios US3. |

Los IDs anteriores solo identifican procedencia del borrador. [tasks.md](tasks.md) ya
contiene las cuatro historias, fundaciones/cierre, dependencias y trazabilidad de las
cinco tareas trasladadas. Las marcas actuales corresponden a la ejecución descrita en
[aceptación parcial](validation/acceptance.md); el resto sigue pendiente. No se marcan
checklists por generar documentos o por implementar tareas.

## Complexity Tracking

Sin infracciones que justificar. El registro durable de aportes evita perder idempotencia,
exclusión y agregados al retirar detalle; los pendientes calculados hacen cumplir
simultáneamente los contratos 001 y el límite propio de CAT-01.
