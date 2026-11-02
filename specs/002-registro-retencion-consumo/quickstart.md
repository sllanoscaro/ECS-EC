# Quickstart y validación: historial y conservación de consumo

[Plan](plan.md), [modelo](data-model.md), [HTTP](contracts/http.md),
[integraciones](contracts/integrations.md), [UI](contracts/ui.md).
Guía de la implementación prevista. El repositorio todavía carece de aplicación,
manifiestos y fixtures ejecutables; los comandos siguientes se habilitarán al implementar.
No se han ejecutado pruebas funcionales ni se acredita aceptación con estos documentos.

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

## Preparación y comandos previstos

Desde la raíz, después de implementar los prerrequisitos:

```sh
cp .env.example .env
uv sync --locked --group dev
npm --prefix frontend ci
npm --prefix frontend run build
docker compose build app
docker compose up -d db
docker compose run --rm app uv run --locked alembic -c backend/alembic.ini upgrade head
docker compose up -d app
uv run --locked pytest backend/tests/unit/consumption backend/tests/integration/consumption backend/tests/contract/consumption
npm --prefix frontend test -- --run
npm --prefix frontend exec -- playwright test tests/e2e/consumption.spec.ts tests/e2e/consumption-history-states.spec.ts
```

Completar `.env` conforme a plataforma antes de arrancar. Pruebas usan
`TEST_DATABASE_URL` a una DB separada comprobada como desechable; nunca base de aplicación
o producción. El harness controla reloj/tzdata internamente, sin endpoint público.
Preparación de Playwright crea usuarios y configuración mediante servicios reales y
levanta aplicación con su propia DB.

Los fixtures llaman a `Reception.accept` en vez de INSERT que eluda validación.
Enviar historia de una categoría en un lote o avanzar reloj >=900 segundos entre
actualizaciones nuevas. La cadencia no exige esperar quince minutos entre cada lectura
del lote. Incluir un historial sintético de >=12 meses para las siete categorías.

Consulta manual, tras autenticar por el flujo real 006 y guardar cookie de prueba en
archivo protegido local, con `APP_PUBLIC_BASE_URL` configurado por plataforma:

```sh
curl --fail-with-body --cookie /tmp/ecs-ec-history-session.cookies --get "$APP_PUBLIC_BASE_URL/api/v1/consumption/categories/CAT-03/aggregates" --data-urlencode 'start=2026-10-31T10:00:00-03:00' --data-urlencode 'end=2026-10-31T11:00:00-03:00' --data-urlencode 'timezone=America/Santiago' --data-urlencode 'granularity=hour'
```

Con fixture de tres cuartos de hora a 1 kWh, esperar un bloque de `"3"` kWh,
`"2700000000"`/`"3600000000"` microsegundos, 75 %, incompleto y terminado
si el reloj está después del fin. Completar el cuarto intervalo en actualización
admisible debe producir 4 kWh, 100 % y nueva revisión en la siguiente consulta.

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

Durante implementación crear `specs/002-registro-retencion-consumo/validation/acceptance.md`
con commit/versiones, comandos, zona/tzdata, fixtures, fuente/adaptador usado, esperados/
observados por FR-001..019 y SC-001..005, fallos/pendientes y evidencias humanas.
No crear resultados ficticios ni marcar checklists por generar el diseño.
