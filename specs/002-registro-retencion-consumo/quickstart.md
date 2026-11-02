# Quickstart y validación: historial y conservación de consumo

[Plan](plan.md), [modelo](data-model.md), [HTTP](contracts/http.md),
[integraciones](contracts/integrations.md), [UI](contracts/ui.md).
Recepción, almacenamiento, calendario/agregados sincrónicos y recuperación CAT-01
están implementados y probados localmente: [aceptación parcial](validation/acceptance.md).
Fachada/UI001, consulta agrupada, retirada y aceptación integral siguen pendientes.
Los escenarios posteriores describen los objetivos restantes, no resultados ya obtenidos.

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
**Retirada interna y sus protecciones completas siguen pendientes de US3**; esta entrega
no añade purga automática ni un comando de retirada. Si cambia tzdata y se detectan
límites incompatibles, se exige reconciliación explícita, sin reinterpretar agregados.

## Operación y recorrido web pendientes

Construcción/arranque y respaldo/restauración comunes siguen los procedimientos de
[plataforma](../009-fundaciones-plataforma/quickstart.md) y
[operación](../../deploy/README.md). Completar secretos y zona/fuentes reales antes de
instalar; America/Santiago es fixture. No se verificó VPS desde estas pruebas locales.

La ruta `/consumption/`, su fachada/router001 y el GET agrupado todavía no existen.
Los recorridos Playwright de agrupación, conservación y estados se habilitan después
de completar ese gate y US2–US4. El build actual no acredita esas pantallas.
003 debe demostrar publicaciones completas/identidad/reenvío;007 su emisor y004/005/008
sus consumidores. Los fixtures internos no acreditan esas integraciones.

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
