# Contrato HTTP: Costos BT4.3

Base `/api/v1`. Sesión funcional opaca de spec-006, permisos actuales y `Cache-Control: no-store` en recursos protegidos. Cookie HttpOnly/SameSite y Secure bajo HTTPS; mutaciones requieren token CSRF ligado a sesión y origen válido. Programador no es un perfil funcional.

## Operaciones

| Método/ruta relativa | Permiso | Contrato |
| --- | --- | --- |
| GET `/costs/cycles` | Lectura funcional | Filtros inicio/fin/corte; ciclos y últimos resultados visibles con temporalidad/suficiencia, sin crear cálculos. |
| GET `/costs/calculations/{calculation_id}` | Lectura funcional | Desglose, importes disponibles/completos, límites, moneda, redondeo, cobertura y referencias de reproducción autorizadas. |
| POST `/costs/calculations` | Administrador | Ciclo/suministro, evidencia mensual cuando corresponda y motivo de recálculo; selecciona perfil publicado al corte y crea revisión, nunca ajusta fuentes por una boleta. |
| GET `/costs/bills` | Lectura funcional | Boletas/revisiones por ciclo, identificador y campos documentales permitidos. |
| GET `/costs/bills/{bill_id}` | Lectura funcional | Revisión vigente o revisión histórica solicitada, conceptos y referencias. |
| POST `/costs/bills` | Administrador | Registro manual de documento con ciclo y conceptos; detectar identificador repetido. |
| PUT `/costs/bills/{bill_id}` | Administrador | Corrección explícita con revisión previa; no modifica el documento histórico. |
| GET `/costs/comparisons/{comparison_id}` | Lectura funcional | Valores calculados/facturados alineados, exclusiones, diferencia y porcentaje nullable. |
| POST `/costs/comparisons` | Administrador | Referencias de cálculo y boleta versionados; persiste comparación nueva autorizada. |
| GET `/costs/profiles` | Administrador | Revisiones con calendarios/segmentos/fuentes y metadatos `latest_version_id`/`selected_published_version_id`; las consultas de cálculo ya muestran referencias funcionales aplicadas. |
| POST `/costs/profiles` | Administrador | Nueva revisión con calendario completo o borrador limitado y `expected_previous_version_id`, sin sobrescribir el historial. |
| GET `/costs/supply` | Administrador | Configuración, id/revisión y ETag fuerte; 404 si aún no existe. |
| PUT `/costs/supply` | Administrador | Alta con `If-None-Match: *` o modificación con `If-Match` del único suministro y asociación explícita de CAT-01 física. |
| GET `/costs/history` | Lectura funcional | Ciclos/resultados/boletas/diferencias compatibles, estados separados y al menos 12 meses cuando existan. |

## Cuerpos y respuestas

Las formas tipadas se implementan en `costs/schemas.py` a partir de [data-model.md](../data-model.md). Campos no declarados se rechazan. Decimales como cadenas finitas; fechas RFC3339 con offset y zona IANA; campos monetarios no calculables son null con razón, nunca cero implícito. Unidades de energía/potencia separadas de CLP.

`CalculateRequest`: `supply_id`, `start_at`, `end_at`, `timezone`, criterio de límites y motivo de recálculo cuando corresponde. Admite `billing_month_ref` (`YYYY-MM`) y `billing_month_source_ref` juntos cuando la política del perfil exige evidencia explícita; el servidor valida su correspondencia documental. El servidor deriva actor/corte/revisión, resuelve la política mensual y selecciona la última revisión publicada del perfil visible al corte con sus segmentos. No admite forzar una revisión tarifaria desde el cuerpo. Mes ausente/no resuelto o políticas contradictorias limitan los cargos afectados (`billing_month_unresolved`), sin impedir los demás componentes calculables; un campo mal formado produce 422. Nunca inferir el mes de emisión/inicio/fin sin regla documental.

En modo explícito, `billing_month_source_ref` es una referencia estructurada con `document_reference`, `supply_id`, `start_at`, `end_at` y `billing_month_ref`; el Administrador declara que el documento respalda esos datos. El servidor valida los metadatos contra solicitud/política y captura la evidencia con el actor autenticado, sin leer automáticamente el documento. Ambos campos omitidos producen limitación prevista; enviar solo uno, un mes inválido o evidencia de forma inválida devuelve 422. Una evidencia bien formada pero contradictoria con suministro/ciclo/mes/política produce `billing_month_unresolved`. En modo `documented_rule` no se admite un mes impuesto por el cliente (422); el servidor deriva mes y referencia de la regla versionada.

`BillInput`: identificador/suministro, fecha de emisión, límites declarados y efectivos, criterio de lectura, moneda, referencia documental, magnitudes leídas/bases facturadas separadas, conceptos y tributación. Cantidades ausentes son null, ajustes/abonos conservan signo. No acepta archivo PDF ni texto de excepción.

`ProfileInput`: BT4.3, suministro/condiciones/fuente, `publication_state` (`draft` o `published`), `expected_previous_version_id` y calendario completo de segmentos. Cada segmento declara límites de vigencia, cargos/reglas soportadas, calendario de punta, históricos, política de mes de demanda y redondeo. El estado se fija al crear; publicar un borrador requiere otra revisión. No hay segmentos superpuestos dentro de la revisión; la coincidencia de vigencias entre revisiones históricas es válida. Guardar una revisión no altera cálculos existentes y solo una publicada cambia la selección de cálculos nuevos. `expected_previous_version_id` es obligatorio, null solo para la primera revisión; comparar atómicamente con la última guardada, incluidos borradores, o devolver 409. GET perfiles conserva esos metadatos en cada página si se pagina el historial.

`SupplyInput`: tablero general/CAT-01 física, distribuidora, ubicación, condiciones, fuentes y diferencias de punto de medición. Actor, id y revisión los deriva el servidor. `SupplyDetail` devuelve esos datos e id/revisión; GET y PUT exitosos incluyen el mismo ETag fuerte de recurso, derivado de id/revisión. Cada cálculo captura los datos y revisión utilizados.

`ComparisonRequest`: `calculation_id` y `bill_revision_id` explícitos. El servidor valida suministro/ciclo/moneda/bases compatibles y persiste la comparación de ese par. Se permite comparar revisiones históricas seleccionadas explícitamente; ello no las convierte en las revisiones actuales. GET ciclos/historial identifica los recursos seleccionados y la comparación exacta si existe para que la UI pueda consultar o crear el contraste.

`CalculationDetail`: revisión y captura, temporalidad/suficiencia/ejecución separadas, conceptos con bases/reglas/precios/importes/limitaciones, subtotal disponible y total completo nullable, moneda, redondeo, suministro/perfil/segmentos capturados, mes de demanda/fuente/versión de política y punto de medición. `ComparisonDetail` contiene ambas revisiones, pares alineados, exclusiones y diferencia con porcentaje null si facturado=0. Ciclos/historial resuelven el par exacto según [integraciones](integrations.md): con recursos seleccionados sin comparación devuelven `comparison_status=missing_for_selected_revisions`, diferencias null y referencias/valores disponibles; nunca recuperan una comparación antigua como actual. Gráfico/tabla consumen los mismos registros, no recomputan dinero en navegador.

## Mutaciones, errores y concurrencia

- Mutaciones usan `Idempotency-Key` por actor/operación y hash canónico del cuerpo; guardar con el cambio. Misma clave/cuerpo reutiliza recurso, cuerpo distinto devuelve 409.
- PUT de recurso existente usa revisión `If-Match`; ausencia 428, revisión desactualizada 412. Autorizar antes de recuperar una respuesta idempotente confirmada; recuperar esa operación antes de evaluar la revisión de una mutación nueva.
- Alta inicial del suministro usa `If-None-Match: *` y devuelve 201/revisión 1/ETag; si ya existe devuelve 412. Modificar exige el ETag exacto en `If-Match` y devuelve 200/revisión incrementada/nuevo ETag. Sin precondición devuelve 428; enviar ambas cabeceras o una forma no admitida devuelve 422. La restricción de edificio único y la evaluación de precondiciones se resuelven atómicamente, también ante altas simultáneas. Reintentar una operación confirmada conserva la precedencia del replay autorizado descrita arriba.
- 200 para lectura/revisión; 201 para creación; 401 sin sesión, 403 sin permiso, 404 objeto inexistente o ajeno no revelable, 409 identidad/vigencia incompatible, 422 campos inválidos y 503 base/dependencia indisponible. Validación no produce modificaciones parciales.
- Error funcional saneado: `{code, detail, operation_ref, field_errors}`; no SQL, rutas internas, sesiones ni excepciones del motor. Un resultado fallido de negocio persistido se devuelve con su identidad/estado; no se confunde con un fallo de transporte HTTP sin resultado durable.
- Listados usan cursor estable, `limit` 1..100 (25 por defecto), rango `[from,to)` y corte; orden determinista por fecha/id. No exponer identidad técnica ni datos de otro edificio.

Todas las catorce operaciones se prueban contra implementaciones reales; el diseño Markdown no acredita por sí mismo una API ejecutada.

## Detalles de la implementación local

Los DTOs Pydantic004 y el OpenAPI de la aplicación son la forma ejecutable de los
recursos. Instantes de comandos aceptan `start_at`/`end_at` documentados y `start`/`end`;
la serialización de períodos anidados usa `start`/`end`. No enviar ambos alias a la vez.
Los tipos frontend readonly se regeneran desde esos DTOs y conservan importes textuales.

GET perfiles incluye `latest_version` y `selected_published_version` completos además de
sus IDs; permite copiar la última guardada aunque quede fuera de la primera página de
historia. Los cursores mantienen corte/filtros originales y están firmados con propósito006.
Porcentaje de contraste: redondeo half-up a seis decimales, regla capturada
`signed_delta_absolute_denominator_6dp_v1`; denominador cero mantiene porcentaje null.
Comparación con límites efectivos declarados inciertos devuelve422 en lugar de cifras
aparentemente alineadas. Estos motivos no producen `cost.failed` técnico.
