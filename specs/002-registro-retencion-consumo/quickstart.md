# Quickstart y validación: historial y conservación de consumo

[Plan](plan.md), [modelo](data-model.md), [HTTP](contracts/http.md),
[integraciones](contracts/integrations.md), [UI](contracts/ui.md).
Recepción, almacenamiento, calendario/agregados sincrónicos y recuperación CAT-01
están implementados y probados localmente: [aceptación parcial](validation/acceptance.md).
La fachada/UI001, consulta agrupada y retirada están integradas y verificadas localmente.
La aceptación integral espera003/007/personas; los resultados vigentes están en la evidencia.

## Prerrequisitos reales

Plataforma009 debe proveer herramientas/locks, PostgreSQL 18, UoW, reloj, helper de
aniversario, auditoría y ciclo de vida. Configuración/catálogo/validación/cálculo puros
de 001 se integran con el almacenamiento real 002 sin exigir aceptación completa de 001.
La DB necesita `btree_gist`; habilitar con permisos adecuados antes de usar la migración.
Para aceptación web, identidad006 real con Operador y Administrador activos y contraseña
renovada. Dobles solo acreditan pruebas aisladas.

Configurar zona IANA real del edificio, fuentes y vigencia histórica inicial mediante
los servicios 001. `America/Santiago` y UUID/fechas de ejemplo son fixtures, no datos
confirmados de una instalación. Secretos en `.env` ignorado/gestor de VPS.
003 debe demostrar identidad de fuente/publicación, intervalos/offsets y posibilidad
de reenviar novedades rechazadas desde la fecha admisible; fixtures no acreditan SFTP.
Correo y visores no son prerrequisitos de recepción/consulta.

## Comandos ejecutables del incremento interno

Desde la raíz, usar CPython 3.14/uv y Node >=20.9 con los locks existentes. Preparar una
DB PostgreSQL 18 separada terminada en `_test`; los fixtures rechazan la DB de aplicación.
Ejemplo exclusivamente sintético usado en esta ejecución:

```sh
uv sync --locked --group dev
npm --prefix frontend ci
docker run -d --name ecs-spec002-test -e POSTGRES_USER=ecs_test -e POSTGRES_PASSWORD=spec002-synthetic -e POSTGRES_DB=ecs_history_test -p 127.0.0.1:55450:5432 postgres:18.3-bookworm@sha256:80630f83606d8db77d30b3851b16a9f78be2d0d4dda6f7b82a1fdca5ebe3acba
docker exec ecs-spec002-test pg_isready -U ecs_test -d ecs_history_test
export TEST_DATABASE_URL='postgresql+psycopg://ecs_test:spec002-synthetic@127.0.0.1:55450/ecs_history_test'
DATABASE_URL="$TEST_DATABASE_URL" uv run --locked alembic -c backend/alembic.ini upgrade head
uv run --locked pytest backend/tests/unit/consumption backend/tests/integration/consumption backend/tests/contract/consumption
uv run --locked pytest backend/tests --cov=ecs_ec.consumption --cov-report=term-missing
npm --prefix frontend test -- --run --maxWorkers=1 --no-file-parallelism
npm --prefix frontend run typecheck
npm --prefix frontend run build
DATABASE_URL="$TEST_DATABASE_URL" uv run --locked alembic -c backend/alembic.ini check
docker rm -fv ecs-spec002-test
```

Esperar a que `pg_isready` confirme salud antes de migrar. La migración002 real es
`47457bdabdfa`, parent `cb63a76198be`; habilita `btree_gist` y necesita sus permisos.
También se comprobó upgrade de una configuración001 existente, sin crear aceptaciones.
El último comando elimina únicamente el contenedor/volumen de prueba de este ejemplo.

`history_environment`, `thirteen_month_records` y `consumption_reception_environment`
están en `backend/tests/integration/consumption/conftest.py`. Proveen servicios reales
001/002/009, reloj interno y datos sintéticos. Los 91 registros de trece meses/siete
categorías entran por `Reception.accept`, no mediante INSERT de mediciones.
Los TRUNCATE de fixtures aíslan la DB desechable y no acreditan retirada funcional.

## Recepción y recuperación internas

`main.create_app(consumption_bindings={process_ref: {building_uuid}})` permite a la
composición confiable003 ligar procesos al edificio; por defecto el mapa está vacío.
Los atributos `app.state.consumption_reception`, `app.state.consumption_store` y
`app.state.consumption_pending_totals` ofrecen los proveedores internos. No hay endpoint
público de inyección ni permisos derivados del contenido recibido.

El adaptador debe persistir `attempt_id` y la entrada ordenada antes de llamar al
puerto. La primera llamada fija manifiesto tipado/digest antes de los resultados.
Tras perder respuesta: `read_attempt` consulta sin efectos; repetir `accept` con el
mismo ID y entrada completa solo lo no confirmado. Un completed conserva incluso
su too_early original. Cambiar entrada con ese ID falla `attempt_payload_conflict`.
Para reenviar novedades rechazadas se necesita **otro ID**, conservando publication_ref.

Próxima incorporación nueva por categoría = última incorporación +900 segundos UTC;
la duración medida no se deduce de esa cadencia. Mostrar la fecha admisible usando
la zona del contexto001 y su instante UTC, sin confiar en el reloj de la fuente.
El host debe mantener UTC sincronizado. Un retroceso detectado rechaza novedades
hasta recuperar elegibilidad; duplicados/rechazos/lecturas no avanzan ese reloj.

El lifespan común registra `consumption-history`: recuperación al arrancar y cada 5s,
cancelable y dentro del mismo proceso. Cada aceptación confirma las solicitudes de
evaluación junto con las parciales, incluso antes de existir candidato. El trabajo
revalida bajo los mismos locks y agrupa los totales admisibles en una actualización.
`app.state.consumption_recovery_error` expone un código interno ante fallo para reintento;
la instrumentación007 continúa pendiente. GET no ejecuta el trabajo.

Las incorporaciones guardan plazos iniciales/aniversarios009 y aportes permanentes.
La retirada interna y sus protecciones están implementadas en `retention.py`;
no hay purga automática ni endpoint público de retirada. Si cambia tzdata y se detectan
límites incompatibles, se exige reconciliación explícita, sin reinterpretar agregados.

## Operación y consulta web implementadas

La ruta `/consumption/` existente001 permite Detalle/Hora/Día/Mes/Año conservando categoría,
filtro y zona. GET `/api/v1/consumption/categories/{category_id}/aggregates` exige
`start`, `end`, `timezone` y `granularity=hour|day|month|year`. Usar offsets del edificio,
no del navegador; los bloques deben caber completos. API y ambas vistas distinguen
null/—, cero, cobertura incompleta y situación temporal usando el mismo corte.
`no-store` se aplica también a errores. Una nueva consulta tras commit ve la revisión nueva;
GET no acepta, publica pendientes ni renueva plazos. No hay datos privados en el export.

Construcción/arranque, secretos y respaldo/restauración siguen los procedimientos de
[plataforma](../009-fundaciones-plataforma/quickstart.md) y
[operación](../../deploy/README.md). Configurar zona/fuentes reales antes de instalar.
No se verificó VPS con estas pruebas. tzdata2026.6 está fijada; ante límites históricos
incompatibles se exige reconciliación, nunca reinterpretación silenciosa.

### Retirada interna

La composición de mantenimiento crea `Retention(database, clock,
authorized_processes={process_ref: {building_uuid}})` desde
`backend/src/ecs_ec/consumption/retention.py`. Invocar por keywords:

```python
preview = await retention.withdraw_detail(building_id=building_uuid,
    record_ids=record_ids, process=process_ref, reason="expired_detail", preview=True)
result = await retention.withdraw_detail(building_id=building_uuid,
    record_ids=record_ids, process=process_ref, reason="expired_detail")
```

La ejecución vuelve a comprobar bajo locks: preview no garantiza elegibilidad posterior.
Resultados por registro: withdrawn/rejected/already_withdrawn y causa. Solo se elimina
payload vencido permitido; se preservan ledger/aportes/configuración/máximos y agregado.
Las solicitudes pending sin candidato y dependientes protegidos impiden retirar evidencia
necesaria. El vencimiento no obliga a borrar. Auditoría y ejecución confirman juntas;
un fallo DB revierte el lote y debe corregirse/reintentarse, sin declarar éxito.

### Recorridos de navegador reproducibles

Usar una DB nueva separada `_test`, migrada y vacía; nunca la de aplicación. Preparar un
archivo de contraseña sintética0600. Con `TEST_DATABASE_URL` apuntando a ese destino y
`DATABASE_URL` apuntando a otro (para la comprobación de aislamiento), ejecutar:

```sh
uv run python scripts/seed_consumption_reference.py --password-file /ruta/privada/password --mode physical
```

Después configurar el servidor con `DATABASE_URL` de esa DB de prueba, `ENVIRONMENT=test`,
`WEB_DIRECTORY=frontend/out`, `IDENTITY_ENABLED=true`, `IDENTITY_DEVELOPMENT_HTTP=true`,
`PUBLIC_URL=http://127.0.0.1:8014`, `IDENTITY_BUILDING_ID=00000000-0000-0000-0000-000000000063`
y claves CSRF/bucket sintéticas distintas de256 bits. No imprimir ni versionar claves.

```sh
uv run uvicorn ecs_ec.main:create_app --factory --host 127.0.0.1 --port 8014
```

En otra terminal con esa misma configuración de fixture:

```sh
IDENTITY_E2E_PASSWORD_FILE=/ruta/privada/password CONSUMPTION_E2E_MODE=physical E2E_BASE_URL=http://127.0.0.1:8014 npm --prefix frontend run test:e2e -- tests/e2e/consumption.spec.ts --workers=1
```

Las cuentas se renuevan usando006. Para repetir tras reiniciar app/PostgreSQL, añadir
`CONSUMPTION_E2E_RENEWED=1`. Para calculado usar otra DB vacía y `--mode calculated`/
`CONSUMPTION_E2E_MODE=calculated` desde su primer recorrido. No mezclar bases de tests
pytest con estos fixtures persistentes de navegador.

Para estados/retirada, usar el fixture físico recién renovado en el que aún no se ejecutó
este recorrido. Crear archivo0600 con `2026-12-01T12:00:00Z` y exportar
`HISTORY_E2E_CLOCK_FILE` a su ruta absoluta tanto en servidor como en Playwright. Arrancar
`backend.tests.run_history_browser:create_test_app` en lugar de la factory de producción.
Ejecutar `tests/e2e/consumption-history-states.spec.ts` con las mismas variables y
`CONSUMPTION_E2E_RENEWED=1`. El test alinea Date del navegador al reloj privado y llama
`python -m backend.tests.control_history_browser` para publicar/retirar a través de los
servicios reales; la app no expone un endpoint de fixture. Este recorrido requiere fixture
nuevo al repetir tras una retirada exitosa. Al terminar retirar únicamente contenedor/
volúmenes y archivos privados que se hayan creado para estas pruebas.

003 todavía debe demostrar publicaciones completas/identidad/reenvío;007 su emisor y
004/005/008 sus consumidores. Los fixtures no acreditan esas integraciones ni SC-005.

## Escenarios de validación

Cada fixture registra reloj, zona/tzdata, configuración, entradas y resultado esperado.
Las pruebas de reglas nuevas preceden a su implementación.

| Caso / trazabilidad | Preparación y resultado esperado |
| --- | --- |
| Primer envío, US1/FR-001..006/SC-001 | Siete categorías habilitadas: primeras actualizaciones válidas en el mismo instante se aceptan independientemente; conservar primera fecha de plataforma y origen. |
| Límite exacto, US1 | Aceptar a10:00; novedad a10:14:59 rechazada con10:15 próxima; a10:15 aceptada mediante reenvío explícito con nuevo attempt_id y misma publication_ref. Recuperar el ID del rechazo conserva ese resultado original; no lo reevalúa. |
| Identidad/recuperación, US1 | Adaptador persiste attempt_id y entrada canónica antes de accept; perder respuesta tras commit y consultar read_attempt sin efectos. Repetir accept con mismo ID/entrada completa solo posiciones sin resultado durable; dos recuperaciones concurrentes no repiten categorías/eventos/plazos. Payload distinto con igual ID falla attempt_payload_conflict; DB/autorización fallidas no son not_found. |
| Duplicados/rechazos, US1 | A 10:10 enviar duplicados equivalentes, inválidos o solo conflictos: no reinician plazo ni conservaciones; dato nuevo válido a 10:15 sigue siendo admisible. |
| Categorías y lotes, US1 | Una categoría anticipada y otra elegible en publicación común; varias lecturas históricas no superpuestas en la elegible: rechazar solo novedades anticipadas y aceptar lote válido como una actualización. |
| Carrera PostgreSQL, US1 | Dos novedades simultáneas de misma categoría; equivalentes, conflictos y superposiciones en casos separados: una actualización nueva como máximo por ventana, sin doble aporte. No SQLite como evidencia. |
| Configuración concurrente, contrato 001 | Ejecutar recepción/cambio de fuentes en ambos órdenes, revisar estados tras retirada: máximos históricos completos, zona protegida y sin configuración parcial ante proveedor ausente/error. |
| CAT-01 pendiente, US1/US2 | Completar contribuciones antes de elegibilidad CAT-01, reiniciar app y ejecutar trabajo al vencimiento: sin fila numérica anticipada; backlog completo en una actualización, referencias/eventos únicos. GET no incorpora. |
| Evaluación sin candidato, US1/FR-014 | Confirmar parciales con solicitud `pending` y detener la app antes de crear candidato. Reiniciar sin reenviar: el trabajo recupera la solicitud, guarda diagnóstico/candidato/total y la marca `processed` atómicamente; si CAT-01 no es elegible, conserva candidato pendiente. |
| Fallo y carrera de evaluación, US1 | Fallar después de escribir resultado y antes de marcar solicitud: rollback de ambos y recuperación sin duplicación. Recibir novedad concurrente: queda incluida o reactiva solicitud, sin pérdida de trabajo ni eventos/aportes duplicados. Duplicados/rechazos no crean solicitudes. |
| Sumas conocidas, US2/SC-002 | Cuatro lecturas contiguas de 1 kWh por hora; cubrir día/mes/año en las siete categorías: valores iguales a suma independiente de originales, no promedio ni rollup de nivel excluido. |
| CAT-01 medida/calculada, US2 | Física 100 con parciales sumando 60 da 100; calculada 20 y 30 en intervalos contiguos da 50 con base identificada. Faltante no aporta total ni cobertura ficticia. |
| Calendario/DST, US2 | Meses de 28/29/30/31 días, año bisiesto, día corto/largo, horas repetidas y transición no entera: límites UTC/offsets correctos, duración real y cada bloque una vez. |
| Contención, US2/FR-010/013 | Filtro con extremos parciales y lectura cruzada: solo bloques contenidos, avisos exactos; lectura puede contribuir a día aunque se excluya de hora. Contigua en fin no se duplica. |
| Cero/hueco/en curso, US4/SC-003 | Tres intervalos de 1 kWh dejan 75 %; ningún dato devuelve null/0 %; ceros cubiertos devuelven 0 kWh; bloque aún en curso conserva cobertura respecto del total. |
| Futuro y fronteras, US4/FR-012/SC-003 | Consultar filtro con bloque futuro sin lecturas y repetir con corte antes de inicio, exactamente en inicio y exactamente en fin: `not_started`/“Aún no iniciado”, `ongoing`/“En curso” y `finished`/“Terminado”. Ambas vistas mantienen filtro/bloques y consumo null/0 % de cobertura sin lecturas; estado y cobertura independientes. |
| Redondeo de cobertura, US4 | Falta un microsegundo: estado incompleto aunque porcentaje redondee a 100; UI muestra <100 % y duración faltante. |
| Exactitud numérica, US2/US4 | Mínimo quantum y máximos 001, total de seis máximos, agregado de suficientes aportes para superar precisión 50: igualdad exacta, sin float, redondeo ni aplicar techo individual al agregado. |
| Dato tardío, US4/FR-014 | Completar hueco desde una actualización elegible: siguiente consulta tras commit muestra nueva suma/cobertura en ambas vistas; repetir entrada no cambia revisión ni plazo. |
| Retención original/tardía, US3/SC-004 | Aceptada 2026-10-31 12:00 local protegida hasta 2027-10-31 12:00; lectura de período antiguo cuenta desde aceptación, no fecha medida. Consultar antes y en límite; superar mínimo no obliga a borrar. |
| Aniversarios especiales, US3 | 2028-02-29 → 2029-02-28 misma hora local; aniversario en hueco → primer instante válido, repetición → posterior. Usar helper 009 con reloj/tzdata controlados. |
| Extensión de agregado, US3 | Aporte nuevo prolonga doce meses desde incorporación; consultas, duplicados, rechazos y retirada del detalle no cambian ese inicio. |
| Retirada y reenvío, US3/FR-018 | Expirar detalle base y extender antes agregado con aporte tardío; retirar payload permitido. Agregado protegido mantiene valor/cobertura; reenvío viejo duplicado/conflicto no suma; novedad válida suma solo una vez. |
| Referencias protegidas, US3 | Intentar retirar base/revisión requerida por total o pendiente protegido: rechazar/posponer; conservar consulta, base y referencias durante mínimo calculado. |
| Historia insuficiente, US3/US4/FR-019 | Año con datos solo desde inicio de operación y categorías sin fuente: cobertura real parcial/ausente, nunca año completo ni ceros inventados. |
| Consumidores, puertos internos | Última ventana completa/revisión, proyección 008 de otra zona con contención real; 004 solo CAT-01 física/resolución probada; reporte comparte captura de siete categorías. Dobles no acreditan integración real. |
| Persistencia/fallos, transversal | Reinicio app/DB conserva datos; rollback de categoría no deja aceptaciones/eventos; caída tras commit recupera resultado sin doble suma. Sin correo/visores recepción y consultas siguen disponibles. |
| Web/seguridad, SC-002/003 | Operador/Administrador consultan; sin sesión/expirada o Programador denegados; filtro y agrupación se conservan, gráfico/tabla idénticos; carrera A→B/error/reintento no muestra respuesta vieja. |

Las pruebas de retirada llaman a la operación interna real, sin DELETE directo que
eluda protecciones. La validación de doce meses usa avance controlado del reloj;
no se cambia el reloj del host ni se espera un año.

## Aceptación humana, operación y evidencia

SC-005: ejecutar diez tareas con personas representativas, asignando categorías,
agrupaciones y períodos. Registrar acierto sin ayuda, tiempo, interpretación de consumo/
período/cobertura y concordancia en ambas vistas. Deben pasar >=9 en <=60 s cada una.
Hasta contar con participantes/resultados, el criterio queda pendiente.

Verificar localmente despliegue único, build sin datos privados, recuperación de pendientes,
salud/migraciones, respaldo/restauración por plataforma y configuración real de zona.
La integración nativa 003 comprueba publicaciones completas, identidad y reenvío
conservando lecturas pendientes en la fuente; una inyección interna no la demuestra.
El despliegue posterior VPS aplica procedimientos 009/006/007; no añadir sus módulos
en tareas de esta spec ni afirmar verificación externa desde pruebas locales.

Ampliar la [aceptación parcial](validation/acceptance.md) con cada incremento: commit/versiones,
comandos, zona/tzdata, fixtures, fuente/adaptador, esperados/observados por FR-001..019 y
SC-001..005, fallos/pendientes y evidencias humanas.
No crear resultados ficticios ni marcar checklists por generar el diseño.
