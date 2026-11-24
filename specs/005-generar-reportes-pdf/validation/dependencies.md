# Dependencias reales e incremento de preparación — 2026-11-02

## Disponibilidad actualizada — 2026-11-24

Productores001/002/004/006/009 disponibles; generación005 y ampliación común007
integradas y verificadas técnicamente. [Entrega y pendientes](acceptance.md).
T037/T058/T059 de005 conservan su alcance físico/humano pendiente. La evidencia de
preparación2026-11-02 que sigue es histórica, no se suma a las nuevas suites.

## Inventario005:T001 vigente

| Capacidad | Implementación real | Uso005 |
| --- | --- | --- |
| DB/UoW/reloj/retención | `backend/src/ecs_ec/core/` (009) | Sesión compartida REPEATABLE READ; no retener durante render |
| Identidad | `backend/src/ecs_ec/identity/services.py` (006) | Resolver sesión actual; `require_report_access`, `authorize(..., 'reports.generate', ...)` |
| Consumo | `backend/src/ecs_ec/consumption/queries.py` (001/002) | `read_report_snapshot` devuelve siete categorías con detail/aggregates/procedencia; granularidad hour/day/month/year |
| Costos | `backend/src/ecs_ec/costs/services.py`, `snapshots.py`, `schemas.py` (004) | `Costs.read_snapshot` con `unit_of_work`; devuelve `CostsSnapshot`, ciclos y comparación del par exacto |
| Eventos | `backend/src/ecs_ec/audit/events.py` (009) | `EventWriter.append(uow,event)`, no firma invertida; registro005 de `pdf.failed` en `reports/repository.py`, con pruebas parciales de atomicidad |
| Emisor común | `backend/src/ecs_ec/observability/{logging,tracing,lifecycle}.py` (007) existentes y registrados desde `main.py` | Operaciones ordinarias y código nuevo de terminales/continuación PDF; 005:T062/T063 verificados; cierre integral007:T037/T038 sujeto a sus prerrequisitos y cobertura por propietario. [Estado007](../../007-observabilidad-externa/validation/step2.md). |

Los [contratos007](../../007-observabilidad-externa/contracts/) y sus
[tareas](../../007-observabilidad-externa/tasks.md) conservan la propiedad de la capacidad
pendiente. No se alteran marcadores de otras specs ni se exige SMTP/008.

## Preparación y pruebas históricas — 2026-11-02

- Puertos005 documentados en `backend/src/ecs_ec/reports/ports.py`.
- Dependencias ReportLab5.1.0/pypdf6.21.4 instaladas con `uv add` bajo CPython3.14.
  Fuente DejaVuSans2.37 y licencia versionadas; prueba de incrustación y texto español.
- Ruta estática `/reportes/` preparada bajo SessionGuard006; informa indisponibilidad.
  No hay todavía formulario ni endpoint de generación/descarga.
- Fixtures existentes `costs_environment`, `costs_client`, `database`, `test_url`
  reutilizadas sin modificar sus salvaguardas: URL PostgreSQL explícita, sufijo `_test`
  y base distinta de aplicación. Entradas conocidas a través de recepción002 real.
- `capture_sources` es un adaptador **parcial de T014**: copia evidencias tipadas de
  totales/gráfico/costos, en la misma UoW, sin recalcular energía ni BT4.3.
  Totales y gráfico usan granularidades separadas. Falta la proyección inmutable,
  hash y persistencia; T014 permanece pendiente.

## Evidencia reproducible

Usando la base descartable del contenedor local `ecs-spec004-test`, puerto55452,
con credenciales recuperadas internamente sin imprimirlas y las comprobaciones de
`checked_test_url` activas:

```sh
TEST_DATABASE_URL="$REPORTS_TEST_DATABASE_URL" uv run --locked pytest backend/tests/integration/reports/test_source_capture.py backend/tests/unit/reports -q
npm --prefix frontend run test -- tests/unit/reports.test.tsx
npm --prefix frontend run typecheck
```

Resultados: **4 backend pasan**, **1 frontend pasa**, TypeScript sin errores.
La captura real verifica1000kWh, siete categorías, identidad del cálculo persistido,
boleta ausente y contraste vacío. READ COMMITTED es rechazado antes de consultar fuentes.
El período de referencia usa diciembre local de Santiago; medianoche UTC del1enero
pertenece al31diciembre local. No se confunden límites UTC con meses locales.

`.gitignore` y `.dockerignore` existentes cubren secretos, entornos, dependencias y
salidas. Frontend es privado (`private:true`); no requiere `.npmignore`.
La imagen ya copia todo `backend/` e instala el lock: incluye fuentes sin carpeta
pública para futuros binarios. No se ha construido la imagen en esta validación.

## Pendientes actuales

005:T037/T058/T059 (impresión física/personas y componente físico de revisión).
[Resultados y orden posterior](acceptance.md). La matriz integral007 sigue en su
propietario; la capacidad común usada por005 ya está implementada y verificada.
