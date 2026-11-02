# Quickstart y validación: Costos BT4.3

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

US1–US4 implementadas sobre001/002/006/009 reales; [validación local](validation/acceptance.md).
T064/SC-006 permanece pendiente por falta de participantes humanos.
Los perfiles de prueba no representan condiciones ni precios reales del edificio.

## Prerrequisitos

Núcleo real con Python/FastAPI, PostgreSQL 18, identidad de spec-006, CAT-01 física y agregados de specs-001/002, auditoría/eventos comunes. Reutilizar capacidades compartidas sin requerir consumidor 008, SMTP o scheduler. Incorporar la migración semántica de costos al head real y configurar suministro/perfil sintético; no usar datos ni relay de producción.

Comandos de verificación, con TEST_DATABASE_URL explícita a una base PostgreSQL separada `_test`:

```sh
uv sync --locked
DATABASE_URL="$COSTS_TEST_DATABASE_URL" ENVIRONMENT=test uv run --locked alembic -c backend/alembic.ini upgrade head
TEST_DATABASE_URL="$COSTS_TEST_DATABASE_URL" uv run --locked pytest backend/tests/unit/costs backend/tests/integration/costs backend/tests/contract/costs
npm --prefix frontend ci
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Pruebas PostgreSQL usan base distinta y comprobada como desechable. Semillas sintéticas y transporte de eventos en la misma base; dobles de puertos solo en pruebas aisladas. Las evidencias registran versiones, zona/tzdata, corte, perfil y comandos sin secretos.

## US1: cálculo real y presentación

Preparar CAT-01 física con 1000 kWh y precio energético sintético 100 CLP/kWh: componente 100000 CLP netos. Bloque completo de 15 minutos con 10 kWh: 40 kW. Máximos de 60/50 en dos meses diferentes: base 55 kW; máximos de punta 30/20 para mes sin punta: 25 kW. Repetir con máximos iguales de meses distintos y mantener ambos antecedentes.

Usar perfil sintético con todos sus cargos aplicables, fuentes de prueba, impuestos/condiciones explícitos y redondeo declarado; comprobar resultados manualmente conocidos de conceptos/subtotales/total. Energía cero mantiene cargos independientes aplicables. Horas incompletas, solo datos horarios, falta de medidor físico y CAT-01 calculada producen limitaciones sin cero ni total completo ficticio. Comprobar igualdad gráfico/tabla/unidades/ciclo y que Operador no pueda crear revisiones.

Detener y reiniciar aplicación/base: resultado y captura siguen legibles. Un fallo controlado del motor registra resultado fallido y `cost.failed` juntos; abortar su transacción de registro no conserva ninguno. Reintentar la misma operación no duplica evento/revisión. Falta de datos esperada no provoca una alerta técnica por cada consulta.

Desde la web administrativa, `CalculationForm` usa GET suministro (sembrado para US1), permite seleccionar ciclo/límites y confirmar POST cálculo; después abrir la revisión persistida y recargar. Confirmar otro recálculo con motivo conserva la anterior. Forzar validación mantiene entradas; reintentar la misma operación reutiliza clave y no duplica revisión. El Operador solo consulta. US3 completa la gestión web del suministro/perfil; los fixtures sintéticos de US1 no acreditan esa administración.

### Referencia mensual sintética entre meses

Usar zona de prueba `Etc/UTC`, ciclo `[2026-03-15T00:00:00Z,2026-04-15T00:00:00Z)` y corte `2026-05-01T00:00:00Z`. El perfil de prueba documenta modo `explicit_evidence`: antecedente `fixture-cycle-2026-03-15` del mismo suministro/ciclo indica `billing_month_ref=2026-04`; `billing_month_source_ref` incluye esa referencia documental y los metadatos de suministro/inicio/fin/mes coincidentes. El Administrador declara el respaldo documental, el servidor valida los metadatos sin OCR y se captura `billing_month_policy_version=fixture-month-v1`. Son condiciones ficticias, no una regla normativa de BT4.3 para el edificio.

| Base sintética | Resultado esperado |
| --- | --- |
| Ventana de 12 meses con referencia abril de 2026 | `[2025-05-01T00:00:00Z,2026-05-01T00:00:00Z)`; no usar la ventana terminada en marzo. |
| Máximos mensuales completos: mayo de 2025=60 kW, junio=50 kW, restantes <=40 kW | Potencia suministrada: `(60+50)/2=55 kW`. |
| Calendario sintético: punta abril–septiembre; máximo de punta abril de 2026=30 kW | Base de punta: 30 kW, porque la referencia documentada es abril. |
| Punta anterior abril–septiembre de 2025: dos mayores 30/20 kW | La alternativa de referencia marzo daría 25 kW; no usarla para el antecedente que establece abril. |
| Mes/fuente ausentes o contradicción con el antecedente del ciclo | `billing_month_unresolved`; cargos dependientes no calculables, sin total completo; otros componentes calculables se conservan. |

Preparar evidencia física completa de los meses requeridos al corte, con bloques de 15 minutos y máximos conocidos; no fabricar cobertura a partir de los máximos aislados. Cambiar posteriormente mes/evidencia exige otra revisión del cálculo y conserva fuente/versión/ventana de la captura anterior.

## US2: boleta y comparación

Registrar boleta cuyo ciclo atraviesa dos meses. Comparación 105 contra 100 CLP: diferencia +5 y 5 %. Contra cero: diferencia monetaria conservada y porcentaje no aplicable. Añadir deuda, crédito negativo y bases tributarias distintas: solo pares compatibles entran al subtotal; total a pagar permanece separado.

Repetir identificador y corregir explícitamente: no duplicar boleta lógica ni borrar revisión previa. Mismos conceptos con impuesto incluido no reciben otro impuesto. Registro de boleta no modifica mediciones, perfil ni cálculo. Sin boleta se mantiene la consulta de costo.

Desde `ComparisonActions`, seleccionar IDs/revisiones compatibles y confirmar POST comparación. Mostrar el recurso persistido y recuperarlo tras recarga; error de validación conserva selección, reintento no duplica operación y Operador no puede mutar. Corregir la boleta conserva la comparación anterior y ofrece crear explícitamente la del nuevo par; consultar o guardar boleta no la crea automáticamente.

## US3: vigencias y perfil

Leer GET suministro: 404 permite alta con `If-None-Match: *` (201/revisión 1/ETag). Recargar editor recupera datos/ETag; editar con `If-Match` devuelve 200/nueva revisión/ETag. Alta simultánea o edición con ETag antiguo devuelve 412; sin precondición 428. Un 412 conserva entradas y exige revisar el estado actual antes de confirmar. Reintentar una operación ya confirmada reproduce su resultado autorizado antes de comprobar precondiciones nuevas.

Guardar V1 publicada con calendario completo y segmento `[2026-01-01,infinito)` a 100 CLP/kWh. Publicar V2 con `[2026-01-01,2026-07-01)` a 100 y `[2026-07-01,infinito)` a 110. Publicar V3 con el primer segmento corregido a 105: 1000 kWh contenidos en ese segmento dan 100000 CLP energéticos con V1/V2 y 105000 con V3, sin cambiar la captura anterior. Los precios son sintéticos y las demás condiciones del perfil de prueba se mantienen explícitas. El recálculo administrativo crea otra revisión del cálculo; abrir el anterior lo reproduce con su calendario capturado.

Superponer segmentos dentro de V3 rechaza publicación, mientras que sus fechas coincidentes con V1/V2 son válidas. Guardar borrador no cambia la revisión publicada seleccionada; publicarlo exige otra revisión. Dos POST con igual `expected_previous_version_id` permiten una sola creación y el otro recibe 409, sin calendario parcial. GET perfiles distingue última guardada/publicada; resolver conflicto exige revisar el calendario actual. Huecos o estrategias sin soporte limitan el resultado sin inventar valores. Ciclo que cruza precio segmenta solo con evidencia y estrategia documentadas, sin prorratear fijo/demanda. Probar DST/calendario de punta, política mensual y zona declarada.

## US4: historia y reproducción

Consultar doce meses de datos sintéticos disponibles, ciclos cerrados/en curso y componentes parciales. Preservar captura/máximos/perfil/boleta y retirar solo detalle de origen cuyo plazo haya vencido: reproducción mantiene importes/versión. Aniversarios incluyen 29 de febrero y horas repetidas/inexistentes con política de spec-002; una consulta no reinicia el plazo.

Comprobar `Costs.read_snapshot` en una unidad de trabajo compartida con consumo: ciclos cerrados por fin efectivo en `[start,end)`, una revisión vigente a corte, corrección posterior excluida, agregados por base/moneda y comparaciones sobre mismos pares. Sin ciclos/boletas/pares se distinguen las causas; ningún prorrateo entra al PDF 005.

Preparar cálculo C1, boleta B1 y comparación K1. Corte A los selecciona. Corregir a B2 antes de corte B sin otra comparación: selecciona C1/B2 con `comparison_status=missing_for_selected_revisions`, diferencias null y fuera del contraste agregado; sus valores siguen disponibles y K1 es histórica. Crear K2 para C1/B2 lo incorpora a cortes posteriores; recalcular C2 vuelve a dejar C2/B2 pendiente. Repetir corte A conserva C1/B1/K1. Probar también cálculo/boleta ausentes y facturado cero con comparación `available`; ninguna lectura crea revisiones/comparaciones. El consumidor PDF aplica el mismo contrato.

## Aceptación transversal

Deshabilitar consumidor de notificaciones y correo: cálculo, resultados y eventos durables permanecen funcionales. Provocar un error de base: no afirmar aceptación/persistencia del evento. Confirmar permisos actuales y exclusión de credenciales técnicas/secretos en respuestas y señales.

Ejecutar diez tareas reales de comprensión (SC-006); al menos nueve sin ayuda en <=2 minutos. Sin participantes, ese criterio queda pendiente. Registrar evidencia de los 23 FR y seis SC en `validation/acceptance.md` durante implementación, con resultados observados y pendientes explícitos.

## Fixture004 y navegador local

Sobre una base **vacía y migrada**, separada de la aplicación y terminada `_test`, preparar
un archivo0600 con contraseña exclusivamente sintética. Ejecutar:

```sh
TEST_DATABASE_URL="$COSTS_TEST_DATABASE_URL" uv run --locked python scripts/seed_costs_reference.py --password-file "$COSTS_PASSWORD_FILE"
npm --prefix frontend run build
```

La semilla usa cuentas006 con renovación normal, configuración001, recepción física002 y
perfil004 documentado de energía-only sintética (100CLP/kWh). No es un pliego real ni
acredita suficiencia de condiciones de una instalación física. Montar Uvicorn común con
IDENTITY_ENABLED=true, claves006 de prueba externas y distintas, origen loopback explícito,
IDENTITY_BUILDING_ID=00000000-0000-0000-0000-000000000063 y WEB_DIRECTORY=frontend/out.
HTTP local requiere la opción explícita006 IDENTITY_DEVELOPMENT_HTTP=true.

```sh
IDENTITY_E2E_PASSWORD_FILE="$COSTS_PASSWORD_FILE" COSTS_E2E=1 E2E_BASE_URL="$COSTS_BROWSER_ORIGIN" npm --prefix frontend run test:e2e -- tests/e2e/costs.spec.ts --workers=1
```

Al repetir después de renovar ambas cuentas, añadir COSTS_E2E_RENEWED=1; no resembrar.
Las consultas viven en `/costos/`, las operaciones explícitas en `/administracion/costos/`.
Los resultados pueden abrirse mediante `?calculation=<UUID>` y se recuperan por GET tras
recargar. Nunca se calculan importes autoritativos en el navegador.

`uv run --locked python scripts/generate_costs_types.py` regenera tipos readonly desde
los esquemas004. No cambia dependencias/lockfiles ni lee datos privados.

## Publicación del pliego real

Administrador lee suministro/ETag y confirma fuente físicaCAT-01, tablero, distribuidora,
ubicación, condiciones y documentos. El formulario conserva diferencias conocidas del punto
de medición sin aplicar un factor implícito. Alta usa If-None-Match:*; editar requiere
If-Match. Un412 exige revisar estado actual antes de confirmar la intención nuevamente.

En Perfil BT4.3, copiar un calendario guardado o crear segmentos estructurados. Registrar
fuentes del pliego y de cada cargo, fechas con offset, unidad/precio/base tributaria,
cargos realmente aplicables, calendario de punta, históricos y redondeo. Para sustituir
vigencia abierta copiar el calendario completo y cerrarla antes del nuevo segmento;
corrección retroactiva crea otra revisión completa. No cambiar versiones anteriores.
El antecesor esperado es la última revisión guardada, incluidos borradores;409 exige
revisión explícita. Borrador no sustituye publicación ni recalcula automáticamente.

La política mensual debe tener versión/fuentes: evidencia explícita compatible con
suministro/ciclo/mes, o regla documentada soportada de inicio/fin local. No se elige regla
normativa por defecto. Reglas, fuentes o vigencias faltantes dejan cargos limitados;
no se prorratean fijos/demanda ni se presupone impuesto/distribuidora universal.

## Recorridos finales y alta inicial

Esperar readiness200 en `/api/v1/health/ready` antes de abrir el navegador.
Después de renovar ambas cuentas con costs.spec.ts, ejecutar en este orden sobre la misma
base sintética (desde frontend, COSTS_E2E_RENEWED=1 y variables del ejemplo anterior):

```sh
npx playwright test costs.spec.ts --workers=1
npx playwright test cost-profiles.spec.ts --workers=1
npx playwright test cost-comparisons.spec.ts --workers=1
npx playwright test cost-history.spec.ts --workers=1
```

Para probar alta inicial, crear **otra base vacía `_test`**, migrarla y ejecutar la semilla
con `--without-costs`. Ejecutar el monolito con ese destino/origen de prueba. En frontend,
con IDENTITY_E2E_PASSWORD_FILE y E2E_BASE_URL correspondientes, ejecutar:

```sh
COSTS_INITIAL_E2E=1 npx playwright test cost-supply-initial.spec.ts --workers=1
```

Esta variante renueva al administrador y registra suministro/perfil desde la web; no
reutilizarla sobre cuentas ya renovadas. Ambas semillas rechazan destinos de aplicación.

## Lectura interna para005

Usar `app.state.costs.read_snapshot(building_id, start, end, cutoff_at, principal,
unit_of_work=uow)` con principal006 actual y UoW009 REPEATABLE READ/serializable, compartida
con consumo. Sin UoW crea una lectura REPEATABLE READ propia. Devuelve CostsSnapshot v1;
`model_dump(mode="json")` serializa importes textuales. Motor reproducible `bt43-v1`.
Solo ciclos cerrados con fin en[start,end), pares exactos y agregados por moneda/concepto/
base; pendientes con diferencias null. No generar cálculos ni prorratear para PDF.
Contrato y prueba concurrente en [integraciones](contracts/integrations.md) y [US4](validation/us4.md).
