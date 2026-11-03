# Prerrequisitos comprobados

Disponibilidad actualizada por inspección estática el2026-11-03; sin cambiar selección
persistida ni ejecutar nuevas pruebas de integración. Registro de preparación2026-11-02:
`requirements.md`: 16/16 revisados, sin cambios de marcadores. No hay extensions.yml.

G0 disponible: Settings, reloj UTC/monotónico, Database/UoW, errores seguros, Alembic,
FunctionalAudit/EventWriter y composición de plataforma009 existen con pruebas reales
registradas en su aceptación. Identidad utiliza estos componentes, sin recrearlos.

| Gate | Resultado y propietario |
| --- | --- |
| G1 consultas | Disponibles `backend/src/ecs_ec/consumption/{queries,router}.py` y `costs/api.py`, compuestos en `main.py`. Integraciones ampliadas006 pendientes según sus tareas; contratos HTTP de specs001/002/004. |
| G2 PDF | Falta `reports/api.py`; contrato HTTP de spec005. |
| G3 mantenimiento | Disponibles `consumption/configuration.py`, validación/recepción/retención002 y `costs/{api,services,profiles,bills}.py`, con UI administrativa001/004.006:T068/T075/T076 siguen pendientes de ejecución propia. |
| G4 SFTP | Falta receptor/publicador003; [contrato](../../003-simulador-pas600-sftp/contracts/sftp-reception.md). |
| G5 emisión técnica | Disponibles `observability/{logging,tracing,lifecycle}.py`, propiedad007;006:T082/T083 siguen pendientes de instrumentación/verificación. No equiparar emisor básico con cobertura integral. |
| G6 personas/VPS | Vistas de consumo/costos disponibles; faltan personas y PDF real para los recorridos que lo requieren. VPS sigue pendiente conforme a decisión previa del usuario. |

Los gates G1/G3 y el emisor básico G5 ya no están ausentes; las tareas006 de integración
y aceptación que los consumen permanecen pendientes hasta su ejecución. No se crean proveedores
ficticios ni se presenta una prueba omitida como aprobación. US1/US3, política, protocolo
neutral e historial propio pueden avanzar sobre G0. El participante concreto/SMTP es de008.
