# Entrega técnica005 — 2026-11-24

**60/63 tareas completas. Generación/descarga real disponible; sin aceptación integral.**
Pendientes:005:T037 (impresión física A4), T058 (personas) y T059 (componente físico
enlazado aT037). La apertura sin red y la revisión digital sí se comprobaron.
[Resultados legibles por máquina](artifacts/results.json), [cobertura FR/SC](coverage.md)
y [punto histórico de interrupción](implementation-checkpoint-2026-11-23.md).

## Resultado y correcciones

Se completó el productor005 dentro del monolito: captura inmutable002/004 en
REPEATABLE READ, admisión idempotente, supervisor con dos plazas, ReportLab/preflight,
resultado/BYTEA/hash atómicos, estado/descarga autorizados y formulario estático.
`pdf.failed` se confirma con su resultado sin depender de008/SMTP.

Al reanudar se eliminaron duplicaciones y se corrigieron: hash funcional sensible a
extensiones operativas de retención; liberación de handles técnicos ante rollback;
etiquetas locales/DST y horas repetidas; clasificación de rechazos/fallos técnicos;
metadatos de simulación posteriores al corte; respuesta tardía que sustituía selección;
y enlace de descarga anterior visible mientras se admitía una nueva generación.
Se quitaron el aviso «Próximamente» de Reportes y códigos de calidad sin traducir.

El build detectó una vulnerabilidad en Next16.4.3. Se fijó16.4.5 y su lockfile según
la [publicación oficial de seguridad](https://nextjs.org/blog/november-2026-security-release),
sin cambiar la arquitectura de exportación estática. Instalación npm:sin vulnerabilidades
reportadas en ese corte; no equivale a una auditoría de seguridad completa.

## Verificación ejecutada

| Comprobación | Resultado | Alcance |
| --- | --- | --- |
| Regresión backend | **627 pasan;31 omitidas** | Las omisiones corresponden al perfil técnico007 opt-in. Se excluyeron dos archivos003 largos y dos reexportaciones007, detallados abajo. |
| Suite propia005/coordinación007 | **65 pasan;1 comprobación adicional pasa** | Procedencia al corte/bloques24/31/12; después se verificó004 real sobreCAT-01 calculada sin costo completo. Los conjuntos solapan la regresión; no sumar todos los conteos. |
| Frontend | **91 pruebas/30 archivos pasan** | Typecheck correcto y build/export de12 páginas correcto. |
| Playwright | **1 recorrido pasa**,8,9s | Tres escalas, progreso, nombres/bytes, fallo durable de composición, transporte, selección y sesión/retorno. |
| Alembic | Correcto | Upgrade desde base vacía; rollback sin reportes y nuevo upgrade; `check` sin diferencias. Rollback con reportes rechazado por `report_evidence_protected`. |
| Seed ampliado | Correcto | `--financial --extremes`:002 real confirma1000,30 y1000000000000.000001kWh;004 real conservaC1/B1/K1 y dejaC1/B2 pendiente. |
| Apertura offline | Correcta | Tres PDFs abiertos en Docker con `--network none --read-only`; una página y fuentes incrustadas. |
| Imagen final | Construida | `ecs005-validation-app:local`, digest en `artifacts/results.json`. |
| Revisión documental | Correcta | Enlaces locales, sintaxis/docstrings propios y `git diff --check`; selección003 y checklists conservados. |

Salida conservada: [backend](artifacts/backend-regression.log),
[suite propia](artifacts/owned-tests.log), [caso calculado004](artifacts/calculated-cost.log), [frontend](artifacts/frontend.log),
[navegador](artifacts/browser.log), [hashes offline](artifacts/offline.json).
Entorno:CPython3.14.4, PostgreSQL18.3, Node24.22.0; ReportLab5.1.0, pypdf6.21.4,
DejaVuSans2.37 y tzdata2026.6. `uv sync --locked`:68 paquetes resueltos/66 comprobados.

## Comandos reproducibles

Usar una base PostgreSQL distinta de aplicación, con sufijo `_test`. Las fixtures
hacen limpieza destructiva exclusivamente allí. No ejecutar tandas simultáneas sobre
la misma base: sus limpiezas se interfieren. Preparar URLs/credenciales fuera del repo.

```sh
uv sync --locked
TEST_DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/pytest backend/tests -q --tb=short --ignore=backend/tests/integration/acquisition/test_real_time_publication.py --ignore=backend/tests/integration/acquisition/test_restore.py --ignore=backend/tests/integration/observability/test_costs_reports.py --ignore=backend/tests/integration/observability/test_identity_administration.py
TEST_DATABASE_URL="$REPORTS_TEST_DATABASE_URL" .venv/bin/pytest backend/tests/unit/reports backend/tests/contract/reports backend/tests/integration/reports backend/tests/contract/observability/test_instrumentation.py backend/tests/integration/observability/test_acquisition.py backend/tests/integration/observability/test_correlation.py -q --tb=short
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend test -- --run
npm --prefix frontend run build
docker build -t ecs005-validation-app:local .
```

La regresión terminó627/31; las dos reexportaciones007 evitan contar dos veces pruebas
desde sus propietarios. Las pruebas de restauración/tiempo real003 excluidas conservan
su evidencia propia y no se presentan como reejecutadas aquí. La cobertura externa007,
TTL, personas y VPS no se acreditan mediante omisiones ni estos resultados.

El E2E necesita `REPORTS_E2E=1`, `IDENTITY_E2E_PASSWORD_FILE`0600, origen en
`E2E_BASE_URL` y la aplicación real sobre una base sintética provisionada con
`scripts/seed_report_reference.py`. El harness opt-in `backend/tests/run_reports_browser.py`
usa `REPORTS_E2E_FAILURE_FILE`0600 para un fallo controlado interno, nunca accesible
por HTTP. `REPORTS_E2E_RENEWED=1` sirve al repetir sobre la misma fixture de operador
ya renovada; el test no cambia ni presume contraseñas operativas.

## Incidencias de verificación, ya delimitadas

Hubo un SIGSEGV de CPython al cargar dependencias durante una primera tanda y fallos
internos de compilación/caché en herramientas JS. La regresión final y las verificaciones
citadas terminaron correctamente. Se limpió únicamente la caché generada de Vitest;
no se alteraron reglas de negocio para ocultar errores. El test de plataforma ahora
ignora `.env` y desactiva identidad explícitamente para probar el scaffold base404.

Una tanda solapada por error con otra sobre la misma base produjo interferencias;
se interrumpió y sus resultados se descartaron. Los627/31 y65 citados proceden de
las tandas posteriores ejecutadas en secuencia, con salidas persistidas.

No se modificó ni migró la base de la aplicación existente. Los recursos temporales
son propios de esta validación; las muestras conservadas son exclusivamente sintéticas.
La revisión visual se hizo en este agente, sin revisión independiente por subagente.

Al terminar se detuvo únicamente el servidor de pruebas8765 y se eliminó el contenedor
`ecs-step2-resume-test` con sus bases descartables. Los tres contenedores existentes
`ecs-ec-app-1`, `ecs-ec-simulator-1` y `ecs-ec-db-1` siguen activos. La imagen validada
y los artefactos saneados se conservan para revisión; no se realizó despliegue.
