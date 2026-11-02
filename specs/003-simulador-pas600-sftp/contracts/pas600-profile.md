# Contrato del perfil PAS600

Perfil `pas600-doca0172en19-energy-v1`. [Investigación](../research.md),
[modelo](../data-model.md), [recepción](sftp-reception.md).
Normativo para el diseño del simulador/adaptador; no acredita conformidad ejecutada.
Referencia externa: [DOCA0172EN-19](https://www.productinfo.schneider-electric.com/ecostruxurepanelserverguide/doca0172-ecostruxure-panel-server-user-guide/English/Panel-Server-User-Guide-DOCA0172EN-19.pdf),
pp. 126–127 y 274–276. Los nombres de campos son del protocolo del fabricante.

## Alcance y descriptor

Un PAS600 Universal publicador, cero a siete medidores configurados, un canal de energía
por categoría medida y período de muestreo común por ejecución. La configuración inicial
contiene siete medidores; CAT-01 medida conserva su valor independiente. Con CAT-03/CAT-05
presentes sin medidor total solo se serializan esos dos; 001/002 obtiene CAT-01 calculada.
Un escenario sin medidores es válido para validar ausencia y genera cero archivos.

El descriptor versionado de cada canal fija exactamente:

| Campo de configuración | Significado |
| --- | --- |
| `publisher_serial`, `publisher_remote_id` | Identidad CSV y JSON del mismo PAS600; correspondencia explícita, no algoritmo supuesto. |
| `device_local_id`, `reduced_id`, `device_name`, `device_type_id`, `device_type_name` | Identidad y metadatos CSV; modelo simulado iEM3150, ID local único. |
| `csv_topic_id`, `csv_measurement_name`, `json_value_item_id` | Identidades nativas equivalentes del canal, sin inferencia por texto traducido. |
| `unit`, `semantics`, `timestamp_role` | `Wh\|kWh\|MWh`, `cumulative\|interval`, `reading_instant` para contador o `interval_end\|interval_start` explícito. |
| `sampling_minutes`, `initial_counter`, `quantum` | Minutos enteros positivos; inicial no negativo para acumulados; quantum decimal positivo exactamente convertible a kWh. |
| `provenance` | Revisión documental, procedencia del descriptor/topología o marca `synthetic`, evidencia y checksum cuando exista. |

El perfil de prueba adopta inicialmente 15 minutos. Otros minutos enteros positivos
requieren descriptor con evidencia de soporte; no se acepta frecuencia arbitraria
incompatible bajo la etiqueta de conformidad PAS600. No se emulan Modbus/RS485.
Un canal de intervalo solo se habilita con descriptor que lo demuestre; no se atribuye
esa capacidad a todos los iEM3150. El contador de energía activa es el caso inicial.
Una configuración sintética permite pruebas locales, pero no certifica sus IDs contra
un equipo real. Antes de instalar un origen real se importan sus identidades verificadas
(por ejemplo, correspondencias de `diagnostic_topology.txt` indicadas por el fabricante).

## Nombres, división y tiempos

| Formato | Nombre final y agrupación |
| --- | --- |
| CSV | `ReducedID_DeviceName_YYYYMMDDhhmmssSSS_n.csv`, un dispositivo y frecuencia por archivo. |
| JSON | `YYYYMMDDhhmmssSSS_n.json`, varias series/dispositivos de la misma frecuencia. |

`n` comienza en 1 dentro de su grupo nativo y es contiguo. Un CSV se divide por dispositivo;
JSON por publicación/frecuencia. Límite temporal de cada archivo: hasta 24 horas de
muestreo, cortando por duración UTC; JSON además <=256000 bytes UTF-8, criterio
conservador para el límite documental de 256 KB. Dividir antes de sobrepasarlo sin partir
un registro; repetir envoltura y referencia temporal válida. El límite incluye envoltura.
No hay máximo N derivable solo del último índice recibido. Los índices no son un commit.

Los caracteres de nombre prohibidos por el fabricante se reemplazan por `~`; conservar
UTF-8 permitido, impedir separadores/traversal y detectar colisiones después de sanear.
La fecha del nombre es la de publicación del escenario, con milisegundos, fija entre
reintentos. El escenario fija `publication_time` y su zona/offset: no usar el reloj de
transferencia para regenerar nombres. No usar el nombre como instante de medición.
En JSON se fija también el timestamp del mensaje de la publicación simulada.

## CSV

UTF-8, separador coma, punto decimal, campos entre comillas dobles con escape CSV;
el emisor usa CRLF. El lector admite LF y CRLF sin modificar la evidencia original.
La estructura tiene siete filas previas al primer dato:

| Fila | Contrato |
| --- | --- |
| 1 | Diez títulos nativos de metadatos del gateway, dispositivo y muestreo del apéndice D. |
| 2 | Los diez valores correspondientes, incluido `Logging Interval` en minutos y `Historical Intervals`, número de filas de datos de ese archivo. |
| 3 | Vacía. |
| 4 | Posiciones de encabezados de tópicos según el apéndice, incluidas celdas vacías de presentación. |
| 5 | Tópicos nativos en las posiciones correspondientes. |
| 6 | Vacía. |
| 7 | `Error`, offset UTC en minutos, fecha local y nombres/unidades de las magnitudes. |
| 8+ | Estado, offset, fecha local `YYYY-MM-DD HH:MM:SS` y valores en orden de magnitud. |

El emisor usa tres celdas vacías iniciales en filas 4/5, según la nota de las tres comas
del apéndice. El lector admite la variante de cuatro celdas vacías de su extracción
textual y enlaza tópicos por orden, sin desplazar las columnas de medición de la fila 7. No tratarlo como CSV plano
con una cabecera propia. Una fila válida usa Error 0; Error 19/NaN representa ausencia o
invalidez, no cero. El lector distingue fallos por celda de estructura ilegible; no debe
desechar los registros independientes válidos cuando la estructura permite localizarlos.
`Historical Intervals` se calcula después de omisiones y antes de corrupción estructural.
Un archivo sin filas omitidas no se inventa para un medidor inexistente.

`instant_UTC = local_timestamp - offset_minutes`. Comprobar el offset contra la zona
IANA del binding/descriptor; una hora repetida usa el offset para desambiguar. Un offset
inconsistente o fecha imposible es diagnóstico por registro, no reparación automática.

## JSON

Un objeto raíz con `$schema` del tipo CewsMessage y `message`. El mensaje contiene
`remoteId`, `contentType=data`, `cewsVersion=3.0.0`, `timestamp` y
`content.data.timeseries`. Cada serie usa `valueItemId`, `timestamp` UTC base y `records`;
cada registro usa `v`, `t` (milisegundos enteros desde la base) y opcional `s` de calidad.
El emisor normal omite `s`; no interpreta su ausencia como muestra faltante.
El perfil inicial trata `s=false` como medida inválida, conforme al ejemplo de la tabla
documental. No usa `s=true` para afirmar calidad válida: se clasifica
`unsupported_quality` hasta disponer de un descriptor de calidad contrastado; conservar
siempre el indicador original. Probar este subconjunto con casos independientes. No
introducir `s` para revelar anomalías.

`instant_UTC = series.timestamp + t milliseconds`. Valores de energía son tokens numéricos
JSON finitos codificados con Decimal; jamás float o cadenas añadidas solo para acomodar
el modelo HTTP. El receptor conserva tokens originales y rechaza tipos incompatibles.
No confiar en un nombre para deducir unidad: JSON la obtiene del descriptor verificado.

## Ejemplos y conformidad independiente

[Ejemplos CSV/JSON y oráculo aritmético](examples/README.md) contienen el caso
100/104 kWh, con correspondencias sintéticas declaradas fuera de los archivos.
Son ejemplos de diseño contrastados documentalmente, no capturas físicas ni pruebas
ejecutadas. Las variantes de celdas vacías de presentación de CSV se describen allí.

No se copia una muestra de IO/tensión cambiando su etiqueta para llamarla iEM3150.
Los casos mínimos de referencia a preparar durante implementación son:

| Caso | Oráculo independiente y resultado conocido |
| --- | --- |
| CSV documental | Tabla del apéndice D transcrita/revisada con procedencia y hash; metadatos/tópicos/offset/filas conocidos, aunque su magnitud sea tensión y no se incorpore a consumo. |
| JSON documental | Ejemplo del apéndice D: envoltura, dos series y offsets revisados; IO se identifica como magnitud no admitida para energía. |
| Energía de prueba | Descriptor declarado sintético, dos lecturas 100/104 kWh a 00:00/00:15 UTC: un consumo 4 kWh, primer extremo solo referencia. CSV y JSON representan exactamente esos mismos instantes/valores. |
| Instalación | Descriptor/topología real con procedencia y, cuando exista equipo, archivo capturado; no sustituye la revisión documental fija ni se afirma obtenido ahora. |
| Fragmentación | >24 horas y JSON >256000 bytes: todos los registros una vez, nombres/índices/cortes correctos y equivalencia lógica sin depender del lector ECS-EC. |

Los fixtures revisados viven en `backend/tests/fixtures/pas600/reference/` y
`tools/pas600_simulator/tests/fixtures/reference/`, con resultados esperados estáticos
revisados contra la fuente, nunca generados con el serializador bajo prueba. Los ejemplos
de energía adicionales deben contrastarse con reglas documentales, sus descriptores y
un lector de pruebas independiente; el round-trip emisor/receptor por sí solo no acredita
FR-004 ni SC-001. No se han creado fixtures de conformidad ejecutada durante el plan.
