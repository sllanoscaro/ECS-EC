# Aislamiento y despliegue003

2026-11-03. Listener opcional dentro de Uvicorn009, puerto2222, liderazgo exclusivo
PostgreSQL y cierre de conexiones/tareas antes de cerrar DB. Deshabilitado no necesita
claves ni socket. Pruebas reales cubren arranque/rearranque y rechazo de otro listener
activo sin abortar su trabajo. No hay contenedor o worker de aplicación adicional.

Host key persistida0600; known_hosts contrastado obligatorio. Clave de cliente0600 o
password_env; receptor guarda solo verificador Argon2/public keys en archivo privado.
Ambos modos pasan con paquete --no-dev. Host desconocido/cambiado rechaza conexión.
SFTP no usa cookies ni actores humanos006 y no concede permisos Programador.

Raíz virtual por binding, archivo privado por sesión, sin shell/exec/forwarding, symlinks,
lectura del host o sobrescritura nativa. Toda operación heredada de filesystem se deniega.
Errores, argumentos malformados y auditoría usan diagnósticos cerrados; debug AsyncSSH
no propaga nombres/rutas. Cuotas se aplican antes de escribir; originales abortados y
pendientes se conservan. La revisión inmutable comprueba edificio, zona y fuentes001
existentes; ningún archivo crea configuración ni otorga autorización.

Compose monta bytes persistentes y secretos readonly externos, publica loopback por
defecto. El operador debe dar propiedad/permisos al UID de app. El destino puede cambiar
a VPS mediante host/puerto/known_hosts y red autorizados, conservando contrato/cadencia.
No se ejecutó VPS. Antes de hardware físico demostrar IDs/topología/canales y una captura
de la convención CLOSE/EOF del firmware; los fixtures sintéticos no acreditan ese gate.
