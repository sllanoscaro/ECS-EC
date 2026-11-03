# Material privado para pruebas locales003

Crear claves de host/cliente efímeras en un directorio0700 temporal; privadas0600.
El auth file del receptor mapea el usuario técnico a `password_hash` Argon2 o
`public_keys` públicas autorizadas. No usar cuentas ni cookies006 para SFTP.
Crear known_hosts desde la clave pública del archivo de host administrado y el puerto
exacto (`[127.0.0.1]:2222 ssh-ed25519 ...`), nunca aceptar una clave descargada sin contraste.
El cliente resuelve contraseña/passphrase desde variables o archivo privado; escenarios,
bytes nativos, manifiestos, journal e informes no contienen esos secretos ni sus rutas.

Las pruebas generan estos archivos en tmp_path, fuera del repositorio. No copiar claves
reales aquí. El fixture usa fuentes001 existentes y descriptores sintéticos explícitos.
