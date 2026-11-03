# Instrumentación propia006 — 2026-11-03

006:T082/T083 completadas con el emisor007 real (`Telemetry`, LogEmitter y Traces),
sin recrear infraestructura ni acoplar autenticación/commits a visores o correo.
`identity/telemetry.py` mantiene contexto por petición mediante ContextVar; crea referencias
opacas nuevas por operación con padre de petición/operación interna. No acepta propagación
pública ni pasa argumentos de servicios, entidades, errores o credenciales al emisor.

- `identity/sessions.py`: autenticación y sesión, etapas de validación/lectura/commit.
- `identity/services.py`: autorización separada y mutaciones/recuperación; terminal después
  de la devolución del servicio, con commit ya confirmado cuando hay cambio.
- `identity/api.py`: contexto aislado de petición, restaurado al finalizar.
- `cli.py`: instancia el emisor común por configuración y delimita ejecución/recursos de
  bootstrap/recuperación. Mantiene TTY, getpass y servicios guardados originales.

`test_telemetry.py` comprueba éxito de ingreso, rechazo de autorización frente a fallo
inesperado, recuperación durable, etapas, referencias concurrentes separadas y ausencia
  de contraseña, correo, cookie, IP, motivo o excepción sintética en señales. Cola real
saturada y sink/admisión fallidos conservan autorización y alta de cuenta; las pérdidas
observables permanecen en el emisor007. Son fallos controlados del adaptador/IO, no una
validación de visores remotos ni de su retención. El contrato/red del exporter pertenece
al proveedor007 y no se declara aceptado por estas pruebas006.

La nueva prueba falló primero por ausencia del módulo; después se ajustó para comprobar
el comportamiento faltante y falló por no existir terminal de autenticación. Tras conectar
el adaptador, los casos pasan. No se afirma TDD integral de toda la regresión.
Los controles nuevos de rechazo de cuerpo y límites sobre consultas reales se agregaron
como regresiones del incremento. Resultados finales en [regresión](regression.md).
