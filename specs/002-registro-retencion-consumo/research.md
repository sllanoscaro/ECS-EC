# Investigación: Registro temporal y retención de consumo

**Fecha**: 2026-11-01. [Plan](plan.md), [spec](spec.md), [arquitectura](../../docs/architecture.md).
Fase 0: decisiones de diseño resueltas; instalación y aceptación todavía pendientes.
Se investigaron recepción/concurrencia y calendario/conservación mediante agentes de
investigación de solo lectura, conforme a la habilidad de planificación.

## R1. Reutilizar los límites de propiedad y puertos existentes

**Decisión**: adoptar las reglas puras y objetos de 001; 002 implementa su almacenamiento,
recepción y proyecciones mediante `backend/src/ecs_ec/consumption/ports.py`. La composición 009 inyecta
implementaciones; 003 adapta publicaciones físicas. Sin endpoint público de ingesta.

**Razón**: los [contratos 001](../001-visualizar-consumo-categorias/contracts/integrations.md)
ya asignan esas responsabilidades y la [hoja de ruta](../../docs/implementation-roadmap.md)
prohíbe crear capacidades externas dentro del setup de 002.

**Alternativas consideradas**: duplicar modelos de dominio/validación; esperar aceptación
completa de 001; importar 008 desde recepción. Las tres crean duplicación o ciclos.

## R2. Serialización durable, resultado independiente por categoría

**Decisión**: UoW READ COMMITTED por actualización de categoría; contexto/configuración
del edificio → categorías afectadas ordenadas CAT-01..07 → pendientes/aportes/agregados
en orden estable. Releer configuración/estado y reloj tras adquirir bloqueos. Validar
registros, clasificar duplicados/conflictos y recién entonces aplicar 900 segundos a
novedades admisibles. Una categoría anticipada no revierte otra válida.

**Razón**: bloqueos de fila y restricciones PostgreSQL protegen incluso con procesos o
peticiones concurrentes; un lock Python no lo hace. READ COMMITTED permite leer el estado
vigente tras esperar el bloqueo compartido con configuración.
Fuentes: [aislamiento PostgreSQL 18](https://www.postgresql.org/docs/18/transaction-iso.html),
[bloqueos explícitos](https://www.postgresql.org/docs/18/explicit-locking.html).

**Alternativas consideradas**: una transacción indivisible para todas las categorías;
consulta previa sin restricción; REPEATABLE READ para reconfigurar después de esperar.
No satisfacen independencia o coordinación con cambios concurrentes.

La identidad del intento se separa de la publicación lógica: una publicación rechazada
por anticipación se puede reenviar desde el límite. Un resultado terminal en caché por
publicación impediría ese reintento; la idempotencia se decide contra registros
efectivamente incorporados, no contra una publicación previamente rechazada.
El adaptador confiable persiste `attempt_id` y la entrada canónica antes de invocar
`Reception.accept`. `read_attempt` es lectura autorizada sin efectos: distingue
`not_found` de errorDB y expone resultados durables. Repetir accept con el mismo ID y
entrada recupera únicamente lo no confirmado; completed devuelve el resultado original,
incluso too_early, y otra entrada con ese ID falla attempt_payload_conflict. Un reenvío
explícito usa otro ID. La exclusión por intento protege dos recuperaciones y se obtiene
sin esperar manteniendo locks de contexto/categorías; no altera la independencia de
commits por categoría ni sus restricciones PostgreSQL.

## R3. El límite usa aceptación de plataforma y tiempo transcurrido

**Decisión**: `next_admissible_at = last_new_data_at + 900 segundos` sobre instantes UTC,
incluyendo CAT-01 incorporada. Obtener reloj actual de 009 después de bloqueos; no fecha
de fuente ni `CURRENT_TIMESTAMP` de una transacción que estuvo esperando. Usar tiempo
monotónico para esperas dentro del proceso y volver a validar elegibilidad durable antes
de confirmar. Duplicados/rechazos/consultas no mueven el estado.

**Razón**: UTC evita discontinuidades de hora local. PostgreSQL diferencia tiempo de
inicio de transacción de tiempo actual; [funciones de fecha](https://www.postgresql.org/docs/18/functions-datetime.html).
Los relojes monotónicos no se persisten entre arranques. El entorno debe mantener reloj
UTC sincronizado; un retroceso detectado bloquea conservadoramente hasta recuperar
elegibilidad, sin adelantar aceptación. No se promete resolver una alteración arbitraria
del reloj del host.

**Alternativas consideradas**: sumar quince minutos al texto local, confiar en timestamp
PAS600 o persistir un valor monotónico como si sobreviviera al reinicio.

## R4. Evidencia permanente de identidades y aportes

**Decisión**: separar el payload de detalle de un registro auxiliar durable con identidad
natural, energía normalizada, intervalo, origen/revisiones y estado de retirada. Unicidad
por identidad y exclusión `tstzrange` por edificio/categoría en ese registro; contigüidad
válida. Registrar una contribución única por agregado y registro incorporado. Mantenerlo
mientras la instalación pueda recibir reenvíos; esta versión no lo purga.

**Razón**: después de retirar detalle expirado hay que distinguir duplicado, conflicto,
superposición y dato nuevo, y preservar el agregado protegido. Las restricciones de rango
son apropiadas para esa exclusión: [rangos y exclusión](https://www.postgresql.org/docs/18/rangetypes.html).
`btree_gist` permite combinar claves escalares y rangos:
[extensión oficial](https://www.postgresql.org/docs/18/btree-gist.html).

**Alternativas consideradas**: recalcular desde detalle restante; tombstone con solo UUID;
hash sin comparación exacta; FK con cascada. Pierden aportes o capacidad de clasificar reenvíos.

## R5. Agregados exactos y cobertura independiente de su porcentaje mostrado

**Decisión**: para cada granularidad sumar directamente registros incorporados de la
misma categoría completamente contenidos; no sumar niveles entre sí. Representar kWh
internamente como coeficientes enteros de `q=10^-15` para acumular sin contexto fijo;
guardar NUMERIC sin escala coercitiva. Duraciones y cobertura usan microsegundos enteros.
El porcentaje se muestra con hasta seis decimales, pero el estado se determina con la
fracción exacta, antes de redondear.

**Razón**: no existe duración mínima de medición; no se puede limitar el número de
sumandos deduciéndolo de los quince minutos de recepción. La precisión 50 de 001 cubre
su suma de seis contribuciones, no todas las agrupaciones. Python ofrece enteros de
precisión ilimitada y Decimal con contexto explícito:
[tipos numéricos](https://docs.python.org/3.14/library/stdtypes.html#numeric-types-int-float-complex),
[Decimal](https://docs.python.org/3.14/library/decimal.html).
PostgreSQL [NUMERIC](https://www.postgresql.org/docs/18/datatype-numeric.html)
conserva exactitud dentro de sus límites, verificados antes de escribir.

**Alternativas consideradas**: float, NUMERIC con escala que redondee, precisión fija
50, promedios o rollups desde horas. Pueden perder energía o excluir datos válidos
para día/mes/año cuando cruzan límites horarios.

## R6. Calendario local, identidades UTC y límites reales

**Decisión**: generar límites con zona IANA y tzdata fijada en entorno. Día/mes/año
entre primeras horas válidas de sus límites locales; la hora repetida tiene dos bloques
identificados por UTC/offset, la inexistente no crea un bloque de duración cero. En
transiciones que no sean de una hora, conservar bloques reales delimitados también por
la transición, sin forzar 3600 segundos. Duración = fin UTC menos inicio UTC.

**Razón**: `zoneinfo` distingue ambigüedad mediante `fold`, pero las fechas locales
inexistentes requieren validación de ida/vuelta UTC. La resta de fechas con la misma zona
puede ignorar cambios de offset: calcular duración en UTC.
Fuentes: [zoneinfo](https://docs.python.org/3.14/library/zoneinfo.html),
[aritmética datetime](https://docs.python.org/3.14/library/datetime.html),
[PEP 495](https://peps.python.org/pep-0495/).

**Alternativas consideradas**: buckets de duración fija UTC para días; 30/365 días;
colapsar horas repetidas por etiqueta; restar horas locales sin convertir a UTC.

## R7. Conservación mínima y retirada controlada

**Decisión**: helper 009 de aniversario de doce meses para primera aceptación física,
primera incorporación calculada y última incorporación nueva a cada agregado.
Persistir zona y vencimiento; los vencimientos no disminuyen. Proteger payloads y
referencias necesarios por dependientes. No programar purga automática; proveer operación
interna de retirada que compruebe vencimientos/dependencias y preserve evidencia.

**Razón**: FR-015..018 requieren tanto consulta protegida como estabilidad tras retirada
permitida. Lecturas y duplicados no son revisiones sustantivas. Un 29 de febrero usa el
último día válido; horas inexistentes/repetidas se resuelven con política 009. La política
del dominio extiende dependencias, sin reimplementar el helper común.

**Alternativas consideradas**: TTL desde fecha medida, eliminación en cascada o purga
obligatoria al aniversario; pin de todo detalle de todos los agregados para siempre.
El registro auxiliar permite retirar payload expirado sin degradar el agregado.

## R8. CAT-01 pendiente, recuperación y siguiente lectura

**Decisión**: evaluar candidatos con `TotalCalculator` 001 y guardar pendientes/diagnósticos
con base y referencias inmutables. La aceptación de parciales nuevas crea/reactiva
`TotalEvaluationRequest` en su misma transacción, incluso antes de existir candidato.
Un trabajo 002 registrado en el
`lifespan` toma los mismos bloqueos, revalida y agrupa todos los candidatos elegibles
en una actualización CAT-01. Al arrancar y periódicamente busca solicitudes pendientes
sin candidato y candidatos pendientes de incorporación. Persiste resultado y solicitud
procesada juntos; rollback conserva la solicitud pendiente. El orden compartido de
bloqueos incluye una novedad concurrente o permite reactivar la solicitud después.
Recupera sin reenvío tras caída entre commit de parciales y creación del candidato,
y protege referencias.
GET no publica nada. Escritura de agregados sincrónica al commit de cada incorporación.

**Razón**: evita publicar CAT-01 antes de 900 segundos y satisface que la siguiente consulta
vea el estado confirmado. Un trabajo interno cumple el monolito; FastAPI documenta
[lifespan](https://fastapi.tiangolo.com/advanced/events/).

**Alternativas consideradas**: calcular en cada GET, cola solo en memoria, scheduler SMTP
de 008, recuperar solo candidatos ya existentes o agregación eventual. Rompen límite,
recuperación, propiedad o FR-014; recuperar solo candidatos pierde trabajo si la caída
ocurre antes de crearlos.

## R8a. Bloques futuros y fronteras temporales

**Decisión**: usar `not_started|ongoing|finished` según `cutoff_at < start`,
`start <= cutoff_at < end` y `cutoff_at >= end`. Conservar bloques futuros contenidos
y filtro solicitado; un bloque futuro sin aportes tiene energía null y cobertura cero.
La cobertura se calcula independientemente de esa clasificación.

**Razón**: “En curso” debe corresponder a un bloque ya iniciado. Las dos vistas usan
el mismo corte y las mismas fronteras exactas, incluida la igualdad en inicio y fin.
Esta precisión de FR-012 fue autorizada al resolver el análisis documental.

**Alternativas consideradas**: llamar en curso a todo bloque aún no terminado, rechazar
el filtro con futuro o recortarlo. Confunden el estado o impiden mantener la selección.

## R9. Consumidores y lecturas coherentes

**Decisión**: UoW REPEATABLE READ y corte común para toda lectura compuesta; copiar la
proyección antes de liberar transacción. `latest_admissible_window` devuelve solo ventana
terminada con cobertura completa, identidad y revisión; admite un cursor para detectar
datos tardíos. Si la zona de regla 008 difiere de la del edificio, calcular proyección
no persistida con los mismos aportes y límites de esa zona, sin reutilizar buckets de
otra zona. No convertir agregados horarios en demanda de quince minutos para 004.

**Razón**: los [puertos 001](../001-visualizar-consumo-categorias/contracts/integrations.md),
[004](../004-costos-tarifa-bt43/contracts/integrations.md),
[005](../005-generar-reportes-pdf/contracts/integrations.md) y
[008](../008-notificaciones-programables/contracts/integrations.md) exigen procedencia,
revisión, cobertura y su propia semántica. Un corte solo no reconstruye versiones
históricas arbitrarias: el consumidor que requiera reproducción conserva snapshot.

**Alternativas consideradas**: consultas separadas a distinto corte, sustituir CAT-01
física por calculada en costos, sumar parciales dos veces o leer datos privados en build.

## R10. Alcance de validación y dependencias externas

**Decisión**: pruebas de dominio y PostgreSQL desde fixtures que llaman al puerto real;
pruebas web con identidad real, gráfico/tabla contra misma respuesta; retiro/reinicio/
reenvío, años y DST controlados. Fuentes deben demostrar timestamps inequívocos,
intervalos y reenvío desde `next_admissible_at` mediante 003.

**Razón**: el repositorio contiene documentos, sin aplicación ni resultados de ejecución.
Doce meses sintéticos comprueban el mínimo sin esperar un año. SC-005 necesita personas,
no se acredita con Playwright.

**Alternativas consideradas**: dar por aceptada SFTP por inyectar fixtures, marcar
checklists al crear archivos, o afirmar rendimiento/compatibilidad sin ejecutar.
