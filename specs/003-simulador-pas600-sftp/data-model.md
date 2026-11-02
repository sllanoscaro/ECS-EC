# Modelo de datos: Simulación y adquisición PAS600

[Spec](spec.md), [plan](plan.md), [perfil](contracts/pas600-profile.md),
[recepción](contracts/sftp-reception.md), [CLI](contracts/cli.md).
Diseño previo a implementación. Decimales exactos, UTC y zona IANA explícita;
intervalos `[start,end)`. Código y rutas siguientes son previstos.

## Separación de almacenes

El simulador usa archivos locales privados; no requiere PostgreSQL ni importa backend.
El receptor guarda metadatos/estados en PostgreSQL 18 y bytes inmutables en volumen
persistente de adquisición dentro del despliegue común. 003 posee sus tablas/migración;
001 posee catálogo/fuentes, 002 mediciones/resultados/estado temporal/agregados y 009
UoW/reloj/auditoría. FK y referencias históricas protegidas, sin DELETE CASCADE.

## Entidades locales del simulador

| Entidad | Campos y reglas |
| --- | --- |
| `SimulationScenario` | `schema_version`, `algorithm_version`, `profile_id`, `seed`, `publisher`, siete estados de categoría, medidores/canales presentes, período UTC y zona, muestreo, `publication_time`, formato, rangos y anomalías. Configuración lógica canónica sin secretos. |
| `SimulatedPublisher` | Nombre, serial, remoteId, IP/MAC sintéticos explícitos; uno por escenario. No se confunde con el medidor. |
| `SimulatedMeterChannel` | Modelo iEM3150, identidad local/ReducedID únicos por PAS600, categoría medida única, descriptor del canal, inicial acumulada y unidad. Sin origen ficticio para CAT-01 calculada. |
| `ExpectedSample` | Clave lógica determinista categoría/origen/canal/índice, inicio/fin, energía prevista, contador previo/posterior cuando corresponda y estado normal. No aparece en los bytes nativos. |
| `AnomalyAssignment` | Clase `missing\|format\|out_of_range`, índice/muestra, antes/después, causa y alcance; una clase por muestra. Archivo corrupto tiene asignación aparte por archivo/operación. |
| `LocalPublication` | Clave lógica estable, tiempo simulado, categorías, lista completa de archivos con nombre/tamaño/hash, perfil, manifiesto canónico. Cambiar bytes exige nueva generación, nunca reintento. |
| `LocalRun` | UUID de ejecución real, hash de configuración lógica, rutas de datos/informe/journal, fecha real, estado `generating\|generated\|publishing\|stopped\|completed\|failed`. |
| `TransferAttempt` | UUID real, publicación, ordinal, inicio/fin UTC y duración monotónica, destino saneado, resultado por archivo, código de fallo, próxima espera. Sin valores de secretos ni volcado de configuración de transporte. |
| `ControlReport` | Snapshot lógico antes de alteración, asignaciones exactas, conteos por categoría/archivo, manifiestos y referencias al journal; `not_configured` difiere de categoría medida con 100 % de omisión. |

Los secretos se resuelven solo en memoria desde entorno/archivo protegido. El informe
no copia esos valores ni rutas sensibles de claves; usa un alias opaco de destino.
Archivos locales de estado usan escritura temporal, fsync y rename atómico; un candado
por destino/publicador protege la cadencia entre procesos. El journal conserva ordinales
al reiniciar. Una nueva ejecución no permite eludir el candado ni el plazo.

## Calendario, tasas y valores

`start < end`, extremos con offset, zona IANA válida y diferencia divisible por muestreo.
Cada intervalo completo pertenece a N; no truncar el último silenciosamente. Para
acumulados generar N+1 lecturas, con una referencia inicial no alterable por las tasas.
Una hora repetida es dos instantes UTC distintos. El período se recorre por duración
real del muestreo y se proyecta a la zona; no fabricar horas inexistentes.

Rangos por categoría: energía `min>=0`, `max>=min`, finitos, unidad y duración exactamente
iguales al canal/intervalo una vez convertidos. Rechazar si no hay valor representable
con el quantum. No escalar rangos sin una regla explícita. Valores normales y sus
sumas acumuladas deben ser finitos y representables en el descriptor.

`n_missing=floor(N*p_missing/100)`, análogamente formato y fuera de rango. Tasas Decimal
entre 0 y 100 y suma <=100. Ranking SHA-256 con dominios separados produce selección
estable de cada clase entre posiciones aún libres; posiciones explícitas deben tener
exactamente el conteo requerido, ser válidas y no solaparse. Las categorías sin medidor
no tienen N ni asignaciones. No asignar muestras a categorías desconocidas/inactivas.

Outlier superior: `max+quantum`; inferior: `min-quantum`, con conversiones exactas.
En acumulados se altera el incremento y desplaza el resto de contadores para no inducir
otros incrementos fuera de rango; si el caso no puede representarse bajo el descriptor,
rechazar la combinación antes de generar. Defectos de tipo/fecha y omisiones afectan
la observabilidad de extremos: el informe separa posiciones deliberadas de intervalos
que no podrán normalizarse por faltar uno de sus extremos. Un archivo roto tiene su
conteo propio aunque contenga otras asignaciones; no reclasifica todas sus muestras.

## Entidades propias del receptor 003

UUID internos generados por el servidor; revisiones positivas; `timestamptz`, NUMERIC y
JSONB tipado. Nombres/IDs remotos son entradas no confiables, no identidades de auditoría.

| Entidad | Campos y relaciones |
| --- | --- |
| `AcquisitionBinding` | `id`, `revision`, `building_id`, identidad técnica SFTP autorizada, publicador permitido, directorio virtual, perfil, descriptores nativos y correspondencia con `MeasurementSource` 001, zona/muestreo, estado habilitado. Versiones históricas inmutables. No crea fuentes ni revisiones 001. |
| `SftpSessionAttempt` | `id`, binding/revisión capturada, inicio/fin reales, `receiving\|sealed\|aborted`, causa, manifiesto sellado nullable, `publication_id\|null`, correlación interna y plazo. Sesión exclusiva, sin handles reutilizados entre intentos. |
| `ReceivedFile` | `id`, sesión, nombre nativo, clave de staging interna, tamaño/hash al cierre, rango de offsets escritos, CLOSE explícito, `writing\|closed\|sealed\|aborted`; `parse_status: pending\|parsed\|unreadable`, diagnóstico seguro, plazo. |
| `NativePublication` | `id`, binding/revisión semántica/perfil/publicador/ciclo nativo, `publication_ref`, lista ordenada de nombres/tamaños/hashes y bytes asociados, perfil/revisión, `sealed_at`, `queued\|processing\|evaluated\|partial_failure`, plazo. Comparar lista además del hash. |
| `PublicationEvaluation` | `id`, publicación, correlación interna, `attempt_id`002 nullable antes de preparar la entrada, `input_schema_version` positiva nullable, `input_records` canónicos ordenados nullable e `input_digest` SHA-256 nullable, fechas, `pending\|processing\|completed\|partial_failure`, resultados de adaptación y referencias a resultados durables002. ID/entrada/digest se fijan juntos antes de llamar002; una reevaluación tiene nuevo ID, recuperación conserva el suyo. |
| `NativeReading` | `id` de observación, edificio/publicador/medidor/canal, binding/revisión semántica, instante UTC nullable si ilegible, token/valor/unidad/estado original, archivo+posición, estado `valid\|invalid\|conflict\|reference_only`, referencia canónica válida nullable, plazo y evidencias de reenvío. |
| `IntervalCandidate` | `id`, origen/categoría/inicio/fin, unidad/valor exactos, referencias a extremo(s) nativos, perfil/revisión, clave de evidencia estable. Sin crear aceptación propia. |
| `AdaptationResult` | evaluación/archivo/posición, `parsed\|invalid\|reference_only\|gap\|counter_decreased\|unsupported_quantity\|candidate\|conflict`, causa y candidato nullable; distingue alcance archivo/registro/intervalo. |

`ReceivedFile` no deduce completitud del parseo. Su copia sellada es inmutable y un reenvío
no sobrescribe original. `NativePublication` se enlaza con muchos intentos SFTP/evaluaciones;
la deduplicación del contenido no suprime nuevas evaluaciones de candidatos rechazados.
Conservar cada observación nativa inmutable, incluidas inválidas. Solo la primera
observación válida reserva la lectura canónica de esa identidad; una inválida no bloquea
una corrección válida posterior. Otra válida equivalente agrega evidencia; otra válida
diferente conserva la primera válida y registra conflicto, sin sobrescribir pares.

Unicidad de observación: archivo/serie/posición. Unicidad de lectura canónica válida:
binding/revisión semántica/origen/canal/instante; semántica incompatible exige
nueva versión/segmento, nunca sustituir la lectura vieja. Unicidad de candidato:
edificio/origen/categoría/inicio/fin y pares originales equivalentes. Los conflictos se
registran, no se resuelven por orden de llegada de una relectura. La identidad definitiva
incorporada y exclusión de intervalos siguen siendo las de 002.

## Transformación de acumulados y recuperación

Lecturas válidas consecutivas y compatibles t0,t1 con `t1=t0+sampling`:
`E([t0,t1))=C(t1)-C(t0)`. Sin primera referencia, nada que incorporar; igualdad produce
cero válido con cobertura. Omisión, inválida o descenso impide ese par, sin repartir
energía ni saltar al último extremo disponible. Un descenso inicia nuevo segmento de
referencia; con siguiente extremo válido se reanuda. Un dato tardío permite formar pares
adyacentes que antes faltaban, manteniendo referencias y candidatos ya incorporados.
Para `interval` se conserva el valor y el intervalo definido por timestamp_role y sampling.

Preparar ledger/candidatos y evaluación pendientes en UoW propia003 antes de llamar002.
Si hay entrada para recepción, generar y persistir `attempt_id`, `input_schema_version`,
`input_records` y digest junto con correlación/edificio/publicación; no dejar solo el ID
sin la entrada que permite repetir exactamente la llamada. Tras ese commit son inmutables;
no regenerarlos desde un ledger que pudiera recibir nuevas lecturas tardías. Una evaluación
sin entrada para002 puede conservar esos campos null. No mantener bloqueos003 mientras002
adquiere los suyos. Después guardar referencias al resultado durable.

Si se pierde respuesta, consultar `Reception.read_attempt` del contrato002 y repetir
`Reception.accept` con el mismo ID/entrada solo para crear o completar trabajo inconcluso.
`not_found` exige lectura autorizada satisfactoria, no se infiere de falloDB; el puerto
coordina recuperaciones concurrentes. Un intento completado conserva sus clasificaciones,
fechas y resultados originales; otra entrada con igual ID produce `attempt_payload_conflict`.
Solo un reenvío explícito completo abre evaluación e intento nuevos, aun con igual
publicación. Un `too_early` confirmado no se reevalúa al recuperar ni programa aceptación
física automática;002 informa próxima admisible para revisión/reenvío.

El trabajo de adquisición procesa publicaciones selladas y recupera evaluaciones
inconclusas al arrancar. Estados/claims PostgreSQL impiden trabajos concurrentes duplicados;
si se repite una llamada tras caída se conserva ID de intento 002. No se avanza un cursor
que descarte pares rechazados. No procesar desde GET ni desde el cierre de un solo archivo.

## Proyecciones de exportación y comparación

`AcquisitionExportSnapshot` es una proyección JSON local, sin tabla nueva: schema_version,
snapshot_id UUID, cutoff_at UTC, publicación/manifiesto, evaluaciones/resultados durables
visibles al corte y selection `{building_id,category_ids,period:{start,end,timezone},view}`.
View admite `detail|hour|day|month|year`; categorías únicas, período creciente y zona/offsets
validados con los contratos001/002. Incluye `consumption_snapshot` con
`status: available|unavailable`, reason_code null solo si available, detail_results y
aggregate_results. Para detail se usa solo la primera lista; para otras vistas solo la
segunda, un resultado real por categoría. Unavailable lleva ambas vacías y causa explícita;
no significa sin consumo ni cobertura cero. Lectura de recepción/consumo comparte UoW
REPEATABLE READ y corte009; si se pierde la captura no se exporta un snapshot coherente
ficticio. No se envía el oráculo al receptor para construir esta selección.

`ComparisonResult` conserva snapshot_id/cutoff_at/selección, diferencias y limitaciones,
con `comparison_status: complete|partial|not_evaluable`. Complete solo si el alcance
declarado tiene evidencia suficiente; resultados parciales no producen código0 sin
diferencias. Los códigos5/6 y las condiciones exactas siguen el [contrato CLI](contracts/cli.md).
Las consultas no prolongan conservación ni reconstruyen por fecha una captura histórica.

## Durabilidad, plazos y límites

El cierre explícito confirma archivo solo después de fsync de sus bytes/evidencia. El
sellado guarda manifiesto durable y promueve staging a ubicación inmutable; usar
transiciones recuperables: archivo faltante tras crash = pendiente/error, nunca lote
completo inventado. El `CLOSE` implícito al limpiar una conexión abortada no equivale a
cierre exitoso del cliente. El EOF limpio puede perderse después de transferir todos los
archivos: estos figuran transferidos en el cliente, pero sin lote sellado en el receptor.
Un reenvío completo recupera esa incertidumbre.

Resultados/lecturas/archivos sellados conservan mínimo doce meses calendario desde
registro o revisión sustantiva con helper 009 y zona/plazo persistidos. Evidencia necesaria
por una medición protegida se conserva hasta el máximo plazo de sus dependientes.
Sin purga automática inicial; registrar y revisar staging abortado con cuota, sin borrar
pendientes silenciosamente. Retener identidades/manifiestos/candidatos suficientes para
reintentos e idempotencia posteriores. Informes locales permanecen hasta retiro explícito
por la persona, no heredan automáticamente el almacenamiento funcional del servidor.

Límites iniciales de protección del receptor, configurables: JSON <=256000 bytes,
CSV <=8 MiB, <=10000 archivos/sesión y <=128 MiB/sesión; <=2 sesiones activas por binding,
solo una publicación en escritura por publicador. Rechazar antes de exceder cuota, con
causa `resource_limit`, abortando el lote, sin afirmar entrega completa. No son máximos
físicos del PAS600 ni SLO. La generación histórica local no tiene esas cuotas de red;
para publicar se divide en ciclos separados respetando cadencia y límite configurado.
