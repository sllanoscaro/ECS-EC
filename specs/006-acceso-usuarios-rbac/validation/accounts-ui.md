# Gestión de cuentas mediante navegador

2026-11-02: Playwright/Chromium con TLS local, servidor/UoW reales y base nueva
`ecs_identity_ui3_test`, fixtures por archivo protegido. Dos escenarios conjuntos pasan:
smoke de plataforma y flujo de identidad/administración completo en6.9s.

La UI crea Operador y Administrador, rechaza correo duplicado y limpia credenciales,
edita/desactiva una cuenta y restablece su contraseña con revisión vigente. Se verifica
renovación por ambos perfiles, reingreso, navegación por permisos, Operador denegado,
cierre entre pestañas y vencimiento con reloj interno. El selector se prueba por rol/nombre
accesible para no confundir el texto de sus opciones con su label.
Vitest y build/TypeScript de estas páginas pasan. No hay datos privados en HTML estático.
Este resultado no acredita consultas/PDF, configuraciones de otros dominios o personas/VPS.
