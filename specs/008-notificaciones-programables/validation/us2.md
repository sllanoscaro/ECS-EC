# Núcleo periódico008 — evidencia local, 2026-11-24

Implementados planificador, captura funcional, SMTP, despacho, recuperación, consulta
protegida y presentación de entregas. El liderazgo usa una conexión/advisory lock
PostgreSQL de sesión; los futuros se reconcilian antes de programar tras cambios de
tzdata. Se conserva el siguiente slot resuelto para no reconstruir un vencido con
reglas horarias diferentes. La reconciliación interrumpida se reanuda por regla.

Pruebas de PostgreSQL: slots únicos, líder excluyente/pérdida de lock, reintentos durables,
uno/cinco minutos desde el fin, indeterminados sin reintento, proceso vivo frente a
recuperación y consolidación de dos períodos nunca intentados. La captura distingue
conteo conocido, historia incompleta y desconocida. Recepción/calidad consumen el ledger
real002; calidad cuenta rechazos declarados por sus eventos, sin inventar un productor
`reception.rejected`. Cambios administrativos requieren su evidencia funcional de
integridad; sin ella no se afirma historia completa.

Mailpitv1.33.1 real, fijado por digest y expuesto solo en loopback: aceptación persistida,
un destinatario por sobre/To, sin CC/BCC, cuerpos y enlace del entorno. Los resultados
de protocolo verifican DATA positivo, rechazo temporal/definitivo, timeout o fallo TLS
durante transferencia y fallo QUIT después de aceptación. Las pruebas de SMTP simulado
son límites internos de protocolo; no acreditan un relay de producción ni certificado
de un servidor externo.

Perfil periódico parcial con reloj real: dos reglas, diez cuentas elegibles,20 entregas,
cola vacía, cuatro plazas SMTP;20/20 aceptadas. Máximo primer inicio:7,578158s desde
el horario. Máxima duración de intento:0,038121s. PostgreSQL18/Mailpit y el código real
del supervisor/despachador estaban operativos. Este resultado corresponde a008:T052;
**no acredita** el perfil mixto40 de008:T070/SC-003.

Navegador real: primera ventana vacía → información insuficiente/No disponible;
siguiente período de un minuto íntegro sin eventos → Sin novedades/Eventos0/cobertura
completa. Captura local identificada y enlaces protegidos. Administrador, acceso propio
del Operador y denegaciones de objetos ajenos se verifican en API.

Ejecuciones observadas:70 pruebas de notificaciones sin navegador en35,55s; arnés de
navegador aprobado en84,30s con tres escenarios Playwright. Ampliaciones posteriores
se incorporan al [registro de continuación](implementation-checkpoint-2026-11-24.md).
Este corte periódico no cubre personas, el perfil mixto, urgencias ni VPS. El perfil
mixto y las urgencias se verificaron posteriormente en [US3](us3.md); personas y VPS
siguen pendientes en el [estado vigente](acceptance.md).

Ejecución de cierre de US2: **83 pruebas aprobadas en122,82s**, incluyendo el arnés
real de tres escenarios de navegador y Mailpit; cero fallos/errores/omisiones.
[Registro saneado de versiones y recursos](artifacts/us2-results.json). La ejecución
usa el host compartido sin CPU/memoria reservadas para SMTP; PostgreSQL/Mailpit
desechables no tienen límites propios. Los ensayos previos007 permanecen activos.
El adaptador de producción recibe un SSLContext que verifica certificado/hostname;
su prueba interna comprueba TLS antes de credenciales. Un certificado externo/VPS
real sigue pendiente. El envío Mailpit comprueba también el correo vigente tras
una modificación real de identidad006.
