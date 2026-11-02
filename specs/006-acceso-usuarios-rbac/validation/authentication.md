# Autenticación real local

PostgreSQL18.3 aislado, CPython3.14.4 y dependencias bloqueadas. Las pruebas se prepararon
antes de implementar; se corrigió la expiración de capturas ORM al salir de la UoW de
lectura (hash/versiones se conservan como captura privada desligada, no con locks abiertos).

Verificados: correo canónico IDNA/casefold sin unir puntos/+, contraseñasUnicode exactas,
15/128 admitidos y14/129 rechazados, Argon2id; CSRF de presesión, origen, cookies y Problem
sin secretos, renovación restringida/reingreso, quinto fallo429 y espera exacta15min sin
extensión, denegación equivalente desconocida/inactiva/incorrecta, introspección sin
actividad y borde30min, actualización interactiva29→59 y no reactivación vencida.
Dos bootstraps concurrentes en conexiones PostgreSQL independientes dejan una sola cuenta.
CLI exigeTTY/getpass y no acepta ni refleja argumentos de contraseña. El costo/límite de
hashing se conserva en [dependencies](dependencies.md); no hay SLO nuevo.

Comando: `uv run --locked pytest backend/tests/unit/identity backend/tests/integration/identity backend/tests/contract/identity`.
Las suites de cuentas/concurrencia y regresión amplían estos resultados. No hay VPS,
consultas de negocio ni SMTP como condición de ingreso local.
