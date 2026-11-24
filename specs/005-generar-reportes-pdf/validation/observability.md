# Instrumentación propia005 con emisor real007

Fecha:2026-11-24. Ver [aceptación técnica y comandos](acceptance.md) y
[matriz de cobertura](coverage.md). Datos exclusivamente sintéticos; no acreditan
una tarifa real, impresión física, participantes ni VPS.

`test_observability.py` verifica una admisión y un terminal por generación nueva,
continuación de la referencia lógica con nueva ejecución y etapas de captura/espera/
render/preflight/publicación. Replay, consulta y descarga no inflan generaciones.
Duraciones se observan con reloj monotónico; captura fallida o recuperación sin una
observación desde claim mantienen null. Los errores de lectura se clasifican como
rechazo esperado/fallo inesperado; un rechazo previo no cuenta como generación admitida.

Saturar la cola acotada o romper el adaptador técnico no impide generar/descargar ni
confirmar estado. Los datos de energía/dinero, cookies, binario, credenciales y detalles
de excepción no se envían al emisor. Las referencias son campos opacos, no etiquetas.
Logs/trazas son observaciones con pérdidas posibles, no un libro contable durable.

La ampliación permanece en007;005 no incorpora infraestructura técnica propia.
Ver [alcance007](../../007-observabilidad-externa/validation/step2.md): las pruebas de
protocolo sobre002 no acreditan su adaptador instalado002:T065 ni003:T072. Su integración
pertenece al paso3; la cobertura completa y visores007 pertenecen al paso4.
