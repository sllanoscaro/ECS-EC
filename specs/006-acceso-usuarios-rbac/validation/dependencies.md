# Dependencias y costo inicial

Verificación local 2026-11-02: `argon2-cffi==25.1.0`, bindings `26.1.0`,
`email-validator==2.3.0`, CPython 3.14.4 convencional y uv 0.11.8. Dependencias y hashes
transitivos bloqueados en `uv.lock`; `uv sync --locked --group dev` correcto. No se
actualizó la pila base. El build final también verifica bindings en la imagen elegida.

Argon2id: 65536 KiB, t=3, p=4, salt16/hash32. Tres parejas hash+verificación reales:
mediana 0.1451 s, RSS máximo del proceso 91908 KiB, límite inicial dos trabajos concurrentes.
Son mediciones de este anfitrión, no un SLO ni dimensionamiento de VPS. Hasta 128 MiB de
memoria de trabajo de Argon2 más intérprete/dependencias con dos hashes activos; medir
de nuevo en despliegue. Cancelar una petición no libera el cupo mientras su thread sigue.

Medición concurrente adicional: seis hashes programados, máximo observado dos workers,
0.3259s totales y RSS máximo155820KiB. La medición corrobora el límite, sin fijar un SLO.

Los secretos HMAC se generan externamente y no van en lockfiles, DB, Git ni export.
La excepción HTTP exige development explícito y origen loopback; producción la rechaza.
