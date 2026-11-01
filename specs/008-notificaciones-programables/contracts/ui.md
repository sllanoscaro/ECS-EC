# Contrato de interfaz funcional

React 19+/Next.js 16+, exportación estática y API autenticada FastAPI del mismo origen.
El HTML/JS de la interfaz no contiene secretos ni datos privados de build. La API decide
permisos actuales; ocultar navegación es solo presentación.

## Rutas y permisos

| Página estática | Operador | Administrador técnico | Programador/sin sesión |
| --- | --- | --- | --- |
| `/notificaciones/` | Solo entregas de su cuenta | Historial completo y filtros | Sin datos funcionales; API rechaza |
| `/notificaciones/reglas/` | No ofrece administración | Catálogo, reglas y editor | API rechaza |

La selección de entrega/regla usa query (`?entrega=<uuid>`, `?regla=<uuid>`) y carga por
API; no exige generar rutas dinámicas por UUID durante build. Abrir una URL con otra
identidad no concede acceso; para el Operador el objeto ajeno se responde 404 sin metadatos.
Sesión caducada conduce a ingreso funcional con retorno seguro a una ruta local.

## Formulario de regla

Campos: nombre, contenido funcional del catálogo, modalidad, cuentas destinatarias y
programación o condición. No hay entrada de direcciones arbitrarias ni contenido HTML
libre. Las cuentas se seleccionan por identidad; sus correos vigentes solo se presentan
al administrador con permiso de gestión de cuentas.

- Periódica: intervalo N minutos/horas o diaria/semanal/mensual/anual, inicio, zona, hora
  y campos calendario aplicables. Muestra próximas tres ocurrencias, ventanas y zona.
- Urgente consumo: CAT-01..07, ventana y resolución si intervalo, comparación y umbral
  Decimal finito >=0 en kWh; categoría calculada identifica base y alcance.
- Urgente ausencia: categoría y plazo >=15 min; informa estado sin fuente sin afirmar cero.
- Urgente sistema: tipo permitido de evento funcional; no logs ni trazas.

Guardar crea regla desactivada o una revisión pausada. Activar exige vista previa vigente,
destinatarios autorizados y botón explícito. Un resumen con auditoría no permite activar
si hay un Operador destinatario. Errores de campo mantienen valores introducidos y muestran
razón; un conflicto de revisión obliga a recargar la configuración actual antes de guardar.
Pausa informa cancelación de pendientes y conserva historial de intentos.

## Historial y detalle

Filtros: período/estado para cuenta propia; administrador añade regla y destinatario.
Paginación por cursor. Estados separados: cargando, sin notificaciones, error de consulta,
datos insuficientes y lista disponible. Un error nunca se representa como lista vacía.

Cada fila indica tipo/prioridad, regla/versión, período, fecha prevista/detección, fecha de
intento y estado funcional. El detalle muestra calidad, unidad, origen medido/calculado,
corte, retraso, períodos recuperados e intentos visibles para su destinatario autorizado.
El Operador no recibe la lista de destinatarios ni direcciones ajenas. Auditoría funcional
solo para administrador. No hay consola técnica ni enlace que herede acceso Programador.

`aceptada`: «Aceptada por el servicio de correo», con identificación de «Transporte de
prueba local» cuando corresponda. No afirmar lectura ni recepción externa. `indeterminada`:
«No se pudo confirmar si el servicio aceptó el correo»; no mostrar reintento automático.
`cancelada` distingue pérdida de permisos, pausa/sustitución y consolidación.

Reenvío disponible solo al administrador en fallida/indeterminada, con motivo y aceptación
explícita de posible repetición. La respuesta enlaza la nueva entrega; la anterior conserva
estado e intentos. Deshabilitar doble envío en UI y enviar clave idempotente estable para
la misma acción. El servidor mantiene la garantía ante reintentos o solicitudes directas.

## Correo

Asunto y cuerpo versionados, texto plano y HTML escapado; edificio, tipo, prioridad,
regla/versión, fechas relevantes, ventana/corte, unidades/calidad y referencias protegidas.
Resumen sin novedades lo dice expresamente; información insuficiente no se presenta
como consumo cero. CAT-01 calculada identifica base/alcance sin repetir la suma.
Recuperación enumera períodos omitidos; no oculta huecos de entregas ya intentadas.

Solo To del destinatario efectivo, sin otras direcciones. No adjuntar automáticamente
PDF. Enlaces se basan en `APP_PUBLIC_BASE_URL` del entorno, no incluyen tokens públicos y
exigen autenticación/permisos normales. El correo no contiene logs, métricas, trazas,
secretos ni detalles internos de excepción.

## Validación de uso

Reutilizar los estados, contenido y tiempos de [quickstart.md](../quickstart.md).
Validar teclado, etiquetas y mensajes comprensibles en formulario/historial. SC-008 exige
9 de 10 tareas de configuración diaria 06:00 realizadas por administradores representativos,
sin ayuda y en <=3 minutos, incluyendo identificar la próxima fecha.
