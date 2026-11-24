# Punto de interrupción del paso 2 — 2026-11-23

**Registro histórico, superado por la reanudación2026-11-24:** ver
[entrega técnica y pendientes actuales](acceptance.md). Este archivo conserva el punto
exacto de interrupción y sus resultados parciales; no describe el estado final actual.

**Estado: implementación en curso; paso 2 sin terminar ni aceptar.** Este registro
responde a la petición de revisar y documentar dónde quedó el trabajo. Esta revisión
no continúa la implementación ni ejecuta nuevas suites funcionales.

Referencia: [plan priorizado, paso 2](../../../docs/implementation-priority-plan-2026-11-03.md),
[tareas005](../tasks.md) y [coordinación007](../../007-observabilidad-externa/validation/step2.md).
Los cambios permanecen en el árbol de trabajo, incluidos archivos nuevos sin seguimiento.
También hay cambios documentales y pruebas del paso 1 anteriores a este incremento;
no deben descartarse al retomar. No se realizó un commit de este incremento.

## Implementación que existe

| Capacidad | Archivos de código, relativos a la raíz | Alcance observado |
| --- | --- | --- |
| Solicitud, captura, resultado y binario | `backend/src/ecs_ec/reports/models.py`, `schemas.py`, `repository.py`; `backend/migrations/versions/reports_005_initial_reports_initial.py` | Cuatro tablas, JSONB/BYTEA, hash/longitud, restricciones e inmutabilidad. Migración `reports_005_initial`, padre `demo_calendar_admission`. |
| Admisión y fuentes | `backend/src/ecs_ec/reports/calendar.py`, `services.py`, `snapshots.py` | Selección calendario en zona del edificio, autorización, clave idempotente, captura REPEATABLE READ de002/004, retención referenciada. |
| Ejecución | `backend/src/ecs_ec/reports/worker.py`, `backend/src/ecs_ec/main.py` | Supervisor con liderazgo PostgreSQL, dos slots, render fuera de la transacción, publicación atómica y reconciliación de interrupciones. |
| Documento | `backend/src/ecs_ec/reports/{renderer,layout,preflight,charts,energy_table,financial_summary,quality,formatting,content}.py` | ReportLab real, fuente incrustada, seis secciones, A4, mínimo10pt, comprobación pypdf y manifiesto. Porcentajes de presentación a dos decimales; energía e importes conservan precisión. |
| HTTP y acceso | `backend/src/ecs_ec/reports/api.py`, `backend/src/ecs_ec/identity/api.py` | POST de admisión, GET de estado y descarga privada; sesión/CSRF/origen y no-store. `pdf.failed` se confirma con el resultado fallido mediante009. |
| Interfaz | `frontend/src/app/reportes/page.tsx`, `frontend/src/components/reports/`, `frontend/src/lib/api/reports.ts` | Formulario diario/mensual/anual, progreso/error, reintento con la misma clave ante respuesta incierta y descarga. Hay cambios adicionales en sesión, retorno seguro y estilos compartidos. |
| Observabilidad | `backend/src/ecs_ec/observability/lifecycle.py` | Ampliación común para admisión/terminal PDF, ejecución/terminal de recepción y continuación de contexto confiable. Su integración completa sigue pendiente. |
| Fixtures | `scripts/seed_report_reference.py`, `scripts/seed_costs_reference.py` | Seed nuevo con reloj controlado y procedencia mixta; el seed004 admite reloj opcional. No se ha acreditado su ejecución final. |

La existencia del código no equivale al cierre de todas las tareas que lo describen.
Se conservan los marcadores: **005:5/63;007:26/65**. Ningún checklist de revisión se
marca por esta documentación. La selección persistida sigue siendo
`specs/003-simulador-pas600-sftp`.

## Evidencia recuperada de ejecuciones parciales

Son resultados observados durante el trabajo anterior, sobre distintos cortes del
código. **No se suman ni acreditan el árbol final después de las últimas ediciones.**

| Ejecución | Resultado observado | Límite |
| --- | --- | --- |
| Contratos e integración005, primera ampliación | 19 pruebas pasan | Incluyó fuentes reales, idempotencia, fallos, revisiones financieras y emisor opcional; después hubo cambios. |
| Unitarias de reportes | 23 pasan | Extremos numéricos/nombres y rechazo de manifiesto alterado, transformación pequeña y PDF corrupto. Se corrigieron fallos previos de composición/preflight. |
| Procedencia mixta y corrección durante render | 3 pasan | Mensual/anual30kWh =10medidos+20calculados, CAT-03/CAT-05; corrección de boleta mientras renderiza conserva captura anterior. |
| Ejemplo financiero real004 | 1 pasa | Tres ciclos: disponible60; dos pares calculado40/facturado38/diferencia2. |
| Supervisor y correlación | 3 pasan | Dos renders simultáneos, reconciliación atómica/idempotente y continuación confiable. |
| Anual con doce ciclos reales | 1 pasa | PDF de una página con subtotal120000 de las fuentes. |
| Unitarias, contratos e integración005 más protocolo/correlación007 | 53 pasan | Última tanda acotada con resultado recuperado; no sustituye regresión general ni cubre las últimas ediciones. |
| Frontend Vitest | 30 archivos,90 pruebas pasan | Se hicieron cambios posteriores en la interfaz/E2E. |
| TypeScript y exportación Next | Hubo typecheck correcto y build con12 páginas estáticas | La última invocación observada de `typecheck` terminó con SIGSEGV interno en TypeScript7, al procesar información incremental. No atribuirlo todavía al código ni dar por validado el frontend final. |
| Alembic en la base aislada | Downgrade vacío, upgrade y `check` terminan correctamente; sin diferencias de esquema | No acredita despliegue ni prueba de rollback con evidencia protegida. |

Los comandos usados para la tanda de53 y el frontend fueron:

```sh
TEST_DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/pytest backend/tests/unit/reports backend/tests/contract/reports backend/tests/integration/reports backend/tests/integration/observability/test_acquisition.py backend/tests/integration/observability/test_correlation.py -q --tb=short
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/alembic -c backend/alembic.ini downgrade demo_calendar_admission
DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/alembic -c backend/alembic.ini upgrade head
DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/alembic -c backend/alembic.ini check
```

El downgrade se ejecutó exclusivamente sobre la base descartable sin reportes; no
es un procedimiento para revertir una instalación con evidencia retenida.

Se inició además una regresión backend general, excluyendo las pruebas largas
`test_real_time_publication.py`/`test_restore.py` y los archivos007 que reexportan
pruebas ya ejecutadas desde sus propietarios. **No se recuperó su resultado final**;
queda pendiente una ejecución con salida persistida. La caché local `lastfailed`
contiene tres entradas de consumo: `test_crossing_rows_and_diagnostics` y dos casos
de `test_original_deadline_and_read_at_anniversary`. La caché no prueba que sean
regresiones de este incremento ni informa el resultado completo de esa ejecución.

## Qué no está acreditado

- No se ejecutó `frontend/tests/e2e/reports.spec.ts`. Su archivo ya existe; aún debe
  validar las tres escalas, descarga, respuesta incierta, sesión y retorno seguro.
- No hay capturas de navegador ni revisión visual desktop/móvil del resultado final.
  Tampoco revisión física de impresión A4 al100%, apertura offline ni personas.
- Falta contrastar toda la matriz financiera, cambios de fuente/base dentro del mismo
  modo, diagnóstico no numérico, total anual1200 con detalle mensual retirado,
  cobertura de DST del gráfico y reproducibilidad al mismo corte.
- El caso1200 en `test_quality_provenance.py` es una prueba unitaria con snapshot
  sintético; no acredita retirada histórica mediante el proveedor002 real.
- El seed no ha demostrado aún todos los escenarios de005:T055, incluidas revisiones
  financieras pendientes y extremos. No usarlo sobre una base con trabajo ajeno.
- Las pruebas007 de recepción llaman explícitamente al emisor desde el test sobre
  resultados reales002. No acreditan que002/003 tengan instalado el adaptador de
  recuperación/terminal:002:T065 y003:T072 pertenecen al paso3.
- `test_costs_reports.py` y `test_identity_administration.py` de007 reexportan pruebas
  de propietarios; no completan toda la cobertura propia004/007:T034/T035.
- No hay matriz final FR/SC, aceptación US1–US4, imagen final validada ni despliegue.
  Los archivos de aceptación previstos por005:T027/T037/T046/T054/T056–T060 siguen
  pendientes. SMTP/008 no es requisito para terminar este productor.

## Revisión de código pendiente al retomar

1. Revisar el árbol final antes de más desarrollo. `worker.py` contiene dos bloques
   consecutivos que vuelven a asignar la misma retención de solicitud/captura; hay
   una importación duplicada de `IncorporatedRecord` en el test007 de recepción.
   Documentar y eliminar duplicaciones cuando se autorice continuar implementando.
2. Volver a probar los últimos cambios en terminales007, tiempos/resultados de etapas,
   captura fallida sin duración de claim y presentación de fechas locales. Son
   posteriores a algunas tandas verdes citadas arriba.
3. Revisar la estabilidad del hash funcional: el snapshot financiero tipado contiene
   metadatos de retención y la protección referenciada puede extenderlos. Falta una
   prueba que demuestre equivalencia de datos/revisiones/corte tras esa protección.
4. Verificar liberación de handles técnicos ante rollback/error de publicación y
   reconciliación, integridad de transiciones y rollback de migración con reportes.
5. Investigar el fallo interno de TypeScript y resolver las entradas de caché de
   consumo con resultados nuevos; no modificar reglas de negocio para ocultarlas.

## Orden concreto para continuar

1. Revisar esas inconsistencias y repetir la tanda acotada005/007 sobre PostgreSQL
   aislado, guardando salida y código de salida para el árbol exacto que se entregue.
2. Completar/verificar seed y escenarios faltantes de contenido, calidad, finanzas,
   retención y concurrencia; reconciliar su cobertura con005:T006–T054/T061–T063 y
   los prerrequisitos reales007:T031–T035/T037/T038.
3. Obtener typecheck, unitarias y build finales; ejecutar el E2E existente y revisar
   capturas desktop/móvil y PDFs reales. Completar apertura offline.
4. Ejecutar la regresión general y validación de migraciones/imagen. Con evidencia
   suficiente, actualizar tareas y matrices de aceptación por propietario.
5. Mantener005:T037/T058/T059 pendientes en su alcance físico/humano no realizado.
   No avanzar al cierre de pasos3/4 como sustituto de terminar este paso2.

## Entorno al detenerse

La base usada antes fue `ecs_step2_test`, en el contenedor propio `ecs-step2-test`,
puerto55462, PostgreSQL18.3. En la consulta Docker de esta revisión **ese contenedor
ya no aparece**; solo aparecen `ecs-ec-app-1`, `ecs-ec-simulator-1` y `ecs-ec-db-1`.
No se eliminó ni modificó ningún contenedor en esta revisión. La carpeta temporal
`/tmp/ecs-step2-browser` no contiene evidencia recuperable en el corte actual.
Al retomar habrá que provisionar otra base aislada y aplicar migraciones; no usar
la base de la aplicación como sustituto ni asumir que sobreviven procesos/fixtures.

La revisión actual solo comprobó archivos, marcadores, sintaxis AST de21 módulos,
`git diff --check` y estado Docker. No ejecutó pruebas funcionales nuevas ni cambió
implementación, selección de Spec Kit o checklists.
