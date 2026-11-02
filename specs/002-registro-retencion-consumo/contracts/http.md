# Contrato HTTP: registros agrupados de consumo

[Modelo](../data-model.md), [integraciones](integrations.md), [UI](ui.md).
Contrato normativo en Markdown; tipos/tablas y ejemplo se verifican mediante pruebas
de contrato al implementar. Base `/api/v1`, mismo origen que el frontend estático.
La documentación OpenAPI de FastAPI deberá reflejar este contrato y convivir con
[HTTP/OpenAPI 001](../../001-visualizar-consumo-categorias/contracts/http.md).
No se añade una API pública de ingesta o retirada.

## GET /consumption/categories/{category_id}/aggregates

Operador y Administrador técnico con sesión vigente pueden consultar; 006 comprueba
cuenta, renovación completada y permiso actual en cada petición. Cookie opaca
`ecs_ec_session`; no credenciales SFTP ni perfil Programador como autorización funcional.
GET es lectura sin CSRF de escritura; todos los resultados protegidos, incluidos errores,
usan `Cache-Control: no-store`. No datos privados en HTML del build.

| Parámetro | Tipo / regla |
| --- | --- |
| `category_id`, path | `CAT-01`..`CAT-07`; las siete permanecen seleccionables. |
| `start`, query obligatorio | ISO 8601 con offset, hasta microsegundos; inicio incluido. |
| `end`, query obligatorio | ISO 8601 con offset, hasta microsegundos; fin excluido y posterior a inicio UTC. |
| `timezone`, query obligatorio | Zona IANA igual a la del edificio. No usar zona del navegador. |
| `granularity`, query obligatorio | `hour|day|month|year`. |

Validar correspondencia de offset con fecha/zona, incluidas horas repetidas explícitas.
Una fecha inexistente, offset incorrecto, precisión no representable o intervalo
inválido devuelve 422. Esta API siempre agrupa en zona del edificio; la proyección
por zona de regla para 008 es un puerto interno distinto, definido en integraciones.

La respuesta enumera todos los bloques de esa granularidad totalmente contenidos en
`[start,end)`, ordenados por inicio UTC. No cambia el filtro, no redondea sus límites y
no prorratea extremos. Dos bloques repetidos con igual etiqueta local conservan distintos
offsets/instantes. No se exige que el período esté terminado: puede contener el bloque
calendario completo que sigue en curso al corte. Los extremos parcialmente incluidos
se explican en `excluded_blocks`; si ninguno cabe, `blocks=[]` y motivo explícito.
Los bloques futuros totalmente contenidos también se devuelven, con estado
`not_started`, conservando el filtro; sin contribuciones tienen energía null y cobertura cero.

No hay paginación parcial silenciosa. Si en implementación se requiere un límite de
recursos, deberá acordarse un contrato explícito antes de recortar períodos/resultados.

## AggregateQueryResult

Respuesta 200, objeto único para gráfico/tabla. Campos presentes; null significa ausencia
expresa. Energía decimal en formato canónico sin exponente, no JSON number.

| Campo | Tipo / significado |
| --- | --- |
| `request_ref` | UUID interno para asociar selección y respuesta. |
| `building_id`, `category_id` | UUID del edificio y categoría solicitada. |
| `period` | `{start,end,timezone}`, filtro exacto validado con offsets. |
| `granularity`, `unit` | Agrupación elegida y constante `kWh`. |
| `cutoff_at` | Fecha UTC de la captura coherente, no fecha del consumo. |
| `state` | `available|incomplete|no_data|no_meter`; no representa carga/error de transporte. |
| `source_mode` | `measured|calculated|mixed|unavailable` según segmentos históricos. |
| `configuration_segments` | Los mismos objetos de procedencia 001: límites, revisiones, modo/fuente, base y pares categoría/fuente. |
| `blocks` | Lista de `AggregateBlock`; incluye bloques sin datos proyectados. |
| `excluded_blocks` | `[{start,end,reason_code}]` con `filter_start|filter_end|filter_both`, sin duplicar el mismo bloque. |
| `diagnostics` | Candidatos CAT-01 sin valor, con motivos/campos 001, acotados al filtro. |
| `warnings` | Lista tipada `{code,start?,end?,record_refs?,detail}` saneada. |
| `reason_code` | Null o motivo global, como `no_complete_blocks`, `no_calculation_basis` o `no_history`. |

`configuration_segments` y `diagnostics` conservan el contrato de 001, con
`category_revision` estable y revisiones globales históricas; no usar base actual para
historia. Cambiar de modo/base dentro de un bloque no invalida sus registros válidos,
pero obliga a identificar la procedencia por segmentos/aportes.

`AggregateBlock`:

| Campo | Tipo / regla |
| --- | --- |
| `aggregate_id`, `revision` | UUID/revisión positiva del agregado persistido; ambos null para bloque sin contribuciones. |
| `start`, `end`, `timezone` | Límites del bloque con offsets reales y zona IANA del edificio. |
| `duration_us`, `covered_duration_us` | Cadenas de enteros >=0; duración total estrictamente positiva. |
| `energy_kwh` | Cadena Decimal >=0 si hay contribuciones; null si no hay ninguna. |
| `coverage_percent` | Cadena entre 0 y 100, hasta seis decimales; se calcula desde duraciones exactas. |
| `coverage_state` | `complete|incomplete|no_data` según fracción exacta, antes de redondear porcentaje. |
| `temporal_state` | `not_started|ongoing|finished`: `cutoff_at < start`, `start <= cutoff_at < end` o `cutoff_at >= end`, respectivamente. |
| `contribution_count` | Entero >=0; cero solo para bloque sin contribuciones. |
| `source_mode` | `measured|calculated|mixed|unavailable` del bloque. |
| `provenance_segments` | Lista de límites, modo/fuente/base/pares y revisiones históricas que explican sus aportes. |
| `created_at`, `last_new_data_at`, `retain_until` | Fechas UTC del agregado; null si es proyección sin contribuciones. |
| `warnings` | Códigos/detalles propios de cruces, huecos, base parcial o detalle retirado. |

La energía suma únicamente registros incorporados de la categoría totalmente contenidos;
cada registro contribuye una vez al nivel. Una lectura que cruza bloque queda en detalle
y aviso, sin energía o cobertura en ese bloque. Los agregados CAT-01 usan su propia
serie incorporada, sin añadir parciales. Medido cero cubierto = `"0"` y cobertura >0;
sin lecturas = null y cobertura cero. La duración es UTC, nunca horas locales restadas.

Estado global: `no_meter` solo para parcial sin fuente durante todo el filtro; de otro
modo `no_data` si no hay energía incorporada ni diagnóstico calculado; `incomplete` si
hay diagnósticos, bloque con cobertura parcial o combinación de bloques con y sin datos;
`available` para los demás resultados con datos. El estado de cada bloque conserva las
dos dimensiones; un período en curso sigue identificado aunque tenga datos.

Avisos mínimos según evidencia: `measurement_crosses_block`, `filter_excludes_block`,
`partial_calculation_basis`, `no_calculation_basis`, `before_operation`,
`detail_withdrawn`, `unconfigured_period` y `missing_coverage`. Un porcentaje agregado
no afirma que la base calculada mida todas las cargas del edificio.
La retirada permitida de detalle no reduce energía/cobertura de un agregado protegido.

## Ejemplo: una hora terminada al 75 %

Tres intervalos de quince minutos, 1 kWh cada uno, aceptados con el mismo instante de
actualización permitido. UUID y fuente son sintéticos.

```json
{
  "request_ref": "00000000-0000-4000-8000-000000000002",
  "building_id": "00000000-0000-4000-8000-000000000001",
  "category_id": "CAT-03",
  "period": {
    "start": "2026-10-31T10:00:00-03:00",
    "end": "2026-10-31T11:00:00-03:00",
    "timezone": "America/Santiago"
  },
  "granularity": "hour",
  "unit": "kWh",
  "cutoff_at": "2026-10-31T15:00:00Z",
  "state": "incomplete",
  "source_mode": "measured",
  "configuration_segments": [{
    "start": "2026-10-31T10:00:00-03:00",
    "end": "2026-10-31T11:00:00-03:00",
    "configuration_revision": 1,
    "category_revision": 1,
    "source_mode": "measured",
    "source_id": "00000000-0000-4000-8000-000000000004",
    "base_categories": [],
    "basis_sources": []
  }],
  "blocks": [{
    "aggregate_id": "00000000-0000-4000-8000-000000000003",
    "revision": 1,
    "start": "2026-10-31T10:00:00-03:00",
    "end": "2026-10-31T11:00:00-03:00",
    "timezone": "America/Santiago",
    "duration_us": "3600000000",
    "covered_duration_us": "2700000000",
    "energy_kwh": "3",
    "coverage_percent": "75",
    "coverage_state": "incomplete",
    "temporal_state": "finished",
    "contribution_count": 3,
    "source_mode": "measured",
    "provenance_segments": [{
      "start": "2026-10-31T10:00:00-03:00",
      "end": "2026-10-31T11:00:00-03:00",
      "configuration_revision": 1,
      "category_revision": 1,
      "source_mode": "measured",
      "source_id": "00000000-0000-4000-8000-000000000004",
      "base_categories": [],
      "basis_sources": []
    }],
    "created_at": "2026-10-31T15:00:00Z",
    "last_new_data_at": "2026-10-31T15:00:00Z",
    "retain_until": "2027-10-31T15:00:00Z",
    "warnings": [{"code": "missing_coverage", "detail": "Faltan quince minutos de cobertura."}]
  }],
  "excluded_blocks": [],
  "diagnostics": [],
  "warnings": [],
  "reason_code": null
}
```

## Errores y coherencia

| HTTP | Causa |
| --- | --- |
| 200 | Consulta válida, incluso sin medidor/datos o sin bloques contenidos. |
| 401 | Sesión ausente, inválida o vencida. |
| 403 | Sin permiso funcional actual o renovación pendiente. |
| 404 | Categoría fuera del catálogo/contexto inexistente. |
| 422 | Filtro, zona, granularidad, fechas u offset inválidos. |
| 503 | DB/proveedor imprescindible no disponible; no convertir a `no_data`. |

`Problem` reutiliza 001: `code`, `detail` saneado, `operation_ref` y
`field_errors:[{path,code,message}]`; sin SQL, rutas internas, excepciones ni secretos.
Cada petición abre o comparte una captura coherente. La siguiente consulta iniciada
tras una incorporación confirmada obtiene su nueva revisión y cobertura. No se promete
que una petición ya en curso cambie su snapshot. Leer no renueva conservación.
