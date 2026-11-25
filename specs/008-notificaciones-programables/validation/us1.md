# Configuración008 — validación local, 2026-11-24

US1 implementada sobre PostgreSQL18, identidad006 y consumo001/002 reales. Las reglas
se crean desactivadas; una revisión inmutable queda pausada. Activar requiere una vista
previa vigente y la pausa cancela pendientes, conservando intentos ya iniciados.

La ejecución inicial de los directorios `backend/tests/{contract,integration,unit}/notifications`
aprobó47 pruebas. La ampliación del núcleo periódico aprobó70 pruebas sin navegador;
incluye las anteriores de configuración. Vitest completo:97 pruebas aprobadas. La
exportación Next contiene `/notificaciones/` y `/notificaciones/reglas/`, sin datos privados
en la construcción. El arnés privado `test_browser.py` ejecutó tres escenarios Playwright
contra el monolito real, con sesiones006, PostgreSQL y Mailpit locales: configuración,
denegación Operador/anónimo y dos cortes periódicos. Resultado: aprobado en84,30s.

Cobertura específica: contrato cerrado; UUID registrados; contenido administrativo
restringido; origen/CSRF; 401/403/404/409/412/428/422; replay antes de If-Match;
ediciones simultáneas; pausa y cambio de versión; intervalos y cuatro calendarios;
DST de Santiago, enero31/febrero/marzo y29 de febrero. Las pruebas de coordinación
verifican ambos órdenes de revocación/inicio, cambio de correo y redescubrimiento
de nuevas referencias entre transacciones PostgreSQL.

La decisión del usuario permite únicamente la primera ventana periódica vacía cuando
su corte coincide con starts_at. El contrato y la captura la identifican expresamente;
sus conteos son NULL y su cobertura desconocida. No modifica intervalos de consumo.

Capturas autenticadas inspeccionadas a1440/768/390px, sin desbordamiento horizontal.
Se conserva el shell/tipografía del proyecto; la inspección usa Playwright porque el
inspector de diseño disponible no administra esta sesión autenticada. Esto verifica
el recorrido automatizado y la presentación, no una evaluación con personas.

El protocolo [SC-008](usability.md) está preparado; no hay resultados humanos.
Las checklists de revisión siguen intactas por autorización expresa del usuario.
