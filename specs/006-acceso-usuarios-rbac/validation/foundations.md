# Fundamentos de identidad

2026-11-02: primera suite fundacional, 31 pruebas pasan con PostgreSQL 18.3 real en
`ecs_identity_test` separado, puerto local 55446. Se escribió y ejecutó la fase de prueba
antes de los módulos; los imports ausentes fallaron como se esperaba.

Se aplicó la migración `identity_initial` sobre `platform_009_initial`, solo cinco tablas
propias y guardia singleton. Se verificaron unicidad incluyendo cuentas inactivas,
roles/estados/versiones, referencias RESTRICT y ausencia de tablas de notificaciones.
Matriz fija completa por acción/perfil/estado, sin autorización por verbo HTTP.
Registro congelado, cero participante y participante sintético con rollback/reintento
completo, exactamente tres intentos máximos y fallo sin cuenta/eventos huérfanos.

Cuenta y evidencia comparten UoW; las denegaciones se registran después de rollback con
actor de proceso/cuenta confiable o no autenticado. Sin almacén paralelo, correo/IP,
credenciales o textos de excepción en la carga. Las suites de autenticación/cuentas
amplían las carreras concretas sobre estos mismos componentes reales.
