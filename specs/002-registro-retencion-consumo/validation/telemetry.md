# Instrumentación propia002 — 2026-11-24

T065 consume el emisor007 real; no incorpora transporte, colector ni visor.
`test_history_telemetry.py` se escribió y ejecutó antes de extender el adaptador:
falló por falta de la inyección telemetry; después pasan recepción/recuperación,
agregados, pendientes, espera15min, retirada protegida y fallo del adaptador.

`ReceptionAttempt.technical_context` guarda UUID opacos fuera del manifiesto/digest y de
mediciones/eventos funcionales. La migración `consumption_002_context` deja registros
históricos sin contexto; no inventa parentesco. Nuevos intentos de una publicación
confiable comparten referencia aleatoria opaca, acotada por edificio/proceso/publicación.
Recuperar conserva operación/intento/publicación y genera otra ejecución.

El caso de referencia confirma tres categorías y falla con dos pendientes: emite
execution.completed/unexpected_error con counts=null, nunca reception.completed.
Otro objeto Reception recupera las dos posiciones, conserva las tres originales y
emite un único resumen lógico con cinco aceptaciones. Lectura y replay completado no
emiten nuevas ejecuciones; reenvío tiene otro intento y cinco duplicados, sin novedades.

Agregados se observan sin contar flush como aceptación; pendientes/retirada tienen
operaciones internas y códigos cerrados. Las consultas de agregados usan
consumption.query_aggregates. Lifespan y adquisición inyectan el emisor común.
No se emiten cuerpos, fuentes nativas, tokens, energía ni texto de excepciones.
Fallo técnico no cambia commits, conservación ni eventos009. Puede perderse señal
entre commit y emisión; no se promete contabilidad técnica exactamente una vez.

[Regresión compartida](../../006-acceso-usuarios-rbac/validation/regression.md).
002 queda70/71; T068 exige personas y permanece pendiente.
