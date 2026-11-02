# Continuación de implementación 001 sobre almacenamiento 002

**Fecha:** 2026-11-02. **Base Git:** `0ef2f9bdfb45e8617f4b17b2ff521fa0a97ec679`.
**Estado:** 48/61 tareas completas; aceptación integral pendiente. Los cambios previos de
spec-004 y el estado 003 en la hoja de ruta se preservaron. No se modificaron checklists,
la selección persistida de Spec Kit ni tareas de otras specs.

## Entrega comprobada

- `backend/src/ecs_ec/consumption/queries.py`: `Consumption.source_status`, catálogo y
  detalle sobre `MeasurementStore` real 002. Capturas REPEATABLE READ READ ONLY con
  corte/configuración/filas coherentes; ninguna lectura incorpora totales ni renueva plazos.
- `schemas.py`, `periods.py` y `router.py`: cuatro operaciones del contrato 001, decimales
  como cadenas exactas, originales/contribuciones y revisiones históricas, contención de
  filas, offsets IANA y microsegundos. Cero disponible difiere de ausencia, error e incompleto.
- Composición existente de 009/006: permisos antes de validar cuerpos, CSRF/origen,
  `no-store`, cuenta/sesión revalidadas bajo locks para PUT. Configuración/auditoría/eventos
  y actividad autorizada se confirman juntos. Historia administrativa registra la acción 001
  mediante el catálogo de productores existente. No se creó otro mecanismo de identidad.
- `/consumption/` y `/administracion/consumo/`: páginas exportadas, catálogo de siete,
  gráfico/tabla de una sola respuesta, período conservado, estado/reintento, formulario
  administrativo versionado. La ruta administrativa usa la navegación española real 006.
- `useConsumptionQuery`: clave completa/generación, abort y descarte adicional de respuestas
  antiguas; invalida resultados durante carga/error y limpia ante cambio de sesión. Datos
  privados solo en memoria, sin localStorage ni datos del edificio incorporados al build.
- `scripts/seed_consumption_reference.py` y `frontend/tests/e2e/consumption.setup.ts`:
  fixtures sintéticos protegidos, destinos vacíos separados `_test`, cuentas 006 con renovación
  ordinaria y todos los registros ingresados mediante `Reception.accept` real 002.

Los proveedores 002 `read_general_snapshot`, `read_demand_history`, agrupaciones y resumen
funcional **no se implementaron** aquí. Esta fachada no desbloquea por sí sola costos 004.
No se añadieron dependencias, migraciones ni modificaciones a lockfiles.

## Verificación ejecutada

| Comando / escenario | Resultado observado |
| --- | --- |
| Script oficial con selección explícita 001 y NO_PERSIST | FEATURE_DIR absoluto correcto; requirements16/16; sin hooks registrados. |
| Regresión inicial de consumo |119 aprobadas, incluidos los cinco escenarios antes omitidos de T015. PostgreSQL real 002, carreras recepción/configuración en ambos órdenes, límites899/900 s y recuperación. |
| `TEST_DATABASE_URL=... uv run --locked pytest backend/tests --cov=ecs_ec --cov-report=term-missing -q` | **287 aprobadas,1 xfail estricta**,38.76 s; cobertura global observada92%. No se inventa un umbral de aceptación. |
| ContratoHTTP tras documentar errores y seguridad en OpenAPI instalado | Se comprueba esquema real de rutas/errores/cookie/CSRF, además del contrato 001 sobre respuestas reales físicas y calculadas. |
| `npm --prefix frontend test -- --run --maxWorkers=1 --no-file-parallelism` |**42 aprobadas**,18 archivos,11.84s en la regresión final, incluidos mensajes de faltantes/espera y limpieza de sesión. |
| TypeScript y `npm --prefix frontend run build` | Aprobados; exporta `/consumption` y `/administracion/consumo` junto con las páginas existentes. |
| Playwright físico |2/2 perfiles aprobados, siete categorías,100 kWh total frente a parciales10 kWh, cero/q, hueco, consulta inválida/cruzada y permisos/configuración persistida. Navegador Asia/Tokyo, edificio America/Santiago. |
| Reinicio real de Uvicorn y PostgreSQL | Se detuvo el proceso y reinició `ecs-spec 001-test`; Playwright físico volvió a pasar2/2 con cuentas renovadas, originales y configuración conservados. |
| Playwright calculado |2/2 perfiles aprobados; CAT-03=12 y CAT-05=8 producen20 kWh, categorías ausentes sin filas ficticias; cero y positivo mínimo conservados. |
| Historia representativa |91 filas físicas, trece meses/siete categorías por recepción real; las siete consultas devuelven13 filas cada una,40296 bytes JSON en total y0.074 s observados. No acredita un SLO ni volúmenes mayores. |
| Revisión documental Python |11 archivos nuevos, sin módulos/clases/funciones propios carentes de docstring. TSDoc revisado en componentes/cliente/pruebas nuevos. |
| Tipos generados / ignores | Generador oficial ejecutado sin cambios de tipos. `.gitignore` y `.dockerignore` cubren las tecnologías reales; sin ESLint/Prettier/Terraform/Helm ni publicación npm que requieran archivos adicionales. |

PostgreSQL 18.3 usa el digest de Compose en el contenedor desechable `ecs-spec 001-test`,
loopback55451. Bases `ecs_consumption_test`, `ecs_consumption_browser_test` y
`ecs_consumption_calculated_test`, distintas de la aplicación. Los servidores web sintéticos
usan puertos8011/8012 y exportNext con un proceso Uvicorn cada uno. La imagen `ecs-spec001-validation:local`,
`sha256:5803638c388db9e1a599b5304d49223e9a92699e594bab95f545e0876228179e`,
pasó los dos perfiles Playwright en3.3s como usuario10001, API ready y sin Node en runtime.
Un único proceso Uvicorn sirve API/exportación; el segundo proceso Python observado
era únicamente el comando de inspección ejecutado dentro del contenedor. Herramientas/locks conservados:
CPython 3.14.4, Node 24.22.0, npm 12.2.0, tzdata 2026.6, decimal.js 10.6.0 y Playwright 1.64.0.

La primera ejecución Playwright necesitó instalar el Chromium correspondiente al lock.
Dos aserciones iniciales se corrigieron: una coincidía con inicio y fin de intervalos
contiguos; otra incluía el anunciador vacío de Next en el selector de alertas. En el
primer recorrido calculado, un worker salió con SIGSEGV después del escenario administrativo;
el escenario Operador pasó aislado y la repetición completa posterior pasó2/2. No se
modificó código funcional para ocultar esos fallos. Las pruebas de fachada y HTTP se
observaron fallar antes de añadir sus implementaciones. Los recorridos E2E y parte de la
validación temporal se añadieron después del montaje inicial: no se afirma TDD E2E completo.

## Gate 002 y trabajo pendiente

`MeasurementStore.read_detail` en `backend/src/ecs_ec/consumption/store.py` informa IDs
cruzados de registros, pero selecciona diagnósticos únicamente por contención. Por ello,
una consulta que excluye un candidato de CAT-01 cruzado no puede informar su cantidad.
`backend/tests/integration/consumption/test_detail_periods.py` conserva el caso como
**xfail strict**, con razón explícita y sin contar el criterio como satisfecho. El caso de
registro físico cruzado sí pasa, contado una sola vez aunque cruce ambos límites.

**Propietario 002:** ampliar su contrato/proveedor `DetailRead` en
`backend/src/ecs_ec/consumption/ports.py` y `MeasurementStore.read_detail` en `store.py`
para exponer la evidencia de diagnósticos cruzados sin duplicarlos. Capacidad de lectura
asignada a **T024 de spec-002** en sus [tareas](../../002-registro-retencion-consumo/tasks.md),
a coordinar con contención/proyecciones de su US2. No se implementó ese proveedor desde 001.
001 podrá completar T038/T041/T044 cuando reciba esa evidencia.

**T018 de 001:** carreras/límites/recuperación y máximos durables ya se ejecutan con 002;
la comprobación con retirada real permitida conserva su gate de conservación de 002.
La simulación de estado retirado en pruebas de almacenamiento no acredita su trabajo de
retirada elegible todavía pendiente (US3 de 002).

**T045/T052/T053:** archivos y pruebas actuales son parciales. Faltan completar todos los
recorridos ampliados de estado/espera/llegada tardía/carreras por navegador y su evidencia.
**T043:** faltan los dos offsets de hora repetida y los casos ampliados en navegador, aunque
las pruebas unitarias de fecha los cubren. No se marcan por el recorrido básico existente.
**T054/T056:** requieren emisor 007 y servicios reales 003/008 según capacidad.
**T057 completa:** build/medición local e imagen/runtime comprobados; ver [construcción](build-and-volume.md).
**T059/T060:** no hay participantes ni VPS; no se sustituyeron por automatización.
**T061:** cierre integral pendiente de esos resultados.

## Trazabilidad funcional vigente

| Requisitos / criterios | Evidencia actual y límite |
| --- | --- |
| FR-001 | Siete categorías y administración autorizada con fuentes reales 002; pruebas/UI locales. Retirada real de T018 pendiente. |
| FR-002..006/010, SC-003 | Semántica/reenvío/concurrencia y originales reales 002; equivalencia y límites exactos; captura de fuente sin sustitución del total físico. |
| FR-007..009, SC-001/002 | API/gráfico/tabla en siete categorías,100 frente a parciales60 y calculado12+8=20. Persistencia tras reinicio. |
| FR-011..013 | Orden/contención/offsets y última consulta válida comprobados; cruce de diagnósticos y recorridos DST ampliados pendientes. |
| FR-014..016, SC-004 | Cero/no fuente/vacío/incompleto/error, limpieza y generaciones verificadas en pruebas actuales; aceptación completa de T045/T052/T053 pendiente. |
| FR-017/018 | Exportación web local y permisos actuales 006; no acredita HTTPS/VPS/red externa. |
| FR-019, SC-006 | Puerto local 002 real; integración SFTP/007/SMTP 008 pendiente. |
| SC-005 | Sin personas; pendiente. |
| SC-007 | Sin VPS; pendiente. |

No hay `.specify/extensions.yml`; se comprobó ausencia de hooks previos y posteriores.

La primera construcción Docker terminó con SIGSEGV durante recolección de trazas de Next,
después de generar páginas. La repetición sin cambios pasó y produjo la imagen validada;
no se actualizó ninguna dependencia ni se eliminó una comprobación para sortear el fallo.
Los contenedores `ecs-spec001-app`/`ecs-spec001-test` y su volumen anónimo de PostgreSQL
se retiraron al finalizar; también el archivo de contraseña sintética. Se conserva la
imagen local como artefacto revisable. `git diff --check` y los enlaces Markdown relativos
se comprobaron sin errores; no se ejecutaron hooks porque no existe su archivo de registro.
