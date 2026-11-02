# Contrato HTTP: Reportes PDF

Base `/api/v1`, mismo origen que la interfaz estática. Tres operaciones protegidas; identidad/sesión reales de spec-006. Operador y Administrador técnico con permiso vigente de consulta/generación PDF pueden solicitar y leer reportes del edificio. Programador o identidad técnica no obtienen acceso funcional.

Cookie opaca `ecs_ec_session`: HttpOnly, SameSite=Lax, Secure bajo HTTPS. Toda respuesta protegida usa `Cache-Control: no-store`. POST exige origen permitido, `X-CSRF-Token` de sesión e `Idempotency-Key` de 1..100 caracteres. El permiso se comprueba antes de recuperar una respuesta idempotente.

## POST `/reports`

Admite exactamente una variante, sin campos ajenos:

| Escala | Cuerpo |
| --- | --- |
| Diario | `{"scale":"diario","date":"2026-10-31"}` |
| Mensual | `{"scale":"mensual","year":2026,"month":10}` |
| Anual | `{"scale":"anual","year":2025}` |

Fecha debe existir, mes está en 1..12 y año representa una ventana calendario válida. Zona y edificio provienen de configuración autorizada, no de offsets arbitrarios enviados por cliente. Rechazar selección incompleta/inexistente/totalmente futura; admitir período actual con corte/provisional y pasado sin datos.

Respuesta 202 JSON con `id`, `scale`, `window:{start,end}`, `timezone`, `cutoff_at`, `state`, `status_path` y `download_path:null`. Solicitud y captura quedan durables; la generación continúa dentro del monolito. Una captura admitida que falla puede quedar `fallido` con resultado/evento durables y se observa en estado; una caída de base sin confirmación produce 503 y no se afirma persistencia.

Misma clave/actor/operación/cuerpo devuelve solicitud original; otro cuerpo con misma clave produce 409. Reintentar por decisión de la persona usa nueva clave e identidad, sin alterar la anterior. La normalización de fecha es la misma al calcular hash y ventana.

## GET `/reports/{report_id}`

200 JSON: `id`, `scale`, `window`, `timezone`, `cutoff_at`, `state`, `created_at`, `issued_at` nullable, `filename` nullable, `functional_reason_code` nullable, `download_path` nullable, `sha256` nullable y `byte_length` nullable. Estados: `pendiente`, `generando`, `generado`, `fallido`. Únicamente `generado` ofrece ruta de descarga.

Sin bytes, manifiesto geométrico interno, datos personales de quien solicitó, stack traces ni detalles de configuración. La interfaz puede consultar periódicamente este recurso con espera acotada; caducar la sesión termina la consulta y requiere ingreso normal.

## GET `/reports/{report_id}/download`

200 solo si generado y autorizado actualmente: binario íntegro `application/pdf`, `Content-Disposition: attachment` con nombre seguro del edificio/escala/período, longitud y `Cache-Control: no-store`. No URL pública, token portador en enlace ni redirección a una carpeta estática. La lectura no vuelve a generar ni modifica captura/emisión.

409 si aún pendiente/generando o fallido; el motivo funcional dirige a conservar opciones y nueva solicitud. Un fallo de red de descarga no cambia un resultado generado ni produce otra emisión o evento `pdf.failed`; la persona puede repetir la descarga del mismo binario.

## Errores comunes

401 sesión inválida; 403 permiso insuficiente/CSRF/origen rechazado; 404 reporte inexistente o fuera de alcance sin metadatos; 409 conflicto idempotente o descarga no disponible; 422 selección/campos inválidos; 503 dependencia de base no disponible. `Problem` contiene `code`, `detail`, `operation_ref`, `field_errors:[{path,code,message}]`, todo saneado. Una denegación/validación no cambia datos de negocio ni se presenta como fallo del generador admitido.
