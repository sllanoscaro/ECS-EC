# Cuentas y concurrencia

PostgreSQL18 real en base independiente. La fase de pruebas nueva precedió a DTOs/servicios
de cuentas y falló por sus imports ausentes. Las suites de API/matriz/recipient y carreras
iniciales pasaron19 casos; la ampliación de concurrencia/acceso pasó17 casos.

Comprobado mediante transacciones/conexiones distintas y esperas observadas en
`pg_stat_activity`, no por ejecutar operaciones secuencialmente: dos administradores
retirándose, correo equivalente concurrente, actor revocado/perfil perdido mientras
espera la guardia, cruce de vencimiento, reset mientras Argon2 verifica login y consumo
único de presesión. Se conserva al menos un admin activo y no se aceptan capturas antiguas.

Todos los cambios de correo/perfil/estado/reset/reactivación revocan dos dispositivos;
recipiente interno refleja correo/revisión/versiones actuales y elegibilidad humana.
No-op conserva revisión, identidad y sesiones (actividad autorizada puede renovarse).
API valida autorización antes del objeto/DTO, ETag fuerte/If-Match428/412, correo409,
cuentas inactivas incluidas, y proyección de solo ocho campos sin hashes/digests/bearers.
