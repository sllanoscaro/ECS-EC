# Contrato HTTP de consulta y configuración

[OpenAPI 3.1](openapi.json) es el esquema verificable de rutas/objetos.
[Modelo](../data-model.md) e [integraciones](integrations.md) fijan invariantes de dominio.
Base `/api/v1`; mismo origen que el frontend estático del monolito.

## Acceso y respuestas comunes

006 valida cookie opaca `ecs_ec_session`, cuenta activa, renovación completada y permisos
actuales en **cada** petición. Operador y Administrador técnico consultan; configuración
solo Administrador, también para GET. Programador/credenciales SFTP no son permisos web.
Cookie HttpOnly, SameSite=Lax y Secure bajo HTTPS. Toda respuesta protegida, incluidos
errores, lleva `Cache-Control: no-store`. No incrustar datos de instalación en el build.

PUT exige origen permitido y `X-CSRF-Token` ligado a sesión. La carga completa se valida
antes del cambio; actor, revisión, auditoría/eventos se confirman juntos. No se permite
editar mediciones, dar de alta cuentas ni iniciar una recepción por estos endpoints.

Estados: 200 éxito; 401 sesión inválida/ausente; 403 permiso, renovación pendiente, CSRF u
origen rechazado; 404 categoría/configuración inexistente; 409 revisión/configuración
incompatible; 422 campos/período inválidos; 503 DB/dependencia no disponible. Un resultado
sin datos es 200, distinto de error de consulta. Error `Problem` saneado con `code`,
`detail`, `operation_ref`, `field_errors:[{path,code,message}]`; sin SQL, rutas o secretos.

## GET /consumption/catalog

Sin filtros. Devuelve `building_id`, `timezone`, `cutoff_at`, `default_period` y exactamente
siete `categories` ordenadas CAT-01..07. Cada categoría incluye nombre/alcance, presencia,
modo/fuente lógica y base actuales; no contiene correspondencias nativas ni credenciales.
Incluye `category_revision` positiva por categoría o null antes de la primera configuración.
El período inicial es común a todas: extensión de mediciones conservadas del edificio,
o día actual del edificio sin datos. La lectura de extensión/configuración comparte captura.
La UI lo usa una sola vez si no tiene selección previa; cambiar categoría no lo reinicia.
Sin configuración inicial, mostrar categorías ausentes y no inferir orígenes; la zona del
contexto del edificio ya debe estar provisionada.

## GET /consumption/categories/{category_id}/detail

`category_id`: CAT-01..CAT-07. Query `start`, `end`, `timezone`, los tres obligatorios;
instantes ISO 8601 con offset y hasta seis decimales de segundo, zona IANA igual a la del
edificio. Comparar instantes UTC: `start < end`. El offset debe corresponder a la zona
en la hora declarada; una hora inexistente o ambigua sin resolución explícita es 422.
Los campos de fecha no se interpretan en la zona del navegador.

Respuesta única `DetailResult` para gráfico y tabla:

- Identidad de petición, edificio/categoría, período y corte de lectura coherente.
- `state: available|no_meter|no_data|incomplete`, independiente de carga/error de transporte.
- `source_mode: measured|calculated|mixed|unavailable`; segmentos de configuración con
  intervalo, revisión global, `category_revision`, modo, `source_id|null`, base y pares
  `basis_sources:[{category_id,source_id}]`. En CAT-01, identificar procedencia por fila/segmento.
- `rows`: exclusivamente datos incorporados, inicio >=start y fin <=end, ordenados por
  inicio/fin UTC e identidad. Cada fila tiene energía kWh cadena, originales si medida,
  o base y contribuciones si calculada, registro/revisión y primera incorporación.
  `configuration_revision` es la global vigente al inicio; `category_revision` identifica
  la fuente/configuración calculada estable en todo el intervalo. Las contribuciones
  incluyen su propia revisión de categoría. Cruzar revisiones globales ajenas es válido.
- `diagnostics`: candidatos no numéricos con intervalo y motivo `missing_contributions`,
  `pending_incorporation` o `calculation_configuration_changed`; revisiones, segmentos,
  categorías faltantes y próxima fecha cuando corresponda. Cambio calculado tiene
  `category_revision=null`, faltantes vacíos, próxima fecha null y segmentos de al menos
  dos revisiones CAT-01; no se presenta como faltantes ni como espera temporal.
- `warnings`: código, cantidad y mensaje; intervalos excluidos por cruzar límites,
  huecos observados, base vacía, cambio de disponibilidad y alcance parcial de la base.

No recortar intervalos. Contar cada intervalo excluido una vez aunque cruce ambos límites.
Si todos cruzan, `rows=[]`, `state=no_data` y aviso. Un hueco entre fin de una fila e inicio
de la siguiente no genera filas de cero ni implica una cadencia esperada desconocida.
Intervalos candidatos de diagnóstico también respetan contención y avisos de cruce.
Si hay diagnósticos y filas válidas, estado `incomplete` conserva esas filas; los diagnósticos
no se dibujan como energía ni se confunden con su tabla.

El dominio de una medición normalizada es `0 <= E < 10^30 kWh`, múltiplo exacto de
`10^-15 kWh`; el total calculado admite `0 <= T <= 6*(10^30-10^-15) kWh`. La respuesta
usa cadenas en notación fija, sin ceros fraccionarios insignificantes, y no limita los
originales según el número de dígitos de su unidad: la admisibilidad es por energía
normalizada. Nunca redondear para entrar al dominio. Los errores internos de recepción
`energy_out_of_supported_range` y `source_configuration_changed` son por registro en el
puerto 002, no un nuevo endpoint público. La definición exacta está en el modelo.

Una respuesta contiene el conjunto completo del período; no hay truncamiento, agregación
ni muestreo silenciosos. Un fallo para recuperarlo es error explícito, no una respuesta
parcial presentada como completa. La incorporación posterior de paginación requeriría
actualizar ambos contratos/vistas con alcance y captura explícitos.

GET no incorpora totales, no inicia tareas ni modifica fechas de conservación. CAT-01
medida mantiene sus huecos aunque existan parciales; calculada solo lee incorporaciones
confirmadas por 002. Hora/día/mes/año son una ampliación HTTP de 002, no parámetros
admitidos a medias por este endpoint de detalle.

## GET /consumption/configuration

Solo Administrador. Devuelve última revisión registrada de instalación, edificio, zona,
vigencia y siete entradas; cada una añade la `category_revision` calculada por servidor a
los IDs/etiquetas de fuentes, nunca sus secretos. Es un campo de salida, no aceptado en PUT. Antes de la
primera revisión devuelve 404 `configuration_missing` y la UI permite crearla.

## PUT /consumption/configuration

Carga `ConfigurationInput`: `expected_revision` (0 para primera), `effective_from`,
`timezone`, `categories` (siete entradas únicas con `category_id`, `has_meter`, `source_id`,
`source_label`). Con medidor, UUID/etiqueta no vacíos; sin medidor ambos null. UUID nuevo
crea origen estable y UUID ya conocido conserva su identidad; no reutilizarlo para otro
medidor. No repetir una fuente en categorías distintas. CAT-01 calculada no recibe UUID
de medidor ficticio: la base se deriva en servidor.

La primera revisión puede cubrir una importación histórica. Cambios posteriores deben
ser efectivos desde el instante de aplicación, no retroactivos ni programados: el cliente
puede enviar null en `effective_from` para que el servidor fije su reloj. Un valor explícito
en revisiones posteriores debe coincidir con ese instante según la precisión del contrato;
se recomienda null. Determinar en servidor las categorías cuya firma cambia, incluida
CAT-01 por modo/base/fuentes cuando corresponda, y consultar
`MeasurementStore.read_reconfiguration_bounds` en la misma UoW de escritura y bajo los
bloqueos compartidos con recepción. Rechazar si su máximo fin aceptado es posterior a ese
instante. El estado incluye incorporaciones retiradas del detalle; ausencia/fallo del
proveedor o claves incompletas produce 503, no historia vacía ni modificación parcial.
La zona es inmutable desde la primera historia aceptada, aun tras retirar detalle.
Solo la primera configuración sin revisiones previas puede prepararse antes de existir 002.

Una nueva revisión global conserva la `category_revision` de cada categoría cuya firma
permanezca igual. Etiquetas descriptivas no la cambian. La recepción tardía resuelve todos
los segmentos históricos de su categoría; solo un cambio de su propia fuente/presencia
dentro del intervalo causa `source_configuration_changed`, sin dividirlo. Para CAT-01
calculada, cambiar modo/base/fuentes dentro del intervalo produce el diagnóstico
`calculation_configuration_changed`, sin total ni descarte de parciales válidas.
PUT sin cambio efectivo devuelve
la revisión actual sin crear evento ni modificar vigencia; reenvío con revisión anterior
devuelve 409, nunca otra revisión automática. Revisión esperada errónea: recargar antes
de editar; no sobrescribir cambios de otra persona.

Respuesta 200 `Configuration` con revisión nueva y fechas confirmadas. La operación es
atómica respecto de recepción/cambio de fuentes. No reescribe totales anteriores ni
dispara incorporación en GET. La edición administrativa es la integración de consumo
con permisos/layout de 006; no implementa la administración general de identidad.
