# Quickstart y validación: Costos BT4.3

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

Esta guía describe la implementación que deberá producir [tasks.md](tasks.md). Actualmente los artefactos son diseño; los comandos de aplicación/pruebas no se presentan como ya ejecutados.

## Prerrequisitos

Núcleo real con Python/FastAPI, PostgreSQL 18, identidad de spec-006, CAT-01 física y agregados de specs-001/002, auditoría/eventos comunes. Reutilizar capacidades compartidas sin requerir consumidor 008, SMTP o scheduler. Incorporar la migración semántica de costos al head real y configurar suministro/perfil sintético; no usar datos ni relay de producción.

Después de implementar los comandos:

```sh
uv sync --locked
docker compose up -d db
uv run alembic -c backend/alembic.ini upgrade head
uv run pytest backend/tests/unit/costs backend/tests/integration/costs backend/tests/contract/costs
npm --prefix frontend ci
npm --prefix frontend test -- --run
npm --prefix frontend exec playwright test tests/e2e/costs.spec.ts
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
